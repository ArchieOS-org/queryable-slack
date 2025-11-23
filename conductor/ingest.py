"""
Main ingestion orchestration.

Entry point for the 5-step ingestion pipeline.
"""

# CRITICAL: Output IMMEDIATELY before ANY imports - this must be first!
import sys
import os
# Force unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'
# Suppress tokenizer parallelism warnings (harmless but noisy)
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(line_buffering=True)
    except:
        pass

# Immediate output - write directly to file descriptor if possible
try:
    sys.stdout.write("🔧 Loading conductor.ingest module...\n")
    sys.stdout.flush()
except:
    pass

import glob
import hashlib
import json
import logging
import os
import re  # Required for discover_conversations function
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Lazy import multiprocessing to avoid blocking
_multiprocessing = None
def _get_multiprocessing():
    global _multiprocessing
    if _multiprocessing is None:
        import multiprocessing
        _multiprocessing = multiprocessing
    return _multiprocessing

# Lazy import chromadb to avoid blocking
_chromadb = None
def _get_chromadb():
    global _chromadb
    if _chromadb is None:
        import chromadb
        _chromadb = chromadb
    return _chromadb

from conductor.file_parser import extract_text_from_file, extract_file_metadata
from conductor.models import Session, SlackMessage, UserMap
from conductor.processor import load_messages_from_directory, sessionize_messages
from conductor.user_mapper import load_users
from conductor.monitoring import track_file_processing, track_ingestion
from conductor.chunking import chunk_session, should_chunk_session
from conductor.config import DEFAULT_DB_PATH
from conductor.checkpoint import CheckpointManager, get_already_processed_channels

# Rich progress bar imports
try:
    from rich.progress import (
        Progress,
        TextColumn,
        BarColumn,
        TaskProgressColumn,
        TimeElapsedColumn,
        ProgressColumn,
    )
    from rich.text import Text
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class TimeRemainingDaysColumn(ProgressColumn):
    """Custom column that displays time remaining in days:hours:minutes format."""
    
    max_refresh = 0.5  # Refresh twice per second to prevent jitter
    
    def render(self, task) -> Text:
        """Show time remaining in days:hours:minutes format."""
        if task.total is None:
            return Text("", style="progress.remaining")
        
        task_time = task.time_remaining
        
        if task_time is None:
            return Text("--:--:--", style="progress.remaining")
        
        # Calculate days, hours, minutes
        total_seconds = int(task_time)
        days, remainder = divmod(total_seconds, 86400)  # 86400 seconds in a day
        hours, remainder = divmod(remainder, 3600)      # 3600 seconds in an hour
        minutes, _ = divmod(remainder, 60)
        
        # Format: days:hours:minutes (only show days if > 0)
        if days > 0:
            formatted = f"{days}d:{hours:02d}h:{minutes:02d}m"
        else:
            formatted = f"{hours:02d}h:{minutes:02d}m"
        
        return Text(formatted, style="progress.remaining")

print("✅ Module imports complete", file=sys.stdout, flush=True)

# Performance optimization: Limit to P-cores on M2 Max (8 P-cores)
# macOS will use E-cores for lighter tasks automatically
# Lazy initialization to avoid blocking at import time
def get_max_workers():
    """Get max workers, avoiding blocking at module import time."""
    try:
        multiprocessing = _get_multiprocessing()
        return min(8, multiprocessing.cpu_count())  # M2 Max has 8 P-cores
    except Exception:
        return 4  # Safe fallback
