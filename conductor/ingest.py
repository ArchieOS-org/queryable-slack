"""
Main ingestion orchestration.

Entry point for the 5-step ingestion pipeline.
"""

import glob
import hashlib
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import chromadb

from conductor.file_parser import extract_text_from_file
from conductor.models import Session, SlackMessage, UserMap
from conductor.processor import load_messages_from_directory, sessionize_messages
from conductor.user_mapper import load_users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def discover_conversations(export_path: Path) -> Dict[str, str]:
    """
    Discover all conversations (channels, DMs, MPIMs) in the export.

    Args:
        export_path: Path to Slack export root directory

    Returns:
        Dictionary mapping conversation directory name -> conversation type
    """
    conversations: Dict[str, str] = {}

    # Load channel metadata
    channels_file = export_path / "channels.json"
    channel_names = set()
    if channels_file.exists():
        try:
            with open(channels_file, "r", encoding="utf-8") as f:
                channels = json.load(f)
            for channel in channels:
                if isinstance(channel, dict) and "name" in channel:
                    channel_names.add(channel["name"])
        except Exception as e:
            logger.warning(f"Failed to load channels.json: {e}")

    # Load DM metadata
    dms_file = export_path / "dms.json"
    dm_ids = set()
    if dms_file.exists():
        try:
            with open(dms_file, "r", encoding="utf-8") as f:
                dms = json.load(f)
            for dm in dms:
                if isinstance(dm, dict) and "id" in dm:
                    dm_ids.add(dm["id"])
        except Exception as e:
            logger.warning(f"Failed to load dms.json: {e}")

    # Load MPIM metadata
    mpims_file = export_path / "mpims.json"
    mpim_names = set()
    if mpims_file.exists():
        try:
            with open(mpims_file, "r", encoding="utf-8") as f:
                mpims = json.load(f)
            for mpim in mpims:
                if isinstance(mpim, dict) and "name" in mpim:
                    mpim_names.add(mpim["name"])
        except Exception as e:
            logger.warning(f"Failed to load mpims.json: {e}")

    # Scan export directory for conversation directories
    for item in export_path.iterdir():
        if not item.is_dir():
            continue

        dir_name = item.name

        # Skip top-level attachments directory
        if dir_name == "attachments":
            continue

        # Check if it's a channel
        if dir_name in channel_names:
            conversations[dir_name] = "channel"
            continue

        # Check if it's a DM (starts with "D" followed by alphanumeric)
        if re.match(r"^D[A-Z0-9]+$", dir_name) and dir_name in dm_ids:
            conversations[dir_name] = "dm"
            continue

        # Check if it's an MPIM (matches MPIM name pattern)
        if dir_name in mpim_names or dir_name.startswith("mpdm-"):
            conversations[dir_name] = "mpim"
            continue

        # Last-resort fallback: Check if it looks like a DM directory
        # This regex matches Slack DM IDs: starts with 'D' followed by 8+ alphanumeric characters
        # Only used when metadata files are missing or corrupted
        import re
        if re.match(r"^D[A-Z0-9]{8,}$", dir_name):
            conversations[dir_name] = "dm"
            continue

    logger.info(f"Discovered {len(conversations)} conversations")
    return conversations


def get_channel_name_for_session(dir_name: str, conversation_type: str) -> str:
    """
    Get the channel_name for a session based on directory name and type.

    Args:
        dir_name: Directory name
        conversation_type: One of "channel", "dm", "mpim"

    Returns:
        Channel name for the session
    """
    if conversation_type == "channel":
        return dir_name
    elif conversation_type == "dm":
        return f"dm-{dir_name}"
    elif conversation_type == "mpim":
        return dir_name
    else:
        return dir_name


