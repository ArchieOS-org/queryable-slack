"""
Supabase vector query module for Conductor.

Provides functions to query vectorized Slack sessions from Supabase using pgvector.

This module integrates with the vecs.conductor_sessions table in Supabase,
which stores session embeddings and metadata. It uses RPC functions for
vector similarity search with cosine distance.

Requirements:
- Supabase project with pgvector extension enabled
- RPC functions created (see supabase/migrations/20250123_create_vector_search_functions.sql)
- SUPABASE_URL and SUPABASE_ANON_KEY environment variables set
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    """
    Initialize and return a Supabase client.

    Returns:
        Supabase client instance

    Raises:
        ValueError: If Supabase credentials are not set
    """
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    supabase_key = os.environ.get("SUPABASE_ANON_KEY", "").strip()

    if not supabase_url or not supabase_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be set. "
            "See .env.example for configuration details."
        )

    return create_client(supabase_url, supabase_key)


def query_vector_similarity(
    query_embedding: List[float],
    match_threshold: float = 0.0,
    match_count: int = 5,
    channel_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Query Supabase for similar sessions using vector similarity search.

    This function queries the vecs.conductor_sessions table using cosine similarity
    on the embedding vectors via the match_conductor_sessions RPC function.

    Args:
        query_embedding: The embedding vector to search for (list of floats)
        match_threshold: Minimum similarity threshold (0.0 to 1.0, default 0.0)
        match_count: Number of results to return (default 5)
        channel_name: Optional filter by Slack channel name
        start_date: Optional filter by session start date (inclusive)
        end_date: Optional filter by session end date (inclusive)

    Returns:
        Dictionary with query results in ChromaDB-compatible format:
        {
            'ids': [[id1, id2, ...]],
            'documents': [[doc1, doc2, ...]],
            'metadatas': [[meta1, meta2, ...]],
            'distances': [[dist1, dist2, ...]]
        }

    Raises:
        Exception: If query fails
    """
    try:
        client = get_supabase_client()

        # Prepare RPC function parameters
        # Note: Supabase RPC expects vector as list of floats (not string)
        rpc_params = {
            'query_embedding': query_embedding,
            'match_threshold': match_threshold,
            'match_count': match_count
        }

        # Use filtered version if filters are provided
        if channel_name or start_date or end_date:
            logger.info(f"Querying with filters: channel={channel_name}, start={start_date}, end={end_date}")

            # Add optional filter parameters
            if channel_name:
                rpc_params['channel_name'] = channel_name
            if start_date:
                rpc_params['start_date'] = start_date.isoformat()
            if end_date:
                rpc_params['end_date'] = end_date.isoformat()

            result = client.rpc('match_conductor_sessions_filtered', rpc_params).execute()
        else:
            # Use basic similarity search without filters
            result = client.rpc('match_conductor_sessions', rpc_params).execute()

        # Parse results into ChromaDB-compatible format
        if result.data:
            ids = []
            documents = []
            metadatas = []
            distances = []

            for row in result.data:
                ids.append(row['id'])

                # Extract document text from metadata
                # Expected metadata structure: {"document": "...", "channel_name": "...", ...}
                metadata = row.get('metadata', {})
                doc_text = metadata.get('document', row['id'])
                documents.append(doc_text)
                metadatas.append(metadata)

                # Convert similarity to distance (1 - similarity for cosine distance)
                similarity = row.get('similarity', 0.0)
                distance = 1.0 - similarity
                distances.append(distance)

            logger.info(f"Found {len(ids)} results from vector similarity search")
            return {
                'ids': [ids],
                'documents': [documents],
                'metadatas': [metadatas],
                'distances': [distances]
            }
        else:
            logger.warning("No results found from vector similarity search")
            return {
                'ids': [[]],
                'documents': [[]],
                'metadatas': [[]],
                'distances': [[]]
            }

    except Exception as e:
        logger.error(f"Failed to query Supabase vector similarity: {e}")
        raise


