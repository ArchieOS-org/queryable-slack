"""
Pydantic data models for Conductor.

All data models with strict typing for I/O boundaries.
Best practices:
- Comprehensive error handling with ValidationError
- Graceful degradation on bad data
- Clear error messages for debugging
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, field_validator, ValidationInfo, ValidationError


class UserMap(BaseModel):
    """Maps Slack user IDs to user metadata for identity resolution."""

    id: str
    real_name: str
    is_admin: bool
    is_bot: bool

    @field_validator("is_bot", mode="before")
    @classmethod
    def compute_is_bot(cls, v: Any, info: ValidationInfo) -> bool:
        """
        Compute is_bot from raw Slack data: is_bot OR is_app_user.
        
        Best practice: Handle missing or invalid data gracefully.
        """
        if isinstance(v, bool):
            return v
        # If not a bool, check the raw data
        try:
            raw_data = info.data if hasattr(info, "data") and isinstance(info.data, dict) else {}
            return raw_data.get("is_bot", False) or raw_data.get("is_app_user", False)
        except Exception:
            # Fallback: assume not a bot if we can't determine
            return False

    class Config:
        """Pydantic v2 config."""

        extra = "ignore"  # Ignore extra fields from Slack export


class SlackMessage(BaseModel):
    """Represents a single message from Slack export."""

    ts: str  # Unix timestamp as string (e.g., "1763652221.867399")
    user: Optional[str] = None  # User ID (may be missing for system messages)
    text: str
    type: str  # Message type (typically "message")
    files: Optional[List[Dict[str, Any]]] = None
    user_profile: Optional[Dict[str, Any]] = None

    class Config:
        """Pydantic v2 config."""

        extra = "ignore"  # Ignore extra fields from Slack export


class Session(BaseModel):
    """The atomic unit of memory - represents a conversation session."""

    session_id: str  # Deterministic hash based on channel_name and start_time
    start_time: datetime
    end_time: datetime
    channel_name: str  # Channel/conversation identifier
    conversation_type: str  # One of: "channel", "dm", "mpim"
    transcript: str  # Pure text conversation with user names resolved
    enriched_transcript: str  # Text plus injected file content
    file_count: int  # Number of files attached in this session
    message_count: int  # Number of messages in this session

    @field_validator("conversation_type")
    @classmethod
    def validate_conversation_type(cls, v: str) -> str:
        """Ensure conversation_type is one of the valid values."""
        if v not in ("channel", "dm", "mpim"):
            raise ValueError(f"conversation_type must be 'channel', 'dm', or 'mpim', got '{v}'")
        return v


class VectorRecord(BaseModel):
    """What goes into ChromaDB for vector search."""

    id: str  # Deterministic ID for idempotency (same as Session.session_id)
    document: str  # The context to embed (typically Session.enriched_transcript)
    metadata: Dict[str, Any]  # Metadata for filtering and retrieval

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure required metadata fields are present."""
        required_fields = {"date", "channel", "start_time", "end_time", "message_count", "file_count"}
        missing = required_fields - set(v.keys())
        if missing:
            raise ValueError(f"Missing required metadata fields: {missing}")
        return v
