"""
Integration tests for the complete pipeline.

Tests end-to-end functionality from file parsing to querying.
"""

import pytest
from pathlib import Path
import json
import csv
from conductor.file_parser import extract_text_from_file, extract_file_metadata
from conductor.ingest import enrich_session_with_files
from conductor.models import Session, SlackMessage
from datetime import datetime


class TestFileParsingIntegration:
    """Integration tests for file parsing."""

    def test_csv_to_enriched_session(self, tmp_path):
        """Test that CSV files are parsed and included in enriched sessions."""
        print("\n🔗 Testing CSV integration with session enrichment...")
        # Create test CSV with proper naming pattern: {file_id}-{filename}
        file_id = "F12345"
        filename = "test.csv"
        csv_file = tmp_path / "attachments" / f"{file_id}-{filename}"
        csv_file.parent.mkdir(parents=True)
        print(f"   Creating CSV file: {csv_file}")
        
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Property", "Price"])
            writer.writerow(["123 Main St", "$500,000"])
        print("   ✅ CSV file created")
        
        print("   Creating session and messages...")
        # Create a session with file attachment
        session = Session(
            session_id="test-session",
            start_time=datetime.now(),
            end_time=datetime.now(),
            channel_name="test-channel",
            conversation_type="channel",
            transcript="User: Check this CSV file",
            enriched_transcript="",
            file_count=0,
            message_count=1,
        )
        
        # Create message with file reference
        messages = [
            SlackMessage(
                ts="1234567890.123456",
                user="U12345",
                text="Check this CSV file",
                type="message",
                files=[{"id": file_id, "name": filename, "filetype": "csv"}]
            )
        ]
        print("   ✅ Session and messages created")
        
        print("   Enriching session with files...")
        # Enrich session
        enriched = enrich_session_with_files(session, messages, tmp_path)
        print(f"   ✅ Session enriched: {enriched.file_count} files processed")
        
        # Check that CSV content is in enriched transcript
        print("   Verifying enriched content...")
        assert "CSV" in enriched.enriched_transcript or "Property" in enriched.enriched_transcript
        assert "ATTACHMENT" in enriched.enriched_transcript
        assert "Property" in enriched.enriched_transcript or "Price" in enriched.enriched_transcript
        print("   ✅ Integration test passed!")

    def test_multiple_file_types_in_session(self, tmp_path):
        """Test that multiple file types are processed correctly."""
        print("\n🔗 Testing multiple file types integration...")
        attachments_dir = tmp_path / "attachments"
        attachments_dir.mkdir(parents=True)
        
        # Create multiple file types with proper naming pattern: {file_id}-{filename}
        print("   Creating multiple file types...")
        (attachments_dir / "F1-test.csv").write_text("Name,Value\nTest,42")
        (attachments_dir / "F2-test.txt").write_text("Plain text content")
        (attachments_dir / "F3-test.png").write_bytes(b"fake image")
        print("   ✅ Created CSV, TXT, and PNG files")
        
        session = Session(
            session_id="test-session",
            start_time=datetime.now(),
            end_time=datetime.now(),
            channel_name="test-channel",
            conversation_type="channel",
            transcript="User: Multiple files",
            enriched_transcript="",
            file_count=0,
            message_count=1,
        )
        
        messages = [
            SlackMessage(
                ts="1234567890.123456",
                user="U12345",
                text="Multiple files",
                type="message",
                files=[
                    {"id": "F1", "name": "test.csv", "filetype": "csv"},
                    {"id": "F2", "name": "test.txt", "filetype": "txt"},
                    {"id": "F3", "name": "test.png", "filetype": "png"},
                ]
            )
        ]
        
        print("   Enriching session with multiple files...")
        enriched = enrich_session_with_files(session, messages, tmp_path)
        print(f"   ✅ Session enriched: {enriched.file_count} files processed")
        
        # Should process all files
        print("   Verifying enriched content...")
        assert "ATTACHMENT" in enriched.enriched_transcript
        assert "test.csv" in enriched.enriched_transcript or "Name" in enriched.enriched_transcript
        assert "test.txt" in enriched.enriched_transcript or "Plain text" in enriched.enriched_transcript
        assert "test.png" in enriched.enriched_transcript or "SKIPPED" in enriched.enriched_transcript
        print("   ✅ Multiple file types integration test passed!")


class TestErrorHandlingIntegration:
    """Integration tests for error handling."""

    def test_missing_file_handles_gracefully(self, tmp_path):
        """Test that missing files don't crash the pipeline."""
        session = Session(
            session_id="test-session",
            start_time=datetime.now(),
            end_time=datetime.now(),
            channel_name="test-channel",
            conversation_type="channel",
            transcript="User: Missing file",
            enriched_transcript="",
            file_count=0,
            message_count=1,
        )
        
        messages = [
            SlackMessage(
                ts="1234567890.123456",
                user="U12345",
                text="Missing file",
                type="message",
                files=[{"id": "NONEXISTENT", "name": "missing.pdf", "filetype": "pdf"}]
            )
        ]
        
        # Should not crash
        enriched = enrich_session_with_files(session, messages, tmp_path)
        
        assert isinstance(enriched, Session)
        assert enriched.file_count == 0  # No files processed

    def test_corrupt_file_handles_gracefully(self, tmp_path):
        """Test that corrupt files don't crash the pipeline."""
        attachments_dir = tmp_path / "attachments"
        attachments_dir.mkdir(parents=True)
        
        # Create a file that looks like PDF but isn't
        fake_pdf = attachments_dir / "F12345-corrupt.pdf"
        fake_pdf.write_text("This is not a real PDF")
        
        session = Session(
            session_id="test-session",
            start_time=datetime.now(),
            end_time=datetime.now(),
            channel_name="test-channel",
            conversation_type="channel",
            transcript="User: Corrupt file",
            enriched_transcript="",
            file_count=0,
            message_count=1,
        )
        
        messages = [
            SlackMessage(
                ts="1234567890.123456",
                user="U12345",
                text="Corrupt file",
                type="message",
                files=[{"id": "F12345", "name": "corrupt.pdf", "filetype": "pdf"}]
            )
        ]
        
        # Should not crash, may return error message
        enriched = enrich_session_with_files(session, messages, tmp_path)
        
        assert isinstance(enriched, Session)

