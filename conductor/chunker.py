"""
Message-level chunking for Conductor.

Provides granular chunking strategies for Slack conversations:
- Session-level chunking (original approach - entire sessions)
- Message-level chunking (individual messages with context)
- Hybrid chunking (both session and message-level for different retrieval needs)

Note on ChromaDB metadata limitations:
- ChromaDB only supports string, number, or boolean metadata values
- Arrays must be stored as comma-separated strings
- Use where_document for text-based entity filtering
"""

import hashlib
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

from .models import Session, EnhancedVectorMetadata
from .entity_extractor import (
    extract_entities,
    group_entities_by_type,
    get_entity_list,
    ExtractionResult,
)

logger = logging.getLogger(__name__)

# Default chunking parameters (tuned for conversational data)
DEFAULT_CHUNK_SIZE = 800  # Characters - smaller for message-level precision
DEFAULT_CHUNK_OVERLAP = 150  # Characters - preserve context between chunks
DEFAULT_MESSAGES_PER_CHUNK = 5  # Messages per chunk for message-based splitting


class MessageChunk(BaseModel):
    """A single chunk of conversation with metadata."""

    chunk_id: str  # Deterministic ID based on parent + index
    parent_session_id: str  # ID of the source session
    chunk_index: int  # Position in parent session (0-indexed)
    text: str  # Chunk text content
    message_count: int  # Number of messages in this chunk
    start_time: Optional[str] = None  # ISO timestamp of first message
    end_time: Optional[str] = None  # ISO timestamp of last message

    # Entity metadata (stored as comma-separated strings for ChromaDB)
    entities_csv: str = ""  # All entities as "TYPE:value,TYPE:value,..."
    person_mentions_csv: str = ""  # "John,Jane,Bob"
    address_mentions_csv: str = ""  # "123 Main St,456 Oak Ave"

    # Full extraction result for processing
    extraction_result: Optional[ExtractionResult] = None

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True


def generate_chunk_id(parent_session_id: str, chunk_index: int) -> str:
    """
    Generate deterministic chunk ID for idempotency.

    Args:
        parent_session_id: ID of the parent session
        chunk_index: Position of chunk in session

    Returns:
        Deterministic hash-based ID
    """
    raw_id = f"{parent_session_id}_chunk_{chunk_index}"
    return hashlib.sha256(raw_id.encode()).hexdigest()[:16]


def chunk_by_messages(
    transcript: str,
    session_id: str,
    messages_per_chunk: int = DEFAULT_MESSAGES_PER_CHUNK,
    extract_entities_flag: bool = True,
) -> List[MessageChunk]:
    """
    Split transcript into chunks by message count.

    Strategy: Split on message boundaries (newlines) to preserve
    complete thoughts/messages.

    Args:
        transcript: Full session transcript
        session_id: Parent session ID
        messages_per_chunk: Number of messages per chunk
        extract_entities_flag: Whether to extract entities from chunks

    Returns:
        List of MessageChunk objects
    """
    if not transcript or not transcript.strip():
        return []

    # Split by newlines (each line is typically a message)
    lines = [line for line in transcript.split("\n") if line.strip()]

    if not lines:
        return []

    chunks = []
    for i in range(0, len(lines), messages_per_chunk):
        chunk_lines = lines[i : i + messages_per_chunk]
        chunk_text = "\n".join(chunk_lines)
        chunk_index = i // messages_per_chunk

        # Extract entities if requested
        extraction_result = None
        entities_csv = ""
        person_csv = ""
        address_csv = ""

        if extract_entities_flag and chunk_text:
            extraction_result = extract_entities(chunk_text, use_llm=False)
            grouped = group_entities_by_type(extraction_result.entities)

            # Convert to CSV format for ChromaDB compatibility
            entities_parts = []
            for entity_type, values in grouped.items():
                for value in values:
                    entities_parts.append(f"{entity_type}:{value}")
            entities_csv = ",".join(entities_parts)

            person_csv = ",".join(get_entity_list(extraction_result.entities, "PERSON"))
            address_csv = ",".join(get_entity_list(extraction_result.entities, "ADDRESS"))

        chunk = MessageChunk(
            chunk_id=generate_chunk_id(session_id, chunk_index),
            parent_session_id=session_id,
            chunk_index=chunk_index,
            text=chunk_text,
            message_count=len(chunk_lines),
            entities_csv=entities_csv,
            person_mentions_csv=person_csv,
            address_mentions_csv=address_csv,
            extraction_result=extraction_result,
        )
        chunks.append(chunk)

    logger.info(
        f"Created {len(chunks)} message chunks from session {session_id} "
        f"({len(lines)} messages, {messages_per_chunk} per chunk)"
    )
    return chunks


