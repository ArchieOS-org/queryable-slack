"""
Tests for Tier 2: Session Chunking.

Tests chunking of large sessions that exceed token limits.
"""

import pytest
from conductor.chunking import chunk_session, should_chunk_session
from conductor.models import Session
from datetime import datetime


class TestSessionChunking:
    """Tests for session chunking functionality."""

    def test_chunking_available(self):
        """Test that chunking module is available."""
        print("\n📦 Testing chunking availability...")
        try:
            from conductor.chunking import chunk_session, should_chunk_session
            assert True
        except ImportError:
            pytest.fail("chunking module should be available")
        print("   ✅ Chunking module available!")

    def test_small_session_no_chunking(self):
        """Test that small sessions are not chunked."""
        print("\n📦 Testing small session (no chunking)...")
        
        session = Session(
            session_id="test_small",
            start_time=datetime.now(),
            end_time=datetime.now(),
            channel_name="test-channel",
            conversation_type="channel",
            transcript="Short transcript",
            enriched_transcript="Short enriched transcript",
            file_count=0,
            message_count=1,
        )
        
        assert not should_chunk_session(session)
        
        chunks = chunk_session(session)
        assert len(chunks) == 1
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["total_chunks"] == 1
        print("   ✅ Small session not chunked!")

    def test_large_session_chunking(self):
        """Test that large sessions are chunked."""
        print("\n📦 Testing large session (chunking)...")
        
        # Create a large enriched transcript (> 40K chars = > 10K tokens)
        large_text = "A" * 50000  # 50K chars = ~12.5K tokens
        
        session = Session(
            session_id="test_large",
            start_time=datetime.now(),
            end_time=datetime.now(),
            channel_name="test-channel",
            conversation_type="channel",
            transcript="Large transcript",
            enriched_transcript=large_text,
            file_count=5,
            message_count=100,
        )
        
        assert should_chunk_session(session)
        
        chunks = chunk_session(session)
        assert len(chunks) > 1
        assert chunks[0]["chunk_index"] == 0
        assert chunks[-1]["chunk_index"] == len(chunks) - 1
        assert all(chunk["total_chunks"] == len(chunks) for chunk in chunks)
        
        print(f"   ✅ Large session chunked into {len(chunks)} chunks!")

    def test_chunk_metadata_preservation(self):
        """Test that chunk metadata is preserved correctly."""
        print("\n📦 Testing chunk metadata...")
        
        session = Session(
            session_id="test_meta",
            start_time=datetime(2024, 1, 1, 10, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 0),
            channel_name="test-channel",
            conversation_type="channel",
            transcript="Test",
            enriched_transcript="A" * 50000,
            file_count=3,
            message_count=50,
        )
        
        chunks = chunk_session(session)
        
        # All chunks should have same session metadata
        for chunk in chunks:
            assert chunk["session_id"] == session.session_id
            assert chunk["channel_name"] == session.channel_name
            assert chunk["conversation_type"] == session.conversation_type
            assert chunk["start_time"] == session.start_time
            assert chunk["end_time"] == session.end_time
        
        # First chunk should have full transcript and file_count
        assert chunks[0]["transcript"] == session.transcript
        assert chunks[0]["file_count"] == session.file_count
        
        # Other chunks should have empty transcript and file_count=0
        for chunk in chunks[1:]:
            assert chunk["transcript"] == ""
            assert chunk["file_count"] == 0
        
        print("   ✅ Chunk metadata preserved correctly!")

    def test_chunk_overlap(self):
        """Test that chunks have overlap for context preservation."""
        print("\n📦 Testing chunk overlap...")
        
        # Create text with clear markers
        large_text = "CHUNK1 " * 20000 + "CHUNK2 " * 20000
        
        session = Session(
            session_id="test_overlap",
            start_time=datetime.now(),
            end_time=datetime.now(),
            channel_name="test-channel",
            conversation_type="channel",
            transcript="Test",
            enriched_transcript=large_text,
            file_count=0,
            message_count=1,
        )
        
        chunks = chunk_session(session)
        
        if len(chunks) > 1:
            # Check that chunks have overlap markers
            assert "[CONTEXT FROM PREVIOUS CHUNK]" in chunks[1]["enriched_transcript"]
            assert "[CONTEXT FOR NEXT CHUNK]" in chunks[0]["enriched_transcript"]
            print("   ✅ Chunk overlap preserved!")
        else:
            print("   ⚠️  Session not large enough for multiple chunks")

