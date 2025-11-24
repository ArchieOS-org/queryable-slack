"""
Core sessionization logic.

Timeline stitching and session creation from Slack messages.
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from conductor.models import Session, SlackMessage, UserMap

logger = logging.getLogger(__name__)

# Session threshold: 6 hours
SESSION_THRESHOLD = timedelta(hours=6)


def parse_timestamp(ts: str) -> datetime:
    """
    Parse Slack timestamp string to datetime.

    Args:
        ts: Slack timestamp string (e.g., "1763652221.867399")

    Returns:
        datetime object
    """
    try:
        timestamp_float = float(ts)
        return datetime.fromtimestamp(timestamp_float)
    except (ValueError, OSError) as e:
        logger.warning(f"Failed to parse timestamp '{ts}': {e}")
        raise ValueError(f"Invalid timestamp format: {ts}")


def load_messages_from_directory(conversation_dir: Path) -> List[SlackMessage]:
    """
    Load and merge all messages from daily JSON files in a conversation directory.

    Args:
        conversation_dir: Path to conversation directory (channel, DM, or MPIM)

    Returns:
        List of SlackMessage objects sorted by timestamp
    """
    messages: List[SlackMessage] = []
    daily_files = sorted([f for f in conversation_dir.iterdir() if f.is_file() and f.suffix == ".json"])

    for daily_file in daily_files:
        # Skip files that don't match YYYY-MM-DD.json pattern
        if not re.match(r"\d{4}-\d{2}-\d{2}\.json$", daily_file.name):
            logger.debug(f"Skipping non-date file: {daily_file.name}")
            continue

        try:
            with open(daily_file, "r", encoding="utf-8") as f:
                raw_messages = json.load(f)

            if not isinstance(raw_messages, list):
                logger.warning(f"Expected array in {daily_file.name}, got {type(raw_messages)}")
                continue

            for raw_msg in raw_messages:
                try:
                    # Only process messages of type "message"
                    if raw_msg.get("type") != "message":
                        continue

                    msg = SlackMessage.model_validate(raw_msg)
                    messages.append(msg)
                except Exception as e:
                    logger.debug(f"Failed to parse message in {daily_file.name}: {e}")
                    continue

        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {daily_file.name}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Error reading {daily_file.name}: {e}")
            continue

    # Sort by timestamp
    messages.sort(key=lambda m: float(m.ts))

    logger.info(f"Loaded {len(messages)} messages from {conversation_dir.name}")
    return messages


def generate_session_id(channel_name: str, start_time: datetime) -> str:
    """
    Generate deterministic session ID from channel name and start time.

    Args:
        channel_name: Channel/conversation identifier
        start_time: Session start time

    Returns:
        Deterministic hash string
    """
    hash_input = f"{channel_name}_{start_time.isoformat()}"
    return hashlib.sha256(hash_input.encode()).hexdigest()


def create_transcript(messages: List[SlackMessage], user_map: Dict[str, UserMap]) -> str:
    """
    Create a text transcript from messages with user names resolved.

    Args:
        messages: List of SlackMessage objects
        user_map: Dictionary mapping user_id -> UserMap

    Returns:
        Formatted transcript string
    """
    transcript_lines = []

    for msg in messages:
        if not msg.user:
            # System message or message without user
            transcript_lines.append(f"[SYSTEM]: {msg.text}")
            continue

        user = user_map.get(msg.user)
        if user:
            user_name = user.real_name
            # Optionally filter out bot messages or label them
            if user.is_bot:
                user_name = f"[BOT: {user_name}]"
        else:
            user_name = f"[UNKNOWN: {msg.user}]"

        transcript_lines.append(f"{user_name}: {msg.text}")

    return "\n".join(transcript_lines)


def sessionize_messages(
    messages: List[SlackMessage],
    channel_name: str,
    conversation_type: str,
    user_map: Dict[str, UserMap],
) -> List[Session]:
    """
    Convert messages into sessions based on 6-hour time threshold.

    Args:
        messages: List of SlackMessage objects (must be sorted by timestamp)
        channel_name: Channel/conversation identifier
        conversation_type: One of "channel", "dm", "mpim"
        user_map: Dictionary mapping user_id -> UserMap

    Returns:
        List of Session objects
    """
    if not messages:
        return []

    sessions: List[Session] = []
    current_session_messages: List[SlackMessage] = []
    session_start_time: Optional[datetime] = None

    for msg in messages:
        msg_time = parse_timestamp(msg.ts)

        if session_start_time is None:
            # First message - start new session
            session_start_time = msg_time
            current_session_messages = [msg]
        else:
            # Check if we should start a new session
            time_diff = msg_time - session_start_time

            if time_diff > SESSION_THRESHOLD:
                # Close current session and start new one
                if len(current_session_messages) >= 2:  # Discard sessions with < 2 messages
                    session = create_session(
                        current_session_messages,
                        channel_name,
                        conversation_type,
                        user_map,
                        session_start_time,
                    )
                    sessions.append(session)

                session_start_time = msg_time
                current_session_messages = [msg]
            else:
                # Add to current session
                current_session_messages.append(msg)

    # Don't forget the last session
    if len(current_session_messages) >= 2:
        session = create_session(
            current_session_messages,
            channel_name,
            conversation_type,
            user_map,
            session_start_time,
        )
        sessions.append(session)

    logger.info(f"Created {len(sessions)} sessions from {len(messages)} messages in {channel_name}")
    return sessions


def create_session(
    messages: List[SlackMessage],
    channel_name: str,
    conversation_type: str,
    user_map: Dict[str, UserMap],
    start_time: Optional[datetime] = None,
) -> Session:
    """
    Create a Session from a list of messages.

    Args:
        messages: List of SlackMessage objects (must be sorted)
        channel_name: Channel/conversation identifier
        conversation_type: One of "channel", "dm", "mpim"
        user_map: Dictionary mapping user_id -> UserMap
        start_time: Optional start time (if None, uses first message timestamp)

    Returns:
        Session object
    """
    if not messages:
        raise ValueError("Cannot create session from empty message list")

    if start_time is None:
        start_time = parse_timestamp(messages[0].ts)
    end_time = parse_timestamp(messages[-1].ts)

    session_id = generate_session_id(channel_name, start_time)
    transcript = create_transcript(messages, user_map)

    # Count files attached
    file_count = sum(1 for msg in messages if msg.files)

    # For now, enriched_transcript is the same as transcript
    # File enrichment will be done separately
    enriched_transcript = transcript

    return Session(
        session_id=session_id,
        start_time=start_time,
        end_time=end_time,
        channel_name=channel_name,
        conversation_type=conversation_type,
        transcript=transcript,
        enriched_transcript=enriched_transcript,
        file_count=file_count,
        message_count=len(messages),
    )