def chunk_by_characters(
    transcript: str,
    session_id: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    extract_entities_flag: bool = True,
) -> List[MessageChunk]:
    """
    Split transcript into chunks by character count with overlap.

    Uses a recursive splitting strategy that prefers semantic boundaries:
    1. Paragraph breaks (\\n\\n)
    2. Line breaks (\\n)
    3. Spaces
    4. Character-by-character (fallback)

    Args:
        transcript: Full session transcript
        session_id: Parent session ID
        chunk_size: Maximum characters per chunk
        chunk_overlap: Overlap between chunks
        extract_entities_flag: Whether to extract entities from chunks

    Returns:
        List of MessageChunk objects
    """
    if not transcript or not transcript.strip():
        return []

    # Separators in order of preference (most semantic to least)
    separators = ["\n\n", "\n", " ", ""]

    def split_text_recursive(text: str, separators: List[str]) -> List[str]:
        """Recursively split text on semantic boundaries."""
        if not separators:
            # Base case: character-level split
            return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size - chunk_overlap)]

        separator = separators[0]
        if not separator:
            # Empty separator = character split
            return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size - chunk_overlap)]

        splits = text.split(separator)

        # Merge small splits back together
        chunks = []
        current_chunk = ""

        for split in splits:
            # If adding this split would exceed chunk_size, start new chunk
            if len(current_chunk) + len(split) + len(separator) > chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                # If single split is too large, recurse with next separator
                if len(split) > chunk_size:
                    sub_chunks = split_text_recursive(split, separators[1:])
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = split
            else:
                if current_chunk:
                    current_chunk += separator + split
                else:
                    current_chunk = split

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    # Split the text
    text_chunks = split_text_recursive(transcript, separators)

    # Apply overlap by including end of previous chunk
    chunks_with_overlap = []
    for i, chunk_text in enumerate(text_chunks):
        if i > 0 and chunk_overlap > 0:
            # Get overlap from previous chunk
            prev_chunk = text_chunks[i - 1]
            overlap_text = prev_chunk[-chunk_overlap:] if len(prev_chunk) > chunk_overlap else prev_chunk
            chunk_text = overlap_text + " " + chunk_text

        chunks_with_overlap.append(chunk_text)

    # Create MessageChunk objects
    chunks = []
    for chunk_index, chunk_text in enumerate(chunks_with_overlap):
        if not chunk_text.strip():
            continue

        # Extract entities if requested
        extraction_result = None
        entities_csv = ""
        person_csv = ""
        address_csv = ""

        if extract_entities_flag:
            extraction_result = extract_entities(chunk_text, use_llm=False)
            grouped = group_entities_by_type(extraction_result.entities)

            entities_parts = []
            for entity_type, values in grouped.items():
                for value in values:
                    entities_parts.append(f"{entity_type}:{value}")
            entities_csv = ",".join(entities_parts)

            person_csv = ",".join(get_entity_list(extraction_result.entities, "PERSON"))
            address_csv = ",".join(get_entity_list(extraction_result.entities, "ADDRESS"))

        # Count messages (approximate by newlines)
        message_count = chunk_text.count("\n") + 1

        chunk = MessageChunk(
            chunk_id=generate_chunk_id(session_id, chunk_index),
            parent_session_id=session_id,
            chunk_index=chunk_index,
            text=chunk_text,
            message_count=message_count,
            entities_csv=entities_csv,
            person_mentions_csv=person_csv,
            address_mentions_csv=address_csv,
            extraction_result=extraction_result,
        )
        chunks.append(chunk)

    logger.info(
        f"Created {len(chunks)} character chunks from session {session_id} "
        f"(chunk_size={chunk_size}, overlap={chunk_overlap})"
    )
    return chunks


