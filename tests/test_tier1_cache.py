"""
Tests for Tier 1: Query Result Caching.

Tests cache functionality, TTL, cache keys, and cache statistics.
"""

import pytest
import time
from pathlib import Path
from conductor.cache import (
    _make_cache_key,
    get_cached_result,
    set_cached_result,
    clear_cache,
    get_cache_stats,
    cached_query,
)


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_cache_key_deterministic(self):
        """Test that same inputs produce same cache key."""
        print("\n🔑 Testing cache key generation...")
        query = "test query"
        db_path = Path("./test_db")
        n_results = 5
        
        key1 = _make_cache_key(query, db_path, n_results, None)
        key2 = _make_cache_key(query, db_path, n_results, None)
        
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex length
        print("   ✅ Cache keys are deterministic!")

    def test_cache_key_different_queries(self):
        """Test that different queries produce different keys."""
        print("\n🔑 Testing cache key uniqueness...")
        db_path = Path("./test_db")
        
        key1 = _make_cache_key("query 1", db_path, 5, None)
        key2 = _make_cache_key("query 2", db_path, 5, None)
        
        assert key1 != key2
        print("   ✅ Different queries produce different keys!")

    def test_cache_key_with_metadata_filter(self):
        """Test that metadata filters affect cache key."""
        print("\n🔑 Testing cache key with filters...")
        query = "test query"
        db_path = Path("./test_db")
        
        key1 = _make_cache_key(query, db_path, 5, None)
        key2 = _make_cache_key(query, db_path, 5, {"file_count": {"$gt": 0}})
        
        assert key1 != key2
        print("   ✅ Metadata filters affect cache keys!")


class TestCacheOperations:
    """Tests for cache get/set operations."""

    def test_set_and_get_result(self):
        """Test basic cache set and get."""
        print("\n💾 Testing cache operations...")
        clear_cache()
        
        cache_key = "test_key_123"
        test_result = {"documents": [["test doc"]], "ids": [["id1"]]}
        
        # Should not exist initially
        assert get_cached_result(cache_key) is None
        
        # Set result
        set_cached_result(cache_key, test_result)
        
        # Should exist now
        cached = get_cached_result(cache_key)
        assert cached is not None
        assert cached == test_result
        print("   ✅ Cache set/get works!")

    def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        print("\n⏰ Testing cache expiration...")
        clear_cache()
        
        cache_key = "test_key_expire"
        test_result = {"documents": [["test"]]}
        
        # Set result
        set_cached_result(cache_key, test_result)
        
        # Manually expire by modifying cache entry timestamp
        from conductor.cache import _cache, _cache_ttl
        _cache[cache_key] = (test_result, time.time() - _cache_ttl - 1)
        
        # Should be expired now
        assert get_cached_result(cache_key) is None
        assert cache_key not in _cache  # Should be removed
        print("   ✅ Cache expiration works!")

    def test_cache_clear(self):
        """Test clearing the cache."""
        print("\n🗑️  Testing cache clear...")
        clear_cache()
        
        # Add some entries
        for i in range(5):
            set_cached_result(f"key_{i}", {"data": i})
        
        from conductor.cache import _cache
        assert len(_cache) == 5
        
        # Clear cache
        cleared = clear_cache()
        assert cleared == 5
        assert len(_cache) == 0
        print("   ✅ Cache clear works!")


class TestCacheStatistics:
    """Tests for cache statistics."""

    def test_cache_stats_empty(self):
        """Test cache stats for empty cache."""
        print("\n📊 Testing cache statistics...")
        clear_cache()
        
        stats = get_cache_stats()
        assert stats["total_entries"] == 0
        assert stats["valid_entries"] == 0
        assert stats["expired_entries"] == 0
        print("   ✅ Empty cache stats correct!")

    def test_cache_stats_with_entries(self):
        """Test cache stats with entries."""
        print("\n📊 Testing cache stats with entries...")
        clear_cache()
        
        # Add valid entries
        for i in range(3):
            set_cached_result(f"key_{i}", {"data": i})
        
        stats = get_cache_stats()
        assert stats["total_entries"] == 3
        assert stats["valid_entries"] == 3
        print("   ✅ Cache stats with entries correct!")


class TestCachedQueryWrapper:
    """Tests for cached_query wrapper function."""

    def test_cached_query_cache_hit(self):
        """Test that cached_query uses cache on second call."""
        print("\n🔄 Testing cached query wrapper...")
        clear_cache()
        
        call_count = {"count": 0}
        
        def mock_query(query, db_path, n_results, where):
            call_count["count"] += 1
            return {"result": f"query_{call_count['count']}"}
        
        query = "test query"
        db_path = Path("./test_db")
        
        # First call - should execute query
        result1 = cached_query(mock_query, query, db_path, 5, None, use_cache=True)
        assert call_count["count"] == 1
        
        # Second call - should use cache
        result2 = cached_query(mock_query, query, db_path, 5, None, use_cache=True)
        assert call_count["count"] == 1  # Should not increment
        assert result1 == result2
        print("   ✅ Cache hit works!")

    def test_cached_query_cache_disabled(self):
        """Test that cache is bypassed when disabled."""
        print("\n🔄 Testing cache bypass...")
        clear_cache()
        
        call_count = {"count": 0}
        
        def mock_query(query, db_path, n_results, where):
            call_count["count"] += 1
            return {"result": call_count["count"]}
        
        query = "test query"
        db_path = Path("./test_db")
        
        # Both calls with cache disabled - should execute both times
        result1 = cached_query(mock_query, query, db_path, 5, None, use_cache=False)
        result2 = cached_query(mock_query, query, db_path, 5, None, use_cache=False)
        
        assert call_count["count"] == 2
        print("   ✅ Cache bypass works!")