def enrich_session_with_files(
    session: Session, messages: List[SlackMessage], conversation_dir: Path
) -> Session:
    """
    Enrich a session's transcript with file content.

    Args:
        session: Session to enrich
        messages: List of SlackMessage objects in the session
        conversation_dir: Path to conversation directory

    Returns:
        Enriched Session object
    """
    attachments_dir = conversation_dir / "attachments"
    if not attachments_dir.exists():
        # No attachments directory, return session as-is
        return session

    enriched_parts = [session.transcript]
    files_processed = 0
    files_skipped = 0
    files_error = 0

    for msg in messages:
        if not msg.files:
            continue

        for file_info in msg.files:
            file_id = file_info.get("id")
            filename = file_info.get("name", "unknown")
            filetype = file_info.get("filetype", "").lower()
            mimetype = file_info.get("mimetype", "").lower()

            if not file_id:
                continue

            # Find the attachment file (may have different naming patterns)
            # Pattern: {FILE_ID}-{filename}
            attachment_pattern = f"{file_id}-*"
            matching_files = list(attachments_dir.glob(attachment_pattern))

            if not matching_files:
                # Try alternative pattern: just file_id
                matching_files = list(attachments_dir.glob(f"{file_id}*"))

            if not matching_files:
                logger.debug(f"Attachment not found for file {file_id} ({filename}) in {conversation_dir.name}")
                files_skipped += 1
                continue

            attachment_file = matching_files[0]

            # Determine file type
            if filetype:
                file_type = filetype
            elif mimetype:
                if "pdf" in mimetype:
                    file_type = "pdf"
                elif "word" in mimetype or "document" in mimetype:
                    file_type = "docx"
                elif "text" in mimetype or "plain" in mimetype:
                    file_type = "txt"
                else:
                    file_type = None
            else:
                # Infer from extension
                file_type = attachment_file.suffix.lower().lstrip(".")

            # Extract text from file
            try:
                file_content = extract_text_from_file(attachment_file, file_type)
                if file_content and not file_content.startswith("[SKIPPED:") and not file_content.startswith("[ERROR:"):
                    enriched_parts.append(f"<<< ATTACHMENT START: {filename} >>>")
                    enriched_parts.append(file_content)
                    enriched_parts.append("<<< ATTACHMENT END >>>")
                    files_processed += 1
                    logger.debug(f"  ✅ Processed attachment: {filename}")
                else:
                    files_skipped += 1
                    logger.debug(f"  ⏭️  Skipped attachment: {filename}")
            except Exception as e:
                logger.warning(f"  ⚠️  Failed to process attachment {filename}: {e}")
                enriched_parts.append(f"<<< ATTACHMENT START: {filename} >>>")
                enriched_parts.append(f"[ERROR: Could not parse file {filename}]")
                enriched_parts.append("<<< ATTACHMENT END >>>")
                files_error += 1

    if files_processed > 0:
        logger.debug(f"  File enrichment: {files_processed} processed, {files_skipped} skipped, {files_error} errors")

    enriched_transcript = "\n\n".join(enriched_parts)

    # Create new session with enriched transcript
    return Session(
        session_id=session.session_id,
        start_time=session.start_time,
        end_time=session.end_time,
        channel_name=session.channel_name,
        conversation_type=session.conversation_type,
        transcript=session.transcript,
        enriched_transcript=enriched_transcript,
        file_count=files_processed,
        message_count=session.message_count,
    )


def store_sessions_in_chromadb(sessions: List[Session], db_path: Path = Path("./conductor_db")) -> None:
    """
    Store sessions in ChromaDB for vector search.

    Args:
        sessions: List of Session objects to store
        db_path: Path to ChromaDB persistent storage directory
    """
    if not sessions:
        logger.info("⚠️  No sessions to store")
        print("⚠️  No sessions to store")
        return

    try:
        logger.info(f"💾 Initializing ChromaDB at {db_path}")
        print(f"💾 Initializing ChromaDB database...")
        
        # Initialize persistent ChromaDB client
        client = chromadb.PersistentClient(path=str(db_path))

        # Get or create collection (idempotent)
        logger.info("📚 Creating/accessing collection 'conductor_sessions'...")
        collection = client.get_or_create_collection(
            name="conductor_sessions",
            metadata={"description": "Real Estate Slack conversation sessions"},
        )

        # Prepare data for upsert
        logger.info(f"📝 Preparing {len(sessions)} sessions for storage...")
        print(f"📝 Preparing {len(sessions)} sessions for vector storage...")
        ids = []
        documents = []
        metadatas = []

        for idx, session in enumerate(sessions, 1):
            if idx % 10 == 0 or idx == len(sessions):
                logger.debug(f"  Preparing session {idx}/{len(sessions)}: {session.channel_name}")
                print(f"  Processing session {idx}/{len(sessions)}...", end="\r")
            
            ids.append(session.session_id)
            documents.append(session.enriched_transcript)
            metadatas.append(
                {
                    "date": session.start_time.date().isoformat(),
                    "channel": session.channel_name,
                    "start_time": session.start_time.isoformat(),
                    "end_time": session.end_time.isoformat(),
                    "message_count": session.message_count,
                    "file_count": session.file_count,
                    "conversation_type": session.conversation_type,
                }
            )

        print()  # New line after progress
        logger.info(f"🔢 Generating embeddings and storing in ChromaDB...")
        print(f"🔢 Generating embeddings (this may take a moment)...")
        
        # Upsert to ChromaDB (idempotent)
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

        logger.info(f"✅ Stored {len(sessions)} sessions in ChromaDB at {db_path}")
        print(f"✅ Stored {len(sessions)} sessions in ChromaDB")

    except Exception as e:
        logger.exception(f"❌ Failed to store sessions in ChromaDB: {e}")
        print(f"❌ Error storing sessions: {e}")
        raise


