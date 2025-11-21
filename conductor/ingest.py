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

        # Check if it looks like a DM directory (starts with D)
        if dir_name.startswith("D") and len(dir_name) > 1:
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
                logger.debug(f"Attachment not found for file {file_id} in {conversation_dir.name}")
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
            except Exception as e:
                logger.warning(f"Failed to process attachment {filename}: {e}")
                enriched_parts.append(f"<<< ATTACHMENT START: {filename} >>>")
                enriched_parts.append(f"[ERROR: Could not parse file {filename}]")
                enriched_parts.append("<<< ATTACHMENT END >>>")

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
        file_count=session.file_count,
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
        logger.info("No sessions to store")
        return

    try:
        # Initialize persistent ChromaDB client
        client = chromadb.PersistentClient(path=str(db_path))

        # Get or create collection (idempotent)
        collection = client.get_or_create_collection(
            name="conductor_sessions",
            metadata={"description": "Real Estate Slack conversation sessions"},
        )

        # Prepare data for upsert
        ids = []
        documents = []
        metadatas = []

        for session in sessions:
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

        # Upsert to ChromaDB (idempotent)
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

        logger.info(f"Stored {len(sessions)} sessions in ChromaDB at {db_path}")

    except Exception as e:
        logger.exception(f"Failed to store sessions in ChromaDB: {e}")
        raise


def main(export_path: Path) -> None:
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
    """
    logger.info(f"Starting ingestion from {export_path}")

    # Step 1: Identity Mapping
    logger.info("Step 1: Identity Mapping")
    try:
        user_map = load_users(export_path)
    except Exception as e:
        logger.error(f"Failed to load users: {e}")
        raise

    # Step 2: Conversation Discovery
    logger.info("Step 2: Conversation Discovery")
    try:
        conversations = discover_conversations(export_path)
    except Exception as e:
        logger.error(f"Failed to discover conversations: {e}")
        raise

    # Step 3 & 4: Process each conversation (Timeline, Sessionization, File Enrichment)
    logger.info("Step 3 & 4: Timeline, Sessionization, and File Enrichment")
    all_sessions: List[Session] = []

    for dir_name, conversation_type in conversations.items():
        conversation_dir = export_path / dir_name

        if not conversation_dir.exists():
            logger.warning(f"Conversation directory not found: {conversation_dir}")
            continue

        try:
            # Load messages from conversation directory
            messages = load_messages_from_directory(conversation_dir)

            if not messages:
                logger.debug(f"No messages found in {dir_name}")
                continue

            # Get channel name for session
            channel_name = get_channel_name_for_session(dir_name, conversation_type)

            # Sessionize messages
            sessions = sessionize_messages(messages, channel_name, conversation_type, user_map)

            # Enrich each session with file content
            enriched_sessions = []
            for session in sessions:
                # Get messages for this session (by matching timestamps)
                # Use a small epsilon to handle floating point precision issues
                session_start_ts = session.start_time.timestamp()
                session_end_ts = session.end_time.timestamp()
                session_messages = [
                    msg
                    for msg in messages
                    if session_start_ts - 1.0 <= float(msg.ts) <= session_end_ts + 1.0
                ]
                enriched_session = enrich_session_with_files(session, session_messages, conversation_dir)
                enriched_sessions.append(enriched_session)

            all_sessions.extend(enriched_sessions)
            logger.info(f"Processed {dir_name}: {len(enriched_sessions)} sessions")

        except Exception as e:
            logger.error(f"Failed to process conversation {dir_name}: {e}")
            # Continue processing other conversations - don't stop on errors
            continue

    # Step 5: Vectorization & Storage
    logger.info(f"Step 5: Vectorization & Storage ({len(all_sessions)} sessions)")
    try:
        store_sessions_in_chromadb(all_sessions)
    except Exception as e:
        logger.error(f"Failed to store sessions in ChromaDB: {e}")
        raise

    logger.info(f"Ingestion complete! Processed {len(all_sessions)} sessions")


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
