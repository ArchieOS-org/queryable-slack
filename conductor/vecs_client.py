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


def _convert_to_pooler_url(db_url: str) -> str:
    """
    Convert direct Supabase connection URL to connection pooler URL.
    Context7 best practice: Use transaction pooler (port 6543) for serverless/Vercel.
    
    Returns pooler URL in format:
    postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-1-[REGION].pooler.supabase.com:6543/postgres
    """
    import re
    from urllib.parse import urlparse, urlunparse
    
    # Parse the connection URL
    parsed = urlparse(db_url)
    
    # Check if already using pooler - return as-is
    if 'pooler.supabase.com' in (parsed.hostname or ''):
        logger.info("Already using pooler connection")
        return db_url
    
    # Extract project ref from hostname (e.g., db.gxpcrohsbtndndypagie.supabase.co)
    match = re.search(r'db\.([^.]+)\.supabase\.co', parsed.hostname or '')
    if not match:
        logger.warning(f"Could not parse Supabase URL for pooler conversion: {parsed.hostname}")
        return db_url  # Return original if we can't parse it
    
    project_ref = match.group(1)
    password = parsed.password or ''
    
    # Try common regions - start with us-east-1 (aws-1 format)
    # Context7: Use aws-1-{region} format for Supabase pooler
    regions_to_try = ['us-east-1', 'us-west-1', 'eu-west-1', 'ap-southeast-1', 'eu-central-1']
    region = os.environ.get('SUPABASE_REGION', 'us-east-1')
    
    if region not in regions_to_try:
        regions_to_try.insert(0, region)
    
    # Use first region (will try others if connection fails)
    pooler_hostname = f'aws-1-{regions_to_try[0]}.pooler.supabase.com'
    pooler_username = f'postgres.{project_ref}'
    
    # Construct pooler URL with transaction mode (port 6543)
    pooler_url = urlunparse((
        'postgresql',
        f'{pooler_username}:{password}@{pooler_hostname}:6543',
        '/postgres',
        '',
        '',
        ''
    ))
    
    logger.info(f"Converted to pooler URL: postgresql://{pooler_username}:***@{pooler_hostname}:6543/postgres")
    return pooler_url


def _get_database_url():
    """Get database URL from environment, checking multiple variable names."""
    for var_name in ['DATABASE_URL', 'POSTGRES_URL', 'POSTGRES_PRISMA_URL', 'POSTGRES_URL_NON_POOLING']:
        url = os.environ.get(var_name)
        if url:
            logger.info(f"Using database URL from {var_name}")
            return url
    return None


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

        # Get database connection string from environment (check multiple variable names)
        db_connection = _get_database_url()
        if not db_connection:
            raise ValueError(
                "Database URL environment variable is required for Supabase vecs. "
                "Set DATABASE_URL, POSTGRES_URL, or POSTGRES_PRISMA_URL."
            )
        
        # Convert to pooler URL for serverless/Vercel (Context7 best practice)
        # Use pooler for better connection management in serverless environments
        if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
            db_connection = _convert_to_pooler_url(db_connection)
        
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
        
        # Vecs query returns IDs, but we need metadata and documents
        # We stored documents in metadata['document'], so we need to fetch records
        # Query PostgreSQL directly to get full records with metadata
        ids = []
        documents = []
        metadatas = []
        distances = []
        
        try:
            import psycopg
            from urllib.parse import urlparse
            import json

            db_url = _get_database_url()
            if not db_url:
                raise ValueError("Database URL not set")
            
            # Convert to pooler URL for serverless/Vercel (Context7 best practice)
            if os.environ.get('VERCEL') or os.environ.get('VERCEL_ENV'):
                db_url = _convert_to_pooler_url(db_url)
            
            # Use connection string directly (psycopg supports connection strings)
            conn = psycopg.connect(db_url)
            
            # Query vecs table directly
            # Vecs stores collections in a table named after the collection in the vecs schema
            # The table has: id (text), embedding (vector), metadata (jsonb)
            table_name = f'"{COLLECTION_NAME}"'  # Vecs uses collection name as table name
            placeholders = ','.join(['%s'] * len(result_ids))
            
            with conn.cursor() as cur:
                # Try vecs schema first
                try:
                    cur.execute(
                        f"""
                        SELECT id, metadata
                        FROM vecs.{table_name}
                        WHERE id IN ({placeholders})
                        """,
                        result_ids
                    )
                except Exception:
                    # If vecs schema doesn't work, try public schema
                    cur.execute(
                        f"""
                        SELECT id, metadata
                        FROM {table_name}
                        WHERE id IN ({placeholders})
                        """,
                        result_ids
                    )
                
                rows = cur.fetchall()
                
                # Create a map of ID to metadata for quick lookup
                id_to_metadata = {}
                for row in rows:
                    record_id, metadata_json = row
                    id_to_metadata[record_id] = metadata_json if metadata_json else {}
            
            conn.close()
            
            # Process results in the order returned by query
            for record_id in result_ids:
                ids.append(record_id)
                metadata = id_to_metadata.get(record_id, {})
                metadatas.append(metadata)
                # Extract document from metadata (we stored it there during upsert)
                documents.append(metadata.get('document', ''))
                # Distance is not available from vecs query, use 0.0
                # (vecs uses cosine similarity internally, but doesn't expose distance in query)
                distances.append(0.0)
                
        except Exception as e:
            logger.error(f"Error fetching vecs records: {e}", exc_info=True)
            # Fallback: return IDs only with empty metadata
            logger.warning("Falling back to IDs only - metadata and documents unavailable")
            for record_id in result_ids:
                ids.append(record_id)
                metadatas.append({})
                documents.append('')
                distances.append(0.0)
        
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

