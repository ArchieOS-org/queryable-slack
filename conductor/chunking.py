"""
Session chunking for large sessions that exceed token limits.

Splits large enriched transcripts into smaller chunks while maintaining context.
"""

import logging
from typing import List, Dict, Any
from conductor.models import Session

logger = logging.getLogger(__name__)

# Approximate tokens per character (rough estimate: 1 token ≈ 4 characters)
CHARS_PER_TOKEN = 4
MAX_TOKENS_PER_CHUNK = 10000  # Conservative limit for embeddings


def chunk_session(session: Session, max_tokens: int = MAX_TOKENS_PER_CHUNK) -> List[Dict[str, Any]]:
    """
    Split a large session into multiple chunks.
    
    Args:
        session: Session object to chunk
        max_tokens: Maximum tokens per chunk
        
    Returns:
        List of chunk dictionaries with session data and chunk metadata
    """
    enriched_transcript = session.enriched_transcript
    max_chars = max_tokens * CHARS_PER_TOKEN
    
    # If session fits in one chunk, return as-is
    if len(enriched_transcript) <= max_chars:
        return [{
            "session_id": session.session_id,
            "chunk_id": f"{session.session_id}_chunk_0",
            "chunk_index": 0,
            "total_chunks": 1,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "channel_name": session.channel_name,
            "conversation_type": session.conversation_type,
            "transcript": session.transcript,
            "enriched_transcript": enriched_transcript,
            "file_count": session.file_count,
            "message_count": session.message_count,
        }]
    
    # Split into chunks
    chunks = []
    total_chars = len(enriched_transcript)
    num_chunks = (total_chars + max_chars - 1) // max_chars  # Ceiling division
    
    logger.debug(f"Chunking session {session.session_id}: {total_chars} chars -> {num_chunks} chunks")
    
    for i in range(num_chunks):
        start_idx = i * max_chars
        end_idx = min((i + 1) * max_chars, total_chars)
        
        chunk_text = enriched_transcript[start_idx:end_idx]
        
        # Add overlap between chunks for context preservation
        if i > 0:
            # Prepend some context from previous chunk
            overlap_start = max(0, start_idx - max_chars // 10)  # 10% overlap
            overlap_text = enriched_transcript[overlap_start:start_idx]
            chunk_text = f"[CONTEXT FROM PREVIOUS CHUNK]\n{overlap_text}\n[END CONTEXT]\n\n{chunk_text}"
        
        if i < num_chunks - 1:
            # Append some context for next chunk
            overlap_end = min(total_chars, end_idx + max_chars // 10)
            overlap_text = enriched_transcript[end_idx:overlap_end]
            chunk_text = f"{chunk_text}\n\n[CONTEXT FOR NEXT CHUNK]\n{overlap_text}\n[END CONTEXT]"
        
        chunks.append({
            "session_id": session.session_id,
            "chunk_id": f"{session.session_id}_chunk_{i}",
            "chunk_index": i,
            "total_chunks": num_chunks,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "channel_name": session.channel_name,
            "conversation_type": session.conversation_type,
            "transcript": session.transcript if i == 0 else "",  # Only include full transcript in first chunk
            "enriched_transcript": chunk_text,
            "file_count": session.file_count if i == 0 else 0,  # Only count files in first chunk
            "message_count": session.message_count,
        })
    
    return chunks


def should_chunk_session(session: Session, max_tokens: int = MAX_TOKENS_PER_CHUNK) -> bool:
    """Check if a session needs to be chunked."""
    max_chars = max_tokens * CHARS_PER_TOKEN
    return len(session.enriched_transcript) > max_chars