def get_session_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific session by its ID from Supabase.

    Args:
        session_id: The unique session identifier

    Returns:
        Dictionary containing session data (id, metadata, vec) or None if not found

    Raises:
        Exception: If query fails
    """
    try:
        client = get_supabase_client()

        # Query the vecs.conductor_sessions table directly by ID
        # Use schema() method to access vecs schema
        result = client.schema('vecs').from_('conductor_sessions').select('*').eq('id', session_id).execute()

        if result.data and len(result.data) > 0:
            logger.info(f"Found session with ID: {session_id}")
            return result.data[0]
        else:
            logger.warning(f"Session not found with ID: {session_id}")
            return None

    except Exception as e:
        logger.error(f"Failed to retrieve session {session_id}: {e}")
        raise


def list_recent_sessions(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve the most recent sessions from Supabase.

    This is a fallback function for when vector similarity search is not needed.

    Args:
        limit: Maximum number of sessions to return (default 10)

    Returns:
        List of session dictionaries with id, metadata, and vec fields

    Raises:
        Exception: If query fails
    """
    try:
        client = get_supabase_client()

        # Query recent sessions from vecs schema, ordered by metadata->start_time if available
        result = client.schema('vecs').from_('conductor_sessions').select('*').limit(limit).execute()

        if result.data:
            logger.info(f"Retrieved {len(result.data)} recent sessions")
            return result.data
        else:
            logger.warning("No sessions found in database")
            return []

    except Exception as e:
        logger.error(f"Failed to list recent sessions: {e}")
        raise


def query_hybrid_search(
    query_embedding: List[float],
    search_text: str = None,
    match_threshold: float = 0.0,
    match_count: int = 10,
    keyword_boost: float = 0.3
) -> Dict[str, Any]:
    """
    Hybrid search combining vector similarity with keyword matching.

    This function boosts the similarity score for documents that contain
    the search text, which is especially useful for finding documents
    with specific identifiers (addresses, names, IDs) that may have
    low semantic similarity but are exact matches.

    Args:
        query_embedding: The embedding vector to search for
        search_text: Optional text to search for (keyword matching)
        match_threshold: Minimum similarity threshold (default 0.0)
        match_count: Number of results to return (default 10)
        keyword_boost: Amount to boost similarity for keyword matches (default 0.3)

    Returns:
        Dictionary with query results in ChromaDB-compatible format
    """
    try:
        client = get_supabase_client()

        # Prepare RPC parameters
        rpc_params = {
            'query_embedding': query_embedding,
            'match_threshold': match_threshold,
            'match_count': match_count,
            'keyword_boost': keyword_boost
        }

        if search_text:
            rpc_params['search_text'] = search_text

        result = client.rpc('hybrid_search_conductor_sessions', rpc_params).execute()

        # Parse results into ChromaDB-compatible format
        if result.data:
            ids = []
            documents = []
            metadatas = []
            distances = []
            keyword_matches = []

            for row in result.data:
                ids.append(row['id'])

                metadata = row.get('metadata', {})
                doc_text = metadata.get('document', row['id'])
                documents.append(doc_text)
                metadatas.append(metadata)

                similarity = row.get('similarity', 0.0)
                distance = 1.0 - similarity
                distances.append(distance)

                keyword_matches.append(row.get('keyword_match', False))

            logger.info(f"Hybrid search found {len(ids)} results, {sum(keyword_matches)} with keyword matches")
            return {
                'ids': [ids],
                'documents': [documents],
                'metadatas': [metadatas],
                'distances': [distances],
                'keyword_matches': [keyword_matches]
            }
        else:
            logger.warning("No results found from hybrid search")
            return {
                'ids': [[]],
                'documents': [[]],
                'metadatas': [[]],
                'distances': [[]],
                'keyword_matches': [[]]
            }

    except Exception as e:
        logger.error(f"Failed to perform hybrid search: {e}")
        raise


def get_sessions_by_channel(channel_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve sessions from a specific Slack channel.

    Args:
        channel_name: The name of the Slack channel
        limit: Maximum number of sessions to return (default 10)

    Returns:
        List of session dictionaries from the specified channel

    Raises:
        Exception: If query fails
    """
    try:
        client = get_supabase_client()

        # Use jsonb query to filter by channel_name in metadata from vecs schema
        # Note: This uses PostgreSQL's ->> operator for jsonb field access
        result = (
            client.schema('vecs')
            .from_('conductor_sessions')
            .select('*')
            .filter('metadata->>channel_name', 'eq', channel_name)
            .limit(limit)
            .execute()
        )

        if result.data:
            logger.info(f"Found {len(result.data)} sessions in channel: {channel_name}")
            return result.data
        else:
            logger.warning(f"No sessions found in channel: {channel_name}")
            return []

    except Exception as e:
        logger.error(f"Failed to retrieve sessions for channel {channel_name}: {e}")
        raise
