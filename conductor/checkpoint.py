"""
Checkpoint and resume functionality for ingestion pipeline.

Tracks successfully processed conversations and failed ones for retry.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manages checkpoint state for resumable ingestion."""
    
    def __init__(self, checkpoint_path: Optional[Path] = None):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_path: Path to checkpoint JSON file. If None, uses default location.
        """
        if checkpoint_path is None:
            checkpoint_path = Path.home() / ".conductor_ingestion_checkpoint.json"
        
        self.checkpoint_path = checkpoint_path
        self._state: Dict[str, any] = {
            "completed": {},  # conversation_dir -> {"sessions": count, "files": count, "timestamp": iso}
            "failed": {},      # conversation_dir -> {"error": str, "timestamp": iso, "retry_count": int}
            "failed_files": {},  # file_path -> {"error": str, "error_type": str, "timestamp": iso, "retry_count": int, "conversation": str}
            "last_updated": None,
        }
        self._load()
    
    def _load(self) -> None:
        """Load checkpoint state from file."""
        if self.checkpoint_path.exists():
            try:
                with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        # Empty file - start fresh
                        logger.warning("⚠️  Checkpoint file is empty. Starting fresh.")
                        self._state = {
                            "completed": {},
                            "failed": {},
                            "failed_files": {},
                            "last_updated": None,
                        }
                        return
                    
                    self._state = json.loads(content)
                    
                    # Validate structure
                    if not isinstance(self._state, dict):
                        raise ValueError("Checkpoint file is not a valid JSON object")
                    
                    # Ensure required keys exist
                    self._state.setdefault("completed", {})
                    self._state.setdefault("failed", {})
                    self._state.setdefault("failed_files", {})
                    
                logger.info(f"✅ Loaded checkpoint: {len(self._state.get('completed', {}))} completed, {len(self._state.get('failed', {}))} failed")
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️  Checkpoint file is corrupted (JSON error: {e}). Starting fresh.")
                # Backup corrupted file
                backup_path = self.checkpoint_path.with_suffix('.json.bak')
                try:
                    import shutil
                    shutil.copy2(self.checkpoint_path, backup_path)
                    logger.info(f"💾 Backed up corrupted checkpoint to {backup_path}")
                except Exception:
                    pass
                self._state = {
                    "completed": {},
                    "failed": {},
                    "failed_files": {},
                    "last_updated": None,
                }
            except Exception as e:
                logger.warning(f"⚠️  Failed to load checkpoint: {e}. Starting fresh.")
                self._state = {
                    "completed": {},
                    "failed": {},
                    "failed_files": {},
                    "last_updated": None,
                }
        else:
            logger.info("📝 No checkpoint found. Starting fresh ingestion.")
    
    def save(self) -> None:
        """Save checkpoint state to file."""
        self._state["last_updated"] = datetime.now().isoformat()
        try:
            self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
            logger.debug(f"💾 Checkpoint saved to {self.checkpoint_path}")
        except Exception as e:
            logger.warning(f"⚠️  Failed to save checkpoint: {e}")
    
    def is_completed(self, conversation_dir: str) -> bool:
        """Check if conversation was successfully completed."""
        return conversation_dir in self._state.get("completed", {})
    
    def mark_completed(self, conversation_dir: str, sessions: int, files: int) -> None:
        """Mark conversation as successfully completed."""
        self._state.setdefault("completed", {})[conversation_dir] = {
            "sessions": sessions,
            "files": files,
            "timestamp": datetime.now().isoformat(),
        }
        # Remove from failed if it was there
        self._state.setdefault("failed", {}).pop(conversation_dir, None)
        self.save()
    
    def mark_failed(self, conversation_dir: str, error: str) -> None:
        """Mark conversation as failed."""
        failed_entry = self._state.setdefault("failed", {}).get(conversation_dir, {})
        retry_count = failed_entry.get("retry_count", 0) + 1
        
        self._state["failed"][conversation_dir] = {
            "error": str(error),
            "timestamp": datetime.now().isoformat(),
            "retry_count": retry_count,
        }
        self.save()
    
    def get_failed(self) -> Dict[str, Dict]:
        """Get all failed conversations."""
        return self._state.get("failed", {})
    
    def get_completed(self) -> Set[str]:
        """Get set of completed conversation directories."""
        return set(self._state.get("completed", {}).keys())
    
    def get_stats(self) -> Dict[str, int]:
        """Get checkpoint statistics."""
        return {
            "completed": len(self._state.get("completed", {})),
            "failed": len(self._state.get("failed", {})),
        }
    
    def mark_file_failed(self, file_path: str, error: str, error_type: str, conversation_dir: str) -> None:
        """Mark a specific file as failed for retry."""
        failed_entry = self._state.setdefault("failed_files", {}).get(file_path, {})
        retry_count = failed_entry.get("retry_count", 0) + 1
        
        self._state["failed_files"][file_path] = {
            "error": str(error),
            "error_type": str(error_type),
            "timestamp": datetime.now().isoformat(),
            "retry_count": retry_count,
            "conversation": conversation_dir,
        }
        self.save()
    
    def mark_file_success(self, file_path: str) -> None:
        """Mark a file as successfully processed (remove from failed list)."""
        self._state.setdefault("failed_files", {}).pop(file_path, None)
        self.save()
    
    def get_failed_files(self, conversation_dir: Optional[str] = None) -> Dict[str, Dict]:
        """Get all failed files, optionally filtered by conversation."""
        failed_files = self._state.get("failed_files", {})
        if conversation_dir:
            return {
                path: info for path, info in failed_files.items()
                if info.get("conversation") == conversation_dir
            }
        return failed_files
    
    def is_file_failed(self, file_path: str) -> bool:
        """Check if a file was previously failed."""
        return file_path in self._state.get("failed_files", {})
    
    def clear(self) -> None:
        """Clear checkpoint state (start fresh)."""
        self._state = {
            "completed": {},
            "failed": {},
            "failed_files": {},
            "last_updated": None,
        }
        if self.checkpoint_path.exists():
            self.checkpoint_path.unlink()
        logger.info("🗑️  Checkpoint cleared")
    
    def get_failed_files_stats(self) -> Dict[str, int]:
        """Get statistics about failed files by error type."""
        failed_files = self._state.get("failed_files", {})
        stats = {}
        for file_info in failed_files.values():
            error_type = file_info.get("error_type", "unknown")
            stats[error_type] = stats.get(error_type, 0) + 1
        return stats


def get_already_processed_channels(db_path: Path) -> Set[str]:
    """
    Query ChromaDB to get list of channels that already have sessions stored.
    
    Args:
        db_path: Path to ChromaDB directory
        
    Returns:
        Set of channel names that have been processed
    """
    try:
        from conductor.ingest import _get_chromadb
        chromadb = _get_chromadb()
        client = chromadb.PersistentClient(path=str(db_path))
        
        try:
            collection = client.get_collection(name="conductor_sessions")
            
            # Get all documents to extract unique channels
            # Use a query with a dummy text to get metadata
            results = collection.get(
                limit=10000,  # Get up to 10k records
                include=["metadatas"]
            )
            
            channels = set()
            if results and results.get("metadatas"):
                for metadata in results["metadatas"]:
                    if metadata and "channel" in metadata:
                        channels.add(metadata["channel"])
            
            logger.info(f"📊 Found {len(channels)} channels already in ChromaDB")
            return channels
            
        except Exception as e:
            # Collection doesn't exist yet or empty
            logger.debug(f"Collection not found or empty: {e}")
            return set()
            
    except Exception as e:
        logger.warning(f"⚠️  Could not query ChromaDB for existing channels: {e}")
        return set()

