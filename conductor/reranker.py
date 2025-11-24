"""
Query result reranking using cross-encoder models.

Improves relevance of search results by reranking initial semantic search results.
"""

import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path

# Lazy load sentence-transformers to avoid dependency issues
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    logging.warning("sentence-transformers not installed. Reranking will be skipped.")

logger = logging.getLogger(__name__)

# Cache cross-encoder model globally
_reranker_model = None


def _load_reranker_model():
    """Load cross-encoder model for reranking (cached globally)."""
    global _reranker_model
    
    if _reranker_model is None and CROSS_ENCODER_AVAILABLE:
        # Use a lightweight cross-encoder model optimized for speed
        model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        logger.info(f"Loading reranker model ({model_name})... This may take a moment.")
        try:
            _reranker_model = CrossEncoder(model_name, max_length=512)
            logger.info("✅ Reranker model loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load reranker model: {e}")
            _reranker_model = None
    
    return _reranker_model


def rerank_results(
    query: str,
    documents: List[str],
    metadatas: List[Dict[str, Any]],
    top_k: int = 5
) -> Tuple[List[str], List[Dict[str, Any]], List[float]]:
    """
    Rerank search results using a cross-encoder model.
    
    Args:
        query: The search query
        documents: List of document texts to rerank
        metadatas: List of metadata dictionaries corresponding to documents
        top_k: Number of top results to return after reranking
        
    Returns:
        Tuple of (reranked_documents, reranked_metadatas, reranked_scores)
    """
    if not CROSS_ENCODER_AVAILABLE or not documents:
        # Return original results if reranking not available
        return documents[:top_k], metadatas[:top_k], [1.0] * min(len(documents), top_k)
    
    model = _load_reranker_model()
    if model is None:
        logger.debug("Reranker model not available, returning original results")
        return documents[:top_k], metadatas[:top_k], [1.0] * min(len(documents), top_k)
    
    try:
        # Prepare pairs for cross-encoder: (query, document)
        pairs = [[query, doc] for doc in documents]
        
        # Get relevance scores
        scores = model.predict(pairs)
        
        # Sort by score (higher is better)
        scored_docs = list(zip(documents, metadatas, scores))
        scored_docs.sort(key=lambda x: x[2], reverse=True)
        
        # Extract top_k results
        reranked_docs = [doc for doc, _, _ in scored_docs[:top_k]]
        reranked_metas = [meta for _, meta, _ in scored_docs[:top_k]]
        reranked_scores = [float(score) for _, _, score in scored_docs[:top_k]]
        
        logger.debug(f"Reranked {len(documents)} results, returning top {len(reranked_docs)}")
        
        return reranked_docs, reranked_metas, reranked_scores
        
    except Exception as e:
        logger.warning(f"Reranking failed: {e}, returning original results")
        return documents[:top_k], metadatas[:top_k], [1.0] * min(len(documents), top_k)