def main(export_path: Path, db_path: Optional[Path] = None) -> None:
    """
    Main ingestion entry point.

    Implements the 5-step ingestion pipeline:
    1. Identity Mapping
    2. Conversation Discovery
    3. Timeline & Sessionization
    4. File Enrichment
    5. Vectorization & Storage

    Args:
        export_path: Path to Slack export directory
        db_path: Optional path to ChromaDB directory (defaults to timestamped conductor_db)
    """
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    
    # Add datestamp to database path if not provided
    if db_path is None:
        db_path = Path(f"./conductor_db_{timestamp}")
    
    logger.info("=" * 80)
    logger.info("INGESTION PIPELINE")
    logger.info("=" * 80)
    logger.info(f"📂 Source export: {export_path}")
    logger.info(f"💾 Database path: {db_path}")
    logger.info(f"⏱️  Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    print(f"\n🚀 Starting ingestion pipeline...")
    print(f"📂 Source: {export_path}")
    print(f"💾 Database: {db_path.name}")
    print(f"⏱️  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Step 1: Identity Mapping
    logger.info("=" * 80)
    logger.info("STEP 1: Identity Mapping")
    logger.info("=" * 80)
    print("📋 Step 1/5: Identity Mapping...")
    try:
        logger.info("Loading user mappings from users.json...")
        user_map = load_users(export_path)
        logger.info(f"✅ Loaded {len(user_map.users)} users")
        print(f"✅ Loaded {len(user_map.users)} users")
    except Exception as e:
        logger.exception(f"❌ Failed to load users: {e}")
        print(f"❌ Error loading users: {e}")
        raise

    # Step 2: Conversation Discovery
    logger.info("=" * 80)
    logger.info("STEP 2: Conversation Discovery")
    logger.info("=" * 80)
    print("\n🔍 Step 2/5: Conversation Discovery...")
    try:
        logger.info("Scanning export directory for conversations...")
        conversations = discover_conversations(export_path)
        logger.info(f"✅ Discovered {len(conversations)} conversations")
        print(f"✅ Discovered {len(conversations)} conversations")
        
        # Log conversation breakdown
        conv_types = {}
        for conv_type in conversations.values():
            conv_types[conv_type] = conv_types.get(conv_type, 0) + 1
        for conv_type, count in conv_types.items():
            logger.info(f"  - {conv_type}: {count}")
            print(f"   {conv_type}: {count}")
    except Exception as e:
        logger.error(f"❌ Failed to discover conversations: {e}")
        print(f"❌ Error discovering conversations: {e}")
        raise

    # Step 3 & 4: Process each conversation (Timeline, Sessionization, File Enrichment)
    logger.info("=" * 80)
    logger.info("STEP 3 & 4: Timeline, Sessionization, and File Enrichment")
    logger.info("=" * 80)
    print(f"\n📝 Step 3-4/5: Processing conversations...")
    all_sessions: List[Session] = []
    total_messages = 0
    total_files = 0

    for idx, (dir_name, conversation_type) in enumerate(conversations.items(), 1):
        conversation_dir = export_path / dir_name
        logger.info(f"[{idx}/{len(conversations)}] Processing: {dir_name} ({conversation_type})")
        print(f"  [{idx}/{len(conversations)}] Processing: {dir_name}...")

        if not conversation_dir.exists():
            logger.warning(f"⚠️  Conversation directory not found: {conversation_dir}")
            print(f"     ⚠️  Directory not found, skipping")
            continue

        try:
            # Load messages from conversation directory
            logger.debug(f"  Loading messages from {dir_name}...")
            messages = load_messages_from_directory(conversation_dir)
            total_messages += len(messages)

            if not messages:
                logger.debug(f"  No messages found in {dir_name}")
                print(f"     ℹ️  No messages found, skipping")
                continue

            logger.info(f"  Loaded {len(messages)} messages")
            print(f"     📨 Loaded {len(messages)} messages")

            # Get channel name for session
            channel_name = get_channel_name_for_session(dir_name, conversation_type)

            # Sessionize messages
            logger.debug(f"  Sessionizing messages...")
            sessions = sessionize_messages(messages, channel_name, conversation_type, user_map)
            logger.info(f"  Created {len(sessions)} sessions")
            print(f"     📦 Created {len(sessions)} sessions")

            # Enrich each session with file content
            logger.debug(f"  Enriching sessions with file content...")
            enriched_sessions = []
            files_in_conversation = 0
            for session_idx, session in enumerate(sessions, 1):
                # Get messages for this session (by matching timestamps)
                session_start_ts = session.start_time.timestamp()
                session_end_ts = session.end_time.timestamp()
                session_messages = [
                    msg
                    for msg in messages
                    if session_start_ts - 1.0 <= float(msg.ts) <= session_end_ts + 1.0
                ]
                enriched_session = enrich_session_with_files(session, session_messages, conversation_dir)
                enriched_sessions.append(enriched_session)
                files_in_conversation += enriched_session.file_count
                
                if session_idx % 5 == 0 or session_idx == len(sessions):
                    logger.debug(f"    Enriched {session_idx}/{len(sessions)} sessions")

            total_files += files_in_conversation
            all_sessions.extend(enriched_sessions)
            logger.info(f"  ✅ Processed {dir_name}: {len(enriched_sessions)} sessions, {files_in_conversation} files")
            print(f"     ✅ {len(enriched_sessions)} sessions, {files_in_conversation} files processed")

        except Exception as e:
            logger.error(f"  ❌ Failed to process conversation {dir_name}: {e}")
            print(f"     ❌ Error processing: {e}")
            # Continue processing other conversations - don't stop on errors
            continue

    logger.info(f"📊 Summary: {len(all_sessions)} sessions, {total_messages} messages, {total_files} files")
    print(f"\n📊 Summary: {len(all_sessions)} sessions, {total_messages} messages, {total_files} files")

    # Step 5: Vectorization & Storage
    logger.info("=" * 80)
    logger.info(f"STEP 5: Vectorization & Storage ({len(all_sessions)} sessions)")
    logger.info("=" * 80)
    print(f"\n💾 Step 5/5: Vectorization & Storage...")
    try:
        store_sessions_in_chromadb(all_sessions, db_path)
    except Exception as e:
        logger.error(f"❌ Failed to store sessions in ChromaDB: {e}")
        print(f"❌ Error storing sessions: {e}")
        raise

    end_time = datetime.now()
    duration = end_time - start_time
    logger.info("=" * 80)
    logger.info("✅ INGESTION COMPLETE!")
    logger.info(f"📊 Processed {len(all_sessions)} sessions")
    logger.info(f"📨 Total messages: {total_messages}")
    logger.info(f"📎 Total files: {total_files}")
    logger.info(f"💾 Database location: {db_path}")
    logger.info(f"⏱️  Duration: {duration}")
    logger.info(f"⏱️  Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    print(f"\n✅ Ingestion complete!")
    print(f"📊 Sessions: {len(all_sessions)}")
    print(f"📨 Messages: {total_messages}")
    print(f"📎 Files: {total_files}")
    print(f"💾 Database: {db_path.name}")
    print(f"⏱️  Duration: {duration}")
    print(f"⏱️  Completed: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python -m conductor.ingest <path_to_slack_export>")
        sys.exit(1)

    export_path = Path(sys.argv[1])
    if not export_path.exists():
        print(f"Error: Export path does not exist: {export_path}")
        sys.exit(1)

    main(export_path)
