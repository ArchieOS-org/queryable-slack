"""
Query result caching to reduce API costs and improve response times.

Uses Python's functools.lru_cache with TTL support.
"""

import hashlib
import json
import logging
import time
from functools import lru_cache
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# In-memory cache with TTL
_cache: Dict[str, Tuple[Any, float]] = {}
_cache_ttl: int = 3600  # 1 hour default TTL


def _make_cache_key(query: str, db_path: Path, n_results: int, where: Optional[Dict] = None) -> str:
    """Create a deterministic cache key from query parameters."""
    cache_data = {
        "query": query,
        "db_path": str(db_path),
        "n_results": n_results,
        "where": where,
    }
    cache_str = json.dumps(cache_data, sort_keys=True)
    return hashlib.sha256(cache_str.encode()).hexdigest()


def get_cached_result(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached result if it exists and hasn't expired."""
    if cache_key not in _cache:
        return None
    
    result, timestamp = _cache[cache_key]
    if time.time() - timestamp > _cache_ttl:
        # Expired, remove from cache
        del _cache[cache_key]
        logger.debug(f"Cache expired for key: {cache_key[:16]}...")
        return None
    
    logger.debug(f"Cache hit for key: {cache_key[:16]}...")
    return result


def set_cached_result(cache_key: str, result: Dict[str, Any]) -> None:
    """Store result in cache with current timestamp."""
    _cache[cache_key] = (result, time.time())
    logger.debug(f"Cached result for key: {cache_key[:16]}...")


def clear_cache() -> int:
    """Clear all cached results. Returns number of items cleared."""
    count = len(_cache)
    _cache.clear()
    logger.info(f"Cleared {count} cached results")
    return count


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    now = time.time()
    expired_count = sum(1 for _, (_, ts) in _cache.items() if now - ts > _cache_ttl)
    valid_count = len(_cache) - expired_count
    
    return {
        "total_entries": len(_cache),
        "valid_entries": valid_count,
        "expired_entries": expired_count,
        "ttl_seconds": _cache_ttl,
    }


def cached_query(
    query_func,
    query: str,
    db_path: Path,
    n_results: int = 5,
    where: Optional[Dict] = None,
    use_cache: bool = True
) -> Dict[str, Any]:
    """
    Wrapper for query function with caching support.
    
    Args:
        query_func: The actual query function to call
        query: Query string
        db_path: Database path
        n_results: Number of results
        where: Optional metadata filter
        use_cache: Whether to use cache (default: True)
        
    Returns:
        Query results dictionary
    """
    if not use_cache:
        return query_func(query, db_path, n_results, where)
    
    cache_key = _make_cache_key(query, db_path, n_results, where)
    cached_result = get_cached_result(cache_key)
    
    if cached_result is not None:
        return cached_result
    
    # Cache miss, execute query
    result = query_func(query, db_path, n_results, where)
    
    # Store in cache
    set_cached_result(cache_key, result)
    
    return result