MAX_WORKERS = None  # Will be initialized lazily

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configure logging to suppress noisy warnings
logging.getLogger("conductor.video_processor").setLevel(logging.INFO)  # Suppress DEBUG FFmpeg messages
logging.getLogger("conductor.audio_processor").setLevel(logging.INFO)  # Suppress DEBUG audio messages
logging.getLogger("pypdf").setLevel(logging.ERROR)  # Suppress pypdf warnings


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
    logger.info(f"Scanning directory: {export_path}")
    print(f"   Scanning directory: {export_path}", flush=True)
    
    try:
        items = list(export_path.iterdir())
        logger.info(f"Found {len(items)} items in export directory")
        print(f"   Found {len(items)} items to scan", flush=True)
    except Exception as e:
        logger.error(f"Failed to list directory contents: {e}")
        print(f"   ❌ Error listing directory: {e}", flush=True)
        raise
    
    processed = 0
    for item in items:
        processed += 1
        if processed % 50 == 0:
            logger.debug(f"Processed {processed}/{len(items)} items...")
            print(f"   Processed {processed}/{len(items)} items...", flush=True)
        
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
        if re.match(r"^D[A-Z0-9]{8,}$", dir_name):
            conversations[dir_name] = "dm"
            continue

    logger.info(f"Discovered {len(conversations)} conversations")
    print(f"   ✅ Discovered {len(conversations)} conversations", flush=True)
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
    session: Session, messages: List[SlackMessage], conversation_dir: Path, checkpoint: Optional[CheckpointManager] = None
) -> Session:
    """
    Enrich a session's transcript with file content.

    Args:
        session: Session to enrich
        messages: List of SlackMessage objects in the session
        conversation_dir: Path to conversation directory
        checkpoint: Optional checkpoint manager for tracking file failures

    Returns:
        Enriched Session object
    """
    # Store checkpoint in function attribute for access in nested scope (for backward compatibility)
    if checkpoint:
        enrich_session_with_files._checkpoint = checkpoint
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
            # Try multiple patterns in order of likelihood:
            # 1. {FILE_ID}-{filename} (most common)
            # 2. {FILE_ID}-{filename} with URL encoding
            # 3. {FILE_ID}* (file_id as prefix)
            # 4. Exact filename match (fallback)
            matching_files = []
            
            # Pattern 1: {FILE_ID}-{filename}
            attachment_pattern = f"{file_id}-*"
            matching_files = list(attachments_dir.glob(attachment_pattern))

            # Pattern 2: {FILE_ID}* (file_id as prefix - handles partial matches)
            if not matching_files:
                matching_files = list(attachments_dir.glob(f"{file_id}*"))

            # Pattern 3: Try exact filename match (in case file_id pattern doesn't work)
            if not matching_files:
                exact_match = attachments_dir / filename
                if exact_match.exists():
                    matching_files = [exact_match]
            
            # Pattern 4: Try filename with file_id prefix variations
            if not matching_files:
                # Try {file_id}_{filename} (underscore instead of dash)
                alt_pattern = f"{file_id}_*"
                matching_files = list(attachments_dir.glob(alt_pattern))
            
            if not matching_files:
                logger.debug(f"Attachment not found for file {file_id} ({filename}) in {conversation_dir.name}")
                files_skipped += 1
                continue

            # Use first match (most specific pattern wins)
            attachment_file = matching_files[0]
            if len(matching_files) > 1:
                logger.debug(f"Multiple matches for {file_id}, using: {attachment_file.name}")

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

            # Extract metadata for all files
            file_metadata = None
            try:
                file_metadata = extract_file_metadata(attachment_file, file_type)
            except Exception as e:
                logger.debug(f"  Could not extract metadata for {filename}: {e}")

            # Check if this file was previously failed and should be retried
            file_path_str = str(attachment_file)
            checkpoint = getattr(enrich_session_with_files, '_checkpoint', None)
            should_retry_file = False
            if checkpoint and checkpoint.is_file_failed(file_path_str):
                should_retry_file = True
                failed_info = checkpoint.get_failed_files().get(file_path_str, {})
                logger.info(f"  🔄 Retrying previously failed file: {filename} (attempt {failed_info.get('retry_count', 0) + 1})")
            
            # Extract text from file
            try:
                file_content = extract_text_from_file(attachment_file, file_type)
                
                # Always include file metadata in the enriched transcript
                # Make file type information prominent for semantic search
                # Use file_metadata file_type if available, otherwise use inferred file_type
                detected_file_type = file_metadata.get('file_type', file_type) if file_metadata else file_type
                file_type_upper = detected_file_type.upper()
                
                # Create prominent file type markers for semantic search
                file_type_descriptions = {
                    'csv': f'CSV file spreadsheet data: {filename}',
                    'xlsx': f'Excel spreadsheet XLSX file: {filename}',
                    'xls': f'Excel spreadsheet XLS file: {filename}',
                    'pptx': f'PowerPoint presentation PPTX file: {filename}',
                    'ppt': f'PowerPoint presentation PPT file: {filename}',
                    'pdf': f'PDF document: {filename}',
                    'docx': f'Word document DOCX file: {filename}',
                    'doc': f'Word document DOC file: {filename}',
                    'txt': f'Text file: {filename}',
                    'zip': f'ZIP archive file: {filename}',
                    'png': f'PNG image file: {filename}',
                    'jpg': f'JPEG image file: {filename}',
                    'jpeg': f'JPEG image file: {filename}',
                    'mp4': f'MP4 video file: {filename}',
                    'mov': f'MOV video file: {filename}',
                    'mp3': f'MP3 audio file: {filename}',
                    'wav': f'WAV audio file: {filename}',
                }
                
                file_type_label = file_type_descriptions.get(detected_file_type.lower(), f'{file_type_upper} file: {filename}')
                
                metadata_str = ""
                if file_metadata:
                    metadata_str = f"File type: {file_type_upper} | File metadata: {detected_file_type}, {file_metadata['size']} bytes"
                    if file_metadata.get('modified'):
                        metadata_str += f", modified: {file_metadata['modified']}"
                    metadata_str += "\n"
                
                # Check if file was processed (includes video/audio processing)
                is_processed = (
                    file_content and 
                    not file_content.startswith("[SKIPPED:") and 
                    not file_content.startswith("[ERROR:") and
                    (file_content.startswith("[VIDEO_PROCESSED:") or 
                     file_content.startswith("[AUDIO_PROCESSED:") or
                     len(file_content.strip()) > 50)  # Has substantial content
                )
                
                if is_processed:
                    enriched_parts.append(f"<<< ATTACHMENT START: {filename} ({file_type_upper} FILE) >>>")
                    enriched_parts.append(file_type_label)  # Prominent file type label
                    enriched_parts.append(metadata_str)
                    enriched_parts.append(file_content)
                    enriched_parts.append("<<< ATTACHMENT END >>>")
                    files_processed += 1
                    track_file_processing(detected_file_type, success=True)
                    logger.debug(f"  ✅ Processed attachment: {filename}")
                    
                    # Mark file as successful in checkpoint if it was previously failed
                    if checkpoint and should_retry_file:
                        checkpoint.mark_file_success(file_path_str)
                        logger.info(f"  ✅ Successfully retried file: {filename}")
                else:
                    # Check if file processing failed (not just skipped)
                    is_error = (
                        file_content.startswith("[ERROR:") or
                        file_content.startswith("[SKIPPED:") and "processing failed" in file_content.lower()
                    )
                    
                    # Even skipped files get metadata included
                    enriched_parts.append(f"<<< ATTACHMENT START: {filename} ({file_type_upper} FILE) >>>")
                    enriched_parts.append(file_type_label)  # Prominent file type label
                    enriched_parts.append(metadata_str)
                    enriched_parts.append(file_content)  # Contains structured skip message
                    enriched_parts.append("<<< ATTACHMENT END >>>")
                    
                    if is_error:
                        files_error += 1
                        error_type = "processing_failed"
                        # Extract error type from content if possible
                        if "FFmpeg error" in file_content:
                            error_type = "ffmpeg_error"
                        elif "Failed to transcribe" in file_content:
                            error_type = "audio_transcription_error"
                        elif "cannot write mode RGBA" in file_content:
                            error_type = "rgba_jpeg_error"
                        elif "unknown file extension" in file_content:
                            error_type = "unsupported_format"
                        elif "partition_docx" in file_content:
                            error_type = "docx_parse_error"
                        
                        # Track file failure in checkpoint
                        if checkpoint:
                            checkpoint.mark_file_failed(
                                file_path_str,
                                file_content[:200],  # First 200 chars of error
                                error_type,
                                conversation_dir.name
                            )
                        track_file_processing(detected_file_type, success=False, error_type=error_type)
                        logger.warning(f"  ⚠️  Failed to process attachment {filename}: {error_type}")
                    else:
                        files_skipped += 1
                        track_file_processing(detected_file_type, success=False, error_type="skipped")
                        logger.debug(f"  ⏭️  Skipped attachment: {filename}")
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                logger.warning(f"  ⚠️  Failed to process attachment {filename}: {error_msg}")
                enriched_parts.append(f"<<< ATTACHMENT START: {filename} >>>")
                if file_metadata:
                    metadata_str = f"File metadata: {file_metadata['file_type']}, {file_metadata['size']} bytes\n"
                    enriched_parts.append(metadata_str)
                enriched_parts.append(f"[ERROR: Could not parse file {filename}]")
                enriched_parts.append("<<< ATTACHMENT END >>>")
                files_error += 1
                
                # Track file failure in checkpoint
                if checkpoint:
                    checkpoint.mark_file_failed(
                        file_path_str,
                        error_msg,
                        error_type,
                        conversation_dir.name
                    )
                
                track_file_processing(detected_file_type, success=False, error_type=error_type)

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