def chunk_session(
    session: Session,
    strategy: str = "messages",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    messages_per_chunk: int = DEFAULT_MESSAGES_PER_CHUNK,
    extract_entities_flag: bool = True,
) -> List[MessageChunk]:
    """
    Chunk a session using the specified strategy.

    Args:
        session: Session to chunk
        strategy: "messages" or "characters"
        chunk_size: For character strategy - max chars per chunk
        chunk_overlap: For character strategy - overlap between chunks
        messages_per_chunk: For message strategy - messages per chunk
        extract_entities_flag: Whether to extract entities

    Returns:
        List of MessageChunk objects
    """
    transcript = session.enriched_transcript or session.transcript

    if strategy == "messages":
        return chunk_by_messages(
            transcript=transcript,
            session_id=session.session_id,
            messages_per_chunk=messages_per_chunk,
            extract_entities_flag=extract_entities_flag,
        )
    elif strategy == "characters":
        return chunk_by_characters(
            transcript=transcript,
            session_id=session.session_id,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            extract_entities_flag=extract_entities_flag,
        )
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}. Use 'messages' or 'characters'.")


def chunk_to_metadata(
    chunk: MessageChunk,
    base_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convert MessageChunk to ChromaDB-compatible metadata.

    ChromaDB only supports string, number, or boolean values.
    Arrays are converted to comma-separated strings.

    Args:
        chunk: MessageChunk to convert
        base_metadata: Base metadata from parent session

    Returns:
        Dictionary of metadata suitable for ChromaDB
    """
    metadata = {
        **base_metadata,
        # Chunking metadata
        "is_chunk": True,
        "parent_session_id": chunk.parent_session_id,
        "chunk_index": chunk.chunk_index,
        "chunk_message_count": chunk.message_count,
        # Entity metadata (as CSV strings for ChromaDB compatibility)
        "entities": chunk.entities_csv,
        "person_mentions": chunk.person_mentions_csv,
        "address_mentions": chunk.address_mentions_csv,
    }

    # Add timestamps if available
    if chunk.start_time:
        metadata["chunk_start_time"] = chunk.start_time
    if chunk.end_time:
        metadata["chunk_end_time"] = chunk.end_time

    return metadata


def create_entity_filter(entity_value: str, entity_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a ChromaDB where_document filter for entity searching.

    Since ChromaDB doesn't support array filtering, we use document
    content filtering with $contains.

    Args:
        entity_value: Entity value to search for
        entity_type: Optional type to narrow search (PERSON, ADDRESS, etc.)

    Returns:
        where_document filter dict for ChromaDB query
    """
    # For now, just search in document content
    # The entity value should appear in the transcript
    return {"$contains": entity_value}


def create_metadata_filter(
    person: Optional[str] = None,
    address: Optional[str] = None,
    is_chunk: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Create a ChromaDB metadata filter for common queries.

    Args:
        person: Person name to filter by (searches in person_mentions CSV)
        address: Address to filter by (searches in address_mentions CSV)
        is_chunk: Filter for chunks vs full sessions

    Returns:
        where filter dict for ChromaDB query
    """
    conditions = []

    if is_chunk is not None:
        conditions.append({"is_chunk": is_chunk})

    # Note: For person/address filtering, since we store as CSV strings,
    # we need to use document filtering instead of metadata filtering.
    # This function returns metadata-only filters.

    if not conditions:
        return {}
    elif len(conditions) == 1:
        return conditions[0]
    else:
        return {"$and": conditions}
