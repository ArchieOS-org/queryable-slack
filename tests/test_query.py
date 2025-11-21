"""
Tests for query functionality.

Tests ChromaDB querying and metadata filtering.
"""

import pytest
from pathlib import Path
import chromadb
from conductor.ask import query_chromadb, format_context


class TestChromaDBQuery:
    """Tests for ChromaDB querying."""

    @pytest.fixture
    def test_db(self, tmp_path):
        """Create a test ChromaDB database."""
        db_path = tmp_path / "test_db"
        client = chromadb.PersistentClient(path=str(db_path))
        
        # Create collection
        collection = client.get_or_create_collection(
            name="conductor_sessions",
            metadata={"description": "Test sessions"}
        )
        
        # Add test documents
        collection.add(
            ids=["session1", "session2", "session3"],
            documents=[
                "This is a test session about real estate properties.",
                "Discussion about CSV files and spreadsheets.",
                "Video file processing and multimedia content.",
            ],
            metadatas=[
                {"channel": "test-channel", "file_count": 2, "date": "2025-01-01"},
                {"channel": "test-channel", "file_count": 1, "date": "2025-01-02"},
                {"channel": "test-channel", "file_count": 0, "date": "2025-01-03"},
            ]
        )
        
        return db_path

    def test_query_chromadb_basic(self, test_db):
        """Test basic ChromaDB query."""
        results = query_chromadb("real estate", db_path=test_db, n_results=2)
        
        assert isinstance(results, dict)
        assert "documents" in results
        assert "metadatas" in results
        assert "distances" in results
        assert len(results["documents"][0]) > 0

    def test_query_chromadb_with_filter(self, test_db):
        """Test ChromaDB query with metadata filter."""
        # Query for sessions with files
        where_filter = {"file_count": {"$gt": 0}}
        results = query_chromadb(
            "files",
            db_path=test_db,
            n_results=5,
            where=where_filter
        )
        
        assert isinstance(results, dict)
        if results.get("metadatas") and results["metadatas"][0]:
            # All results should have file_count > 0
            for metadata in results["metadatas"][0]:
                assert metadata.get("file_count", 0) > 0

    def test_query_chromadb_no_results(self, test_db):
        """Test query that returns no results."""
        # Query for something that doesn't exist
        results = query_chromadb(
            "nonexistent topic xyzabc123",
            db_path=test_db,
            n_results=1
        )
        
        # Should still return dict structure, may be empty
        assert isinstance(results, dict)


class TestContextFormatting:
    """Tests for context formatting."""

    def test_format_context_with_results(self):
        """Test formatting context from query results."""
        results = {
            "documents": [["Document 1 content", "Document 2 content"]],
            "metadatas": [[
                {"channel": "test", "date": "2025-01-01", "file_count": 1},
                {"channel": "test", "date": "2025-01-02", "file_count": 2},
            ]]
        }
        
        context = format_context(results)
        
        assert isinstance(context, str)
        assert "Document 1 content" in context
        assert "Document 2 content" in context
        assert "test" in context
        assert "2025-01-01" in context

    def test_format_context_empty_results(self):
        """Test formatting context with empty results."""
        results = {
            "documents": [[]],
            "metadatas": [[]]
        }
        
        context = format_context(results)
        
        assert isinstance(context, str)
        assert "No relevant context found" in context or len(context) == 0

    def test_format_context_missing_keys(self):
        """Test formatting context with missing keys."""
        results = {}
        
        context = format_context(results)
        
        # Should handle gracefully
        assert isinstance(context, str)

