"""
Integration tests for Tier 1 and Tier 2 features working together.

Tests caching + hybrid search, chunking + storage, etc.
"""

import pytest
from pathlib import Path
from conductor.cache import cached_query, clear_cache
from conductor.chunking import chunk_session, should_chunk_session
from conductor.models import Session
from datetime import datetime


class TestTier1Tier2Integration:
    """Integration tests for Tier 1 and Tier 2."""

    def test_cache_with_hybrid_search_pattern(self):
        """Test that caching works with hybrid search pattern."""
        print("\n🔄 Testing cache + hybrid search pattern...")
        clear_cache()
        
        call_count = {"count": 0}
        
        def mock_hybrid_search(query, db_path, n_results, where):
            call_count["count"] += 1
            return {"result": f"hybrid_{call_count['count']}"}
        
        query = "test query"
        db_path = Path("./test_db")
        
        # First call
        result1 = cached_query(mock_hybrid_search, query, db_path, 5, None, use_cache=True)
        assert call_count["count"] == 1
        
        # Second call should use cache
        result2 = cached_query(mock_hybrid_search, query, db_path, 5, None, use_cache=True)
        assert call_count["count"] == 1
        assert result1 == result2
        
        print("   ✅ Cache works with hybrid search pattern!")

    def test_chunking_preserves_session_structure(self):
        """Test that chunking preserves session structure for storage."""
        print("\n📦 Testing chunking for storage...")
        
        large_session = Session(
            session_id="test_chunk_storage",
            start_time=datetime.now(),
            end_time=datetime.now(),
            channel_name="test-channel",
            conversation_type="channel",
            transcript="Test transcript",
            enriched_transcript="A" * 50000,
            file_count=5,
            message_count=100,
        )
        
        chunks = chunk_session(large_session)
        
        # Verify chunks can be used for ChromaDB storage
        for chunk in chunks:
            assert "session_id" in chunk
            assert "chunk_id" in chunk
            assert "enriched_transcript" in chunk
            assert "metadata" not in chunk  # Should be flat structure
            
            # Verify required fields for ChromaDB
            assert chunk["channel_name"] == large_session.channel_name
            assert chunk["conversation_type"] == large_session.conversation_type
        
        print(f"   ✅ Chunking produces {len(chunks)} storage-ready chunks!")

    def test_multiple_features_together(self):
        """Test that multiple Tier 1/2 features work together."""
        print("\n🔄 Testing multiple features together...")
        
        # Test chunking
        large_session = Session(
            session_id="test_multi",
            start_time=datetime.now(),
            end_time=datetime.now(),
            channel_name="test-channel",
            conversation_type="channel",
            transcript="Test",
            enriched_transcript="A" * 50000,
            file_count=3,
            message_count=50,
        )
        
        assert should_chunk_session(large_session)
        chunks = chunk_session(large_session)
        assert len(chunks) > 1
        
        # Test cache
        clear_cache()
        from conductor.cache import get_cache_stats
        stats = get_cache_stats()
        assert stats["total_entries"] == 0
        
        print("   ✅ Multiple features work together!")

