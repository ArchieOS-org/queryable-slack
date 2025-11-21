"""
Hybrid search implementation combining semantic and keyword search.

Uses ChromaDB's RRF (Reciprocal Rank Fusion) for combining results.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, List, Any

import chromadb

logger = logging.getLogger(__name__)


def hybrid_search(
    user_query: str,
    db_path: Path,
    n_results: int = 5,
    where: Optional[Dict] = None,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> Dict[str, Any]:
    """
    Perform hybrid search combining semantic and keyword search using RRF.
    
    Note: ChromaDB's hybrid search requires the cloud API or newer versions.
    For local ChromaDB, we'll use a fallback approach:
    1. Semantic search (default)
    2. Keyword filtering on document content
    3. Combine results
    
    Args:
        user_query: Natural language query string
        db_path: Path to ChromaDB persistent storage directory
        n_results: Number of results to return
        where: Optional metadata filter dictionary
        semantic_weight: Weight for semantic search (0.0-1.0)
        keyword_weight: Weight for keyword search (0.0-1.0)
        
    Returns:
        Dictionary with query results containing ids, documents, metadatas, distances
    """
    try:
        # Initialize ChromaDB client
        client = chromadb.PersistentClient(path=str(db_path))
        collection = client.get_collection(name="conductor_sessions")
        
        # For local ChromaDB, we'll use semantic search with keyword boosting
        # Get more results for reranking
        initial_n_results = n_results * 3
        
        # Build query parameters
        query_params = {
            "query_texts": [user_query],
            "n_results": initial_n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        
        # Add metadata filter if provided
        if where is not None:
            query_params["where"] = where
        
        # Perform semantic search
        semantic_results = collection.query(**query_params)
        
        if not semantic_results.get("documents") or not semantic_results["documents"][0]:
            return semantic_results
        
        # Boost results that contain query keywords
        documents = semantic_results["documents"][0]
        metadatas = semantic_results["metadatas"][0]
        distances = semantic_results["distances"][0]
        
        # Extract keywords from query (simple approach)
        query_keywords = set(user_query.lower().split())
        
        # Score each result: combine semantic distance with keyword matches
        scored_results = []
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances)):
            # Count keyword matches in document
            doc_lower = doc.lower()
            keyword_matches = sum(1 for keyword in query_keywords if keyword in doc_lower)
            keyword_score = keyword_matches / max(len(query_keywords), 1)
            
            # Combine scores: lower distance = better, higher keyword_score = better
            # Normalize distance to 0-1 range (assuming max distance ~2.0)
            normalized_dist = min(dist / 2.0, 1.0)
            
            # Hybrid score: lower is better (like distance)
            hybrid_score = (semantic_weight * normalized_dist) - (keyword_weight * keyword_score)
            
            scored_results.append({
                "document": doc,
                "metadata": meta,
                "distance": dist,
                "hybrid_score": hybrid_score,
                "keyword_matches": keyword_matches,
            })
        
        # Sort by hybrid score (lower is better)
        scored_results.sort(key=lambda x: x["hybrid_score"])
        
        # Take top n_results
        top_results = scored_results[:n_results]
        
        # Reconstruct results format
        result = {
            "ids": [[r["metadata"].get("id", f"result_{i}") for i, r in enumerate(top_results)]],
            "documents": [[r["document"] for r in top_results]],
            "metadatas": [[r["metadata"] for r in top_results]],
            "distances": [[r["distance"] for r in top_results]],
        }
        
        logger.debug(f"Hybrid search: {len(documents)} candidates -> {len(top_results)} results")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to perform hybrid search: {e}")
        # Fallback to regular semantic search
        logger.warning("Falling back to regular semantic search")
        from conductor.ask import query_chromadb
        return query_chromadb(user_query, db_path, n_results, where)

