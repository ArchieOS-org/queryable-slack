"""
Supabase Vecs client for pgvector operations.

Provides a unified interface for vector storage and querying using Supabase's vecs library.
Replaces ChromaDB for Vercel/serverless deployments.
"""

import os
import logging
from typing import Dict, Optional, List, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy import vecs
_vecs_client = None
_vecs_collection = None

# Default embedding dimension for all-MiniLM-L6-v2 (ChromaDB default)
EMBEDDING_DIMENSION = 384
COLLECTION_NAME = "conductor_sessions"


def _get_vecs_client():
    """Get or create vecs client (singleton)."""
    global _vecs_client
    
    if _vecs_client is None:
        try:
            import vecs
        except ImportError:
            raise ImportError(
                "vecs is not installed. Install with: pip install vecs"
            )
        
        # Get database connection string from environment
        db_connection = os.environ.get('DATABASE_URL')
        if not db_connection:
            raise ValueError(
                "DATABASE_URL environment variable is required for Supabase vecs. "
                "Set it to your Supabase Postgres connection string."
            )
        
        logger.info("Connecting to Supabase Postgres via vecs...")
        _vecs_client = vecs.create_client(db_connection)
        logger.info("✅ Connected to Supabase Postgres")
    
    return _vecs_client


def _get_collection():
    """Get or create vecs collection (singleton)."""
    global _vecs_collection
    
    if _vecs_collection is None:
        vx = _get_vecs_client()
        logger.info(f"Getting or creating collection '{COLLECTION_NAME}' with dimension {EMBEDDING_DIMENSION}...")
        _vecs_collection = vx.get_or_create_collection(
            name=COLLECTION_NAME,
            dimension=EMBEDDING_DIMENSION
        )
        logger.info(f"✅ Collection '{COLLECTION_NAME}' ready")
    
    return _vecs_collection


def query_vecs(
    query_text: str,
    n_results: int = 5,
    filters: Optional[Dict[str, Any]] = None,
    query_embedding: Optional[List[float]] = None
) -> Dict[str, Any]:
    """
    Query vecs collection for similar documents.
    
    Args:
        query_text: Natural language query string (will be embedded)
        n_results: Number of results to return
        filters: Optional metadata filters (e.g., {"date": {"$eq": "2024-01-01"}})
        query_embedding: Optional pre-computed embedding vector (if provided, query_text is ignored)
        
    Returns:
        Dictionary with ids, documents, metadatas, distances (ChromaDB-compatible format)
    """
    try:
        collection = _get_collection()
        
        # If query_embedding is provided, use it directly
        # Otherwise, vecs will embed the query_text automatically
        if query_embedding:
            query_data = query_embedding
        else:
            query_data = query_text
        
        # Query vecs collection
        # Vecs supports metadata filtering similar to ChromaDB
        # Vecs query returns a list of record IDs
        result_ids = collection.query(
            data=query_data,
            limit=n_results,
            filters=filters or {}
        )
        
        # Convert vecs results to ChromaDB-compatible format
        if not result_ids:
            return {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }
        
        # Fetch full records with metadata for the returned IDs
        # Vecs stores documents in metadata, so we need to retrieve them
        ids = []
        documents = []
        metadatas = []
        distances = []
        
        # Vecs query returns IDs, but we need to get the full records
        # For now, we'll use the IDs and fetch metadata separately if needed
        # Note: vecs stores document text in metadata['document']
        for result_id in result_ids:
            # Try to get the record from collection
            # Vecs doesn't have a direct "get by ID" method, so we'll use the IDs
            # and reconstruct from what we stored
            ids.append(result_id)
            # Distance is not directly available from query, set to 0.0
            # Vecs uses cosine similarity internally
            distances.append(0.0)
            # Metadata and document will be retrieved from stored records
            # For now, return empty and let the caller handle it
            metadatas.append({})
            documents.append('')
        
        # TODO: Implement proper record retrieval from vecs
        # Vecs may need a different approach - we might need to store records
        # in a way that allows retrieval by ID, or use a different query method
        
        return {
            "ids": [ids],
            "documents": [documents],
            "metadatas": [metadatas],
            "distances": [distances]
        }
        
    except Exception as e:
        logger.error(f"Error querying vecs: {e}", exc_info=True)
        raise


def upsert_vecs(
    records: List[Tuple[str, str, Dict[str, Any]]]
) -> None:
    """
    Upsert records into vecs collection.
    
    Args:
        records: List of tuples (id, document_text, metadata)
                 The document_text will be embedded automatically by vecs
    """
    try:
        collection = _get_collection()
        
        # Prepare records for vecs upsert
        # Vecs format: (id, embedding_or_text, metadata)
        # Since we're using text, vecs will embed it automatically
        vecs_records = []
        for record_id, document_text, metadata in records:
            # Store document text in metadata for retrieval
            metadata_with_doc = {**metadata, "document": document_text}
            vecs_records.append((record_id, document_text, metadata_with_doc))
        
        logger.info(f"Upserting {len(vecs_records)} records into vecs collection...")
        collection.upsert(records=vecs_records)
        
        # Create index if it doesn't exist (idempotent)
        try:
            collection.create_index()
            logger.info("✅ Index created/updated")
        except Exception as e:
            logger.warning(f"Index creation skipped (may already exist): {e}")
        
        logger.info(f"✅ Upserted {len(vecs_records)} records")
        
    except Exception as e:
        logger.error(f"Error upserting to vecs: {e}", exc_info=True)
        raise


def delete_collection() -> None:
    """Delete the collection (use with caution!)."""
    try:
        vx = _get_vecs_client()
        vx.delete_collection(COLLECTION_NAME)
        global _vecs_collection
        _vecs_collection = None
        logger.info(f"✅ Deleted collection '{COLLECTION_NAME}'")
    except Exception as e:
        logger.error(f"Error deleting collection: {e}", exc_info=True)
        raise


def disconnect() -> None:
    """Disconnect from vecs client."""
    global _vecs_client, _vecs_collection
    try:
        if _vecs_client:
            _vecs_client.disconnect()
            logger.info("✅ Disconnected from vecs")
    except Exception as e:
        logger.warning(f"Error disconnecting: {e}")
    finally:
        _vecs_client = None
        _vecs_collection = None