def store_sessions_in_chromadb(sessions: List[Session], db_path: Path = DEFAULT_DB_PATH) -> None:
    """
    Store sessions in vector database (ChromaDB or Supabase vecs).

    Args:
        sessions: List of Session objects to store
        db_path: Path to ChromaDB persistent storage directory (ignored if using vecs)
    """
    if not sessions:
        logger.info("⚠️  No sessions to store")
        print("⚠️  No sessions to store")
        return

    # Check if we should use vecs (Supabase)
    from conductor.config import USE_VECS
    if USE_VECS:
        _store_sessions_in_vecs(sessions)
        return

    # Otherwise use ChromaDB
    try:
        logger.info(f"💾 Initializing ChromaDB at {db_path}")
        print(f"💾 Initializing ChromaDB database...", flush=True)
        sys.stdout.flush()
        
        # Initialize persistent ChromaDB client (lazy import)
        chromadb = _get_chromadb()
        client = chromadb.PersistentClient(path=str(db_path))

        # Get or create collection (idempotent)
        logger.info("📚 Creating/accessing collection 'conductor_sessions'...")
        collection = client.get_or_create_collection(
            name="conductor_sessions",
            metadata={"description": "Real Estate Slack conversation sessions"},
        )

        # Prepare data for upsert (with chunking support)
        logger.info(f"📝 Preparing {len(sessions)} sessions for storage...")
        print(f"📝 Preparing {len(sessions)} sessions for vector storage...")
        ids = []
        documents = []
        metadatas = []
        chunked_count = 0

        for idx, session in enumerate(sessions, 1):
            if idx % 10 == 0 or idx == len(sessions):
                logger.debug(f"  Preparing session {idx}/{len(sessions)}: {session.channel_name}")
                print(f"  Processing session {idx}/{len(sessions)}...", end="\r")
            
            # Check if session needs chunking
            if should_chunk_session(session):
                chunks = chunk_session(session)
                chunked_count += 1
                logger.debug(f"  Chunked session {session.session_id} into {len(chunks)} chunks")
                
                for chunk in chunks:
                    ids.append(chunk["chunk_id"])
                    documents.append(chunk["enriched_transcript"])
                    metadatas.append(
                        {
                            "date": chunk["start_time"].date().isoformat(),
                            "channel": chunk["channel_name"],
                            "start_time": chunk["start_time"].isoformat(),
                            "end_time": chunk["end_time"].isoformat(),
                            "message_count": chunk["message_count"],
                            "file_count": chunk["file_count"],
                            "conversation_type": chunk["conversation_type"],
                            "session_id": chunk["session_id"],
                            "chunk_index": chunk["chunk_index"],
                            "total_chunks": chunk["total_chunks"],
                        }
                    )
            else:
                # Regular session, no chunking needed
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
        
        if chunked_count > 0:
            logger.info(f"📦 Chunked {chunked_count} large sessions")
            print(f"📦 Chunked {chunked_count} large sessions")

        print()  # New line after progress
        logger.info(f"🔢 Generating embeddings and storing in ChromaDB...")
        print(f"🔢 Generating embeddings (this may take a moment)...")
        
        # Upsert to ChromaDB in batches (ChromaDB has a max batch size limit)
        # Use batch size of 5000 to stay safely under the limit (5461)
        batch_size = 5000
        total_items = len(ids)
        
        for i in range(0, total_items, batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_documents = documents[i:i + batch_size]
            batch_metadatas = metadatas[i:i + batch_size]
            
            batch_num = (i // batch_size) + 1
            total_batches = (total_items + batch_size - 1) // batch_size
            
            if total_batches > 1:
                print(f"  Storing batch {batch_num}/{total_batches} ({len(batch_ids)} items)...", end="\r")
            
            collection.upsert(ids=batch_ids, documents=batch_documents, metadatas=batch_metadatas)
        
        if total_batches > 1:
            print()  # New line after progress

        logger.info(f"✅ Stored {len(sessions)} sessions in ChromaDB at {db_path}")
        print(f"✅ Stored {len(sessions)} sessions in ChromaDB")

    except Exception as e:
        logger.exception(f"❌ Failed to store sessions in ChromaDB: {e}")
        print(f"❌ Error storing sessions: {e}")
        raise


def _store_sessions_in_vecs(sessions: List[Session]) -> None:
    """
    Store sessions in Supabase vecs (pgvector) for vector search.
    
    Args:
        sessions: List of Session objects to store
    """
    try:
        from conductor.vecs_client import upsert_vecs
        from conductor.chunking import should_chunk_session, chunk_session
        
        logger.info("💾 Initializing Supabase vecs (pgvector)...")
        print(f"💾 Initializing Supabase vecs database...", flush=True)
        sys.stdout.flush()
        
        # Prepare data for upsert (with chunking support)
        logger.info(f"📝 Preparing {len(sessions)} sessions for storage...")
        print(f"📝 Preparing {len(sessions)} sessions for vector storage...")
        records = []
        chunked_count = 0
        
        for idx, session in enumerate(sessions, 1):
            if idx % 10 == 0 or idx == len(sessions):
                logger.debug(f"  Preparing session {idx}/{len(sessions)}: {session.channel_name}")
                print(f"  Processing session {idx}/{len(sessions)}...", end="\r")
            
            # Check if session needs chunking
            if should_chunk_session(session):
                chunks = chunk_session(session)
                chunked_count += 1
                logger.debug(f"  Chunked session {session.session_id} into {len(chunks)} chunks")
                
                for chunk in chunks:
                    metadata = {
                        "date": chunk["start_time"].date().isoformat(),
                        "channel": chunk["channel_name"],
                        "start_time": chunk["start_time"].isoformat(),
                        "end_time": chunk["end_time"].isoformat(),
                        "message_count": chunk["message_count"],
                        "file_count": chunk["file_count"],
                        "conversation_type": chunk["conversation_type"],
                        "session_id": chunk["session_id"],
                        "chunk_index": chunk["chunk_index"],
                        "total_chunks": chunk["total_chunks"],
                    }
                    records.append((
                        chunk["chunk_id"],
                        chunk["enriched_transcript"],
                        metadata
                    ))
            else:
                # Regular session, no chunking needed
                metadata = {
                    "date": session.start_time.date().isoformat(),
                    "channel": session.channel_name,
                    "start_time": session.start_time.isoformat(),
                    "end_time": session.end_time.isoformat(),
                    "message_count": session.message_count,
                    "file_count": session.file_count,
                    "conversation_type": session.conversation_type,
                }
                records.append((
                    session.session_id,
                    session.enriched_transcript,
                    metadata
                ))
        
        if chunked_count > 0:
            logger.info(f"📦 Chunked {chunked_count} large sessions")
            print(f"📦 Chunked {chunked_count} large sessions")
        
        print()  # New line after progress
        logger.info(f"🔢 Generating embeddings and storing in Supabase vecs...")
        print(f"🔢 Generating embeddings (this may take a moment)...")
        
        # Upsert to vecs in batches (vecs handles batching internally, but we'll batch for progress tracking)
        batch_size = 1000  # Reasonable batch size for vecs
        total_items = len(records)
        total_batches = (total_items + batch_size - 1) // batch_size
        
        for i in range(0, total_items, batch_size):
            batch_records = records[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            if total_batches > 1:
                print(f"  Storing batch {batch_num}/{total_batches} ({len(batch_records)} items)...", end="\r")
            
            upsert_vecs(batch_records)
        
        if total_batches > 1:
            print()  # New line after progress
        
        logger.info(f"✅ Stored {len(sessions)} sessions in Supabase vecs")
        print(f"✅ Stored {len(sessions)} sessions in Supabase vecs")
        
    except Exception as e:
        logger.exception(f"❌ Failed to store sessions in vecs: {e}")
        print(f"❌ Error storing sessions: {e}")
        raise


def main(export_path: Path, db_path: Optional[Path] = None, clear_checkpoint: bool = False) -> None:
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
        clear_checkpoint: If True, clear checkpoint and start fresh
    """
    # CRITICAL: Force immediate output with explicit flushing
    import sys
    
    # Ensure unbuffered output
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(line_buffering=True)
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(line_buffering=True)
    
    # Immediate output - use file=sys.stdout for explicit flushing
    print("\n" + "=" * 80, file=sys.stdout, flush=True)
    print("🚀 CONDUCTOR INGESTION PIPELINE", file=sys.stdout, flush=True)
    print("=" * 80, file=sys.stdout, flush=True)
    
    start_time = datetime.now()
    timestamp = start_time.strftime("%Y%m%d_%H%M%S")
    
    # Use default database path if not provided
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    print(f"📂 Source: {export_path}", file=sys.stdout, flush=True)
    print(f"💾 Database: {db_path}", file=sys.stdout, flush=True)
    print(f"⏱️  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stdout, flush=True)
    print("=" * 80 + "\n", file=sys.stdout, flush=True)
    
    # Also log for file-based logging
    logger.info("=" * 80)
    logger.info("INGESTION PIPELINE")
    logger.info("=" * 80)
    logger.info(f"📂 Source export: {export_path}")
    logger.info(f"💾 Database path: {db_path}")
    logger.info(f"⏱️  Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)
    
    logger.info("=" * 80)
    logger.info("INGESTION PIPELINE")
    logger.info("=" * 80)
    logger.info(f"📂 Source export: {export_path}")
    logger.info(f"💾 Database path: {db_path}")
    logger.info(f"⏱️  Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    # Step 1: Identity Mapping
    print("📋 Step 1/5: Identity Mapping...", flush=True)
    sys.stdout.flush()
    logger.info("=" * 80)
    logger.info("STEP 1: Identity Mapping")
    logger.info("=" * 80)
    try:
        logger.info("Loading user mappings from users.json...")
        user_map = load_users(export_path)
        logger.info(f"✅ Loaded {len(user_map)} users")
        print(f"✅ Loaded {len(user_map)} users", flush=True)
        sys.stdout.flush()
    except Exception as e:
        logger.exception(f"❌ Failed to load users: {e}")
        print(f"❌ Error loading users: {e}")
        raise

    # Step 2: Conversation Discovery
    print("\n🔍 Step 2/5: Conversation Discovery...", flush=True)
    sys.stdout.flush()
    logger.info("=" * 80)
    logger.info("STEP 2: Conversation Discovery")
    logger.info("=" * 80)
    try:
        logger.info("Scanning export directory for conversations...")
        conversations = discover_conversations(export_path)
        logger.info(f"✅ Discovered {len(conversations)} conversations")
        print(f"✅ Discovered {len(conversations)} conversations", flush=True)
        sys.stdout.flush()
        
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
    print(f"\n📝 Step 3-4/5: Processing conversations...", flush=True)
    sys.stdout.flush()
    logger.info("=" * 80)
    logger.info("STEP 3 & 4: Timeline, Sessionization, and File Enrichment")
    logger.info("=" * 80)
    
    # Initialize checkpoint manager for resume/retry
    checkpoint = CheckpointManager()
    
    # Clear checkpoint if requested
    if clear_checkpoint:
        checkpoint.clear()
        print("🗑️  Checkpoint cleared - starting fresh ingestion", flush=True)
        logger.info("🗑️  Checkpoint cleared - starting fresh ingestion")
    
    checkpoint_stats = checkpoint.get_stats()
    failed_files_stats = checkpoint.get_failed_files_stats()
    
    # Display checkpoint status
    if checkpoint_stats["completed"] > 0 or checkpoint_stats["failed"] > 0 or len(failed_files_stats) > 0:
        print(f"\n📊 Checkpoint Status:", flush=True)
        if checkpoint_stats["completed"] > 0:
            print(f"   ✅ {checkpoint_stats['completed']} conversations completed", flush=True)
        if checkpoint_stats["failed"] > 0:
            print(f"   ❌ {checkpoint_stats['failed']} conversations failed (will retry)", flush=True)
        if len(failed_files_stats) > 0:
            total_failed_files = sum(failed_files_stats.values())
            print(f"   ⚠️  {total_failed_files} files failed (will retry):", flush=True)
            for error_type, count in sorted(failed_files_stats.items(), key=lambda x: -x[1]):
                print(f"      - {error_type}: {count}", flush=True)
        print()
    
    # Get already processed channels from ChromaDB
    already_processed_channels = get_already_processed_channels(db_path)
    
    # Filter conversations: skip completed, include failed for retry
    conversations_to_process = {}
    skipped_count = 0
    retry_count = 0
    
    for dir_name, conv_type in conversations.items():
        # Check if already completed in checkpoint
        if checkpoint.is_completed(dir_name):
            skipped_count += 1
            logger.debug(f"⏭️  Skipping {dir_name} (already completed)")
            continue
        
        # Check if channel already in ChromaDB (by checking if any sessions exist)
        # We'll check this more precisely per conversation
        conversations_to_process[dir_name] = conv_type
        
        # Count retries
        if dir_name in checkpoint.get_failed():
            retry_count += 1
    
    if skipped_count > 0:
        print(f"⏭️  Skipping {skipped_count} already completed conversations", flush=True)
        logger.info(f"⏭️  Skipping {skipped_count} already completed conversations")
    
    if retry_count > 0:
        print(f"🔄 Retrying {retry_count} previously failed conversations", flush=True)
        logger.info(f"🔄 Retrying {retry_count} previously failed conversations")
    
    if not conversations_to_process:
        print("✅ All conversations already processed!", flush=True)
        logger.info("✅ All conversations already processed!")
        return
    
    print(f"📋 Processing {len(conversations_to_process)} conversations ({len(conversations)} total)", flush=True)
    logger.info(f"📋 Processing {len(conversations_to_process)} conversations ({len(conversations)} total)")
    
    all_sessions: List[Session] = []
    total_messages = 0
    total_files = 0

    # Create elegant progress bar (Steve Jobs style)
    # Detect if we're in a TTY (interactive terminal) or redirected to file
    is_tty = sys.stdout.isatty() if hasattr(sys.stdout, 'isatty') else False
    
    if RICH_AVAILABLE and is_tty:
        # Interactive terminal - use Rich progress bars
        progress = Progress(
            TextColumn("[bold cyan]{task.description}", justify="left"),
            BarColumn(bar_width=None),
            TaskProgressColumn(),  # Shows "x/y"
            TextColumn("•", style="dim"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%", style="bold"),
            TextColumn("•", style="dim"),
            TimeElapsedColumn(),
            TextColumn("•", style="dim"),
            TimeRemainingDaysColumn(),  # Custom: days:hours:minutes
            console=Console(file=sys.stdout),
            expand=True,
        )
        progress.start()
        main_task = progress.add_task(
            "[bold cyan]Processing conversations",
            total=len(conversations_to_process)
        )
    else:
        # File output or Rich not available - use simple logging
        progress = None
        main_task = None
        print(f"📊 Processing {len(conversations_to_process)} conversations...", flush=True)
        logger.info(f"📊 Processing {len(conversations_to_process)} conversations")

    try:
        for idx, (dir_name, conversation_type) in enumerate(conversations_to_process.items(), 1):
            conversation_dir = export_path / dir_name
            
            # Update progress bar
            if progress and main_task is not None:
                progress.update(
                    main_task,
                    description=f"[bold cyan]{dir_name[:50]}",
                    completed=idx - 1,
                    refresh=True
                )
            elif not is_tty:
                # Simple progress for file output - more frequent updates with ETA
                pct = int((idx / len(conversations_to_process)) * 100)
                elapsed = (datetime.now() - start_time).total_seconds()
                if idx > 1:
                    avg_time_per_conv = elapsed / idx
                    remaining_convos = len(conversations_to_process) - idx
                    eta_seconds = avg_time_per_conv * remaining_convos
                    eta_days = int(eta_seconds // 86400)
                    eta_hours = int((eta_seconds % 86400) // 3600)
                    eta_mins = int((eta_seconds % 3600) // 60)
                    if eta_days > 0:
                        eta_str = f"{eta_days}d:{eta_hours:02d}h:{eta_mins:02d}m"
                    else:
                        eta_str = f"{eta_hours:02d}h:{eta_mins:02d}m"
                    print(f"   [{idx}/{len(conversations_to_process)}] {pct}% | ETA: {eta_str} | {dir_name}", flush=True)
                else:
                    print(f"   [{idx}/{len(conversations_to_process)}] {pct}% | {dir_name}", flush=True)
            
            # Also log for file-based logging
            logger.info(f"[{idx}/{len(conversations_to_process)}] Processing: {dir_name} ({conversation_type})")

            if not conversation_dir.exists():
                logger.warning(f"⚠️  Conversation directory not found: {conversation_dir}")
                if progress and main_task is not None:
                    progress.console.print(f"[yellow]⚠️  Directory not found, skipping[/]")
                continue

            try:
                # Load messages from conversation directory
                logger.debug(f"  Loading messages from {dir_name}...")
                messages = load_messages_from_directory(conversation_dir)
                total_messages += len(messages)

                if not messages:
                    logger.debug(f"  No messages found in {dir_name}")
                    if progress and main_task is not None:
                        progress.console.print(f"[dim]ℹ️  No messages found, skipping[/]")
                    continue

                logger.info(f"  Loaded {len(messages)} messages")
                if progress and main_task is not None:
                    progress.console.print(f"[dim]📨 Loaded {len(messages)} messages[/]")

                # Get channel name for session
                channel_name = get_channel_name_for_session(dir_name, conversation_type)

                # Sessionize messages
                logger.debug(f"  Sessionizing messages...")
                sessions = sessionize_messages(messages, channel_name, conversation_type, user_map)
                logger.info(f"  Created {len(sessions)} sessions")
                if progress and main_task is not None:
                    progress.console.print(f"[dim]📦 Created {len(sessions)} sessions[/]")

                # Enrich each session with file content
                logger.debug(f"  Enriching sessions with file content...")
                enriched_sessions = []
                files_in_conversation = 0
                
                # Nested progress for sessions (transient - disappears when done)
                # Only use Rich if we're in a TTY
                if RICH_AVAILABLE and is_tty and len(sessions) > 1:
                    session_progress = Progress(
                        TextColumn("[dim]{task.description}", justify="left"),
                        BarColumn(bar_width=None),
                        TaskProgressColumn(),
                        TextColumn("•", style="dim"),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%", style="dim"),
                        console=Console(file=sys.stdout),
                        transient=True,  # Disappears when done
                    )
                    session_progress.start()
                    session_task = session_progress.add_task(
                        f"[dim]Enriching sessions",
                        total=len(sessions)
                    )
                else:
                    session_progress = None
                    session_task = None
                    if len(sessions) > 1:
                        print(f"   📦 Enriching {len(sessions)} sessions...", flush=True)
                
                try:
                    for session_idx, session in enumerate(sessions, 1):
                        # Get messages for this session (by matching timestamps)
                        session_start_ts = session.start_time.timestamp()
                        session_end_ts = session.end_time.timestamp()
                        session_messages = [
                            msg
                            for msg in messages
                            if session_start_ts - 1.0 <= float(msg.ts) <= session_end_ts + 1.0
                        ]
                        enriched_session = enrich_session_with_files(session, session_messages, conversation_dir, checkpoint)
                        enriched_sessions.append(enriched_session)
                        files_in_conversation += enriched_session.file_count
                        
                        # Update session progress
                        if session_progress and session_task is not None:
                            session_progress.update(session_task, completed=session_idx, refresh=True)
                        
                        if session_idx % 5 == 0 or session_idx == len(sessions):
                            logger.debug(f"    Enriched {session_idx}/{len(sessions)} sessions")
                finally:
                    if session_progress:
                        session_progress.stop()

                total_files += files_in_conversation
                all_sessions.extend(enriched_sessions)
                logger.info(f"  ✅ Processed {dir_name}: {len(enriched_sessions)} sessions, {files_in_conversation} files")
                
                # Mark as completed in checkpoint
                checkpoint.mark_completed(dir_name, len(enriched_sessions), files_in_conversation)
                
                # Update main progress
                if progress and main_task is not None:
                    progress.update(main_task, completed=idx, refresh=True)
                elif not is_tty:
                    # Simple progress for file output
                    pct = int((idx / len(conversations_to_process)) * 100)
                    print(f"   [{idx}/{len(conversations_to_process)}] {pct}% - {dir_name}", flush=True)

            except Exception as e:
                error_msg = str(e)
                logger.error(f"  ❌ Failed to process conversation {dir_name}: {error_msg}")
                if progress and main_task is not None:
                    progress.console.print(f"[red]❌ Error processing {dir_name}: {error_msg}[/]")
                else:
                    print(f"   ❌ Error processing {dir_name}: {error_msg}", flush=True)
                
                # Mark as failed in checkpoint (for retry later)
                checkpoint.mark_failed(dir_name, error_msg)
                
                # Continue processing other conversations - don't stop on errors
                continue
    finally:
        if progress:
            progress.stop()
        elif not is_tty:
            print(f"\n✅ Completed processing {len(conversations_to_process)} conversations", flush=True)

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
    duration_seconds = duration.total_seconds()
    
    # Track ingestion metrics
    track_ingestion(len(all_sessions), duration_seconds)
    
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
    # CRITICAL: Write directly to stdout file descriptor for immediate output
    import sys
    import os
    
    # Force unbuffered
    os.environ['PYTHONUNBUFFERED'] = '1'
    
    # Write directly to file descriptor 1 (stdout) - bypasses Python buffering
    try:
        os.write(1, "🚀 Conductor ingestion starting...\n".encode('utf-8'))
        os.fsync(1)
    except:
        sys.stdout.write("🚀 Conductor ingestion starting...\n")
        sys.stdout.flush()
    
    try:
        os.write(1, f"📋 Arguments: {sys.argv}\n".encode('utf-8'))
        os.fsync(1)
    except:
        print(f"📋 Arguments: {sys.argv}", flush=True)

    # Parse arguments
    clear_checkpoint = False
    if len(sys.argv) == 2:
        export_path = Path(sys.argv[1])
    elif len(sys.argv) == 3 and sys.argv[2] == "--clear-checkpoint":
        export_path = Path(sys.argv[1])
        clear_checkpoint = True
    else:
        try:
            usage = "Usage: python -m conductor.ingest <path_to_slack_export> [--clear-checkpoint]\n"
            os.write(2, usage.encode('utf-8'))
            os.fsync(2)
        except:
            print("Usage: python -m conductor.ingest <path_to_slack_export> [--clear-checkpoint]", file=sys.stderr, flush=True)
        sys.exit(1)
    try:
        os.write(1, f"📂 Checking export path: {export_path}\n".encode('utf-8'))
        os.fsync(1)
    except:
        print(f"📂 Checking export path: {export_path}", flush=True)
    
    if not export_path.exists():
        try:
            os.write(2, f"❌ Error: Export path does not exist: {export_path}\n".encode('utf-8'))
            os.fsync(2)
        except:
            print(f"❌ Error: Export path does not exist: {export_path}", file=sys.stderr, flush=True)
        sys.exit(1)

    try:
        os.write(1, f"✅ Export path found: {export_path}\n".encode('utf-8'))
        os.write(1, "🔄 Calling main()...\n".encode('utf-8'))
        os.fsync(1)
    except:
        print(f"✅ Export path found: {export_path}", flush=True)
        print("🔄 Calling main()...", flush=True)
    
    try:
        main(export_path, clear_checkpoint=clear_checkpoint)
    except Exception as e:
        try:
            os.write(2, f"❌ Fatal error: {e}\n".encode('utf-8'))
            import traceback
            os.write(2, traceback.format_exc().encode('utf-8'))
            os.fsync(2)
        except:
            print(f"❌ Fatal error: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
        sys.exit(1)
