"""
Reciprocal Rank Fusion (RRF) for combining multiple ranked result sets.

Implements RRF algorithm to merge results from multiple queries or search methods,
ensuring comprehensive coverage while maintaining relevance ranking.
"""

import logging
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    result_sets: List[List[Dict[str, Any]]],
    k: int = 60,
    top_k: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Combine multiple ranked result sets using Reciprocal Rank Fusion (RRF).
    
    RRF formula: score = sum(1 / (rank + k)) for each result set where the document appears
    
    Args:
        result_sets: List of ranked result lists, each containing dicts with at least:
                    - 'id' or 'metadata' with 'id' field
                    - 'document' or 'doc' field
                    - 'metadata' field
                    - 'distance' or 'score' field (optional)
        k: RRF constant (default: 60, standard value)
        top_k: Maximum number of results to return (None = return all)
        
    Returns:
        List of deduplicated, reranked results sorted by RRF score (descending)
    """
    if not result_sets:
        logger.warning("No result sets provided to RRF")
        return []
    
    logger.debug(f"Starting RRF fusion: {len(result_sets)} result sets, k={k}, top_k={top_k}")
    
    # Track fused scores and document data by ID
    fused_scores = defaultdict(float)
    document_data = {}  # Store full document data by ID
    
    # Process each result set
    total_docs_processed = 0
    for result_set_idx, result_set in enumerate(result_sets, 1):
        if not result_set:
            logger.debug(f"  Result set {result_set_idx}: empty, skipping")
            continue
        
        logger.debug(f"  Result set {result_set_idx}: processing {len(result_set)} documents")
            
        for rank, result in enumerate(result_set):
            # Extract document ID
            doc_id = None
            if isinstance(result, dict):
                doc_id = result.get("id")
                if not doc_id and "metadata" in result:
                    doc_id = result["metadata"].get("id")
                if not doc_id:
                    # Generate ID from document content hash as fallback
                    doc_content = result.get("document") or result.get("doc", "")
                    # Use abs() to ensure positive hash, and limit length
                    content_hash = abs(hash(doc_content)) % (10 ** 10)  # Limit to 10 digits
                    doc_id = f"doc_{content_hash}"
                    logger.debug(f"    Generated fallback ID for document at rank {rank}: {doc_id}")
            else:
                # Handle case where result is a string or other type
                content_hash = abs(hash(str(result))) % (10 ** 10)  # Limit to 10 digits
                doc_id = f"doc_{content_hash}"
                logger.debug(f"    Generated ID from string result at rank {rank}: {doc_id}")
            
            # Calculate RRF score contribution
            rrf_score = 1.0 / (rank + k)
            fused_scores[doc_id] += rrf_score
            total_docs_processed += 1
            
            # Store document data (keep first occurrence or best score)
            if doc_id not in document_data:
                document_data[doc_id] = result
    
    logger.debug(f"Processed {total_docs_processed} documents, found {len(fused_scores)} unique documents")
    
    # Sort by fused score (descending)
    sorted_results = sorted(
        fused_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    logger.debug(f"Sorted results by RRF score, top score: {sorted_results[0][1] if sorted_results else 0:.6f}")
    
    # Build final result list
    final_results = []
    for doc_id, score in sorted_results:
        result = document_data[doc_id].copy() if isinstance(document_data[doc_id], dict) else document_data[doc_id]
        if isinstance(result, dict):
            result["rrf_score"] = score
        final_results.append(result)
    
    # Limit to top_k if specified
    if top_k is not None:
        logger.debug(f"Limiting results from {len(final_results)} to {top_k}")
        final_results = final_results[:top_k]
    
    logger.info(f"RRF fusion complete: {len(result_sets)} result sets, {len(fused_scores)} unique documents -> {len(final_results)} final results")
    
    return final_results


def fuse_chromadb_results(
    result_sets: List[Dict[str, Any]],
    k: int = 60,
    top_k: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fuse multiple ChromaDB query results using RRF.
    
    Args:
        result_sets: List of ChromaDB result dictionaries, each with:
                    - 'ids': List[List[str]]
                    - 'documents': List[List[str]]
                    - 'metadatas': List[List[Dict]]
                    - 'distances': List[List[float]] (optional)
        k: RRF constant (default: 60)
        top_k: Maximum number of results to return
        
    Returns:
        Single ChromaDB-formatted result dictionary with fused results
    """
    if not result_sets:
        logger.warning("No ChromaDB result sets provided to fuse_chromadb_results")
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
    
    logger.debug(f"Fusing {len(result_sets)} ChromaDB result sets")
    
    # Convert ChromaDB results to list of dicts for RRF
    all_result_lists = []
    
    for result_set_idx, result_set in enumerate(result_sets, 1):
        if not result_set.get("ids") or not result_set["ids"][0]:
            logger.debug(f"  Result set {result_set_idx}: no IDs, skipping")
            continue
        
        ids = result_set["ids"][0]
        documents = result_set.get("documents", [[]])[0]
        metadatas = result_set.get("metadatas", [[]])[0]
        distances = result_set.get("distances", [[]])[0]
        
        logger.debug(f"  Result set {result_set_idx}: {len(ids)} documents")
        
        result_list = []
        for i, doc_id in enumerate(ids):
            result_dict = {
                "id": doc_id,
                "document": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
            }
            if i < len(distances):
                result_dict["distance"] = distances[i]
            result_list.append(result_dict)
        
        all_result_lists.append(result_list)
    
    logger.debug(f"Converted {len(all_result_lists)} result sets for RRF")
    
    # Apply RRF
    fused_results = reciprocal_rank_fusion(all_result_lists, k=k, top_k=top_k)
    
    # Convert back to ChromaDB format
    if not fused_results:
        logger.warning("No fused results from RRF")
        return {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
    
    logger.debug(f"Converting {len(fused_results)} fused results back to ChromaDB format")
    
    fused_ids = []
    fused_documents = []
    fused_metadatas = []
    fused_distances = []
    
    for result in fused_results:
        fused_ids.append(result.get("id", ""))
        fused_documents.append(result.get("document", ""))
        fused_metadatas.append(result.get("metadata", {}))
        fused_distances.append(result.get("distance", 0.0))
    
    logger.info(f"Fused ChromaDB results: {len(fused_ids)} documents")
    
    return {
        "ids": [fused_ids],
        "documents": [fused_documents],
        "metadatas": [fused_metadatas],
        "distances": [fused_distances],
    }

