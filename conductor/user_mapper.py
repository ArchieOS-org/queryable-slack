"""
Identity resolution for Slack users.

Maps Slack user IDs to user metadata, handles bot detection.
"""

import json
import logging
from pathlib import Path
from typing import Dict

from conductor.models import UserMap

logger = logging.getLogger(__name__)


def load_users(export_path: Path) -> Dict[str, UserMap]:
    """
    Load users.json and create a UserMap dictionary.

    Args:
        export_path: Path to Slack export root directory

    Returns:
        Dictionary mapping user_id -> UserMap object

    Raises:
        FileNotFoundError: If users.json doesn't exist
        json.JSONDecodeError: If users.json is invalid JSON
        ValueError: If user data validation fails
    """
    users_file = export_path / "users.json"

    if not users_file.exists():
        logger.error(f"users.json not found at {users_file}")
        raise FileNotFoundError(f"users.json not found at {users_file}")

    try:
        with open(users_file, "r", encoding="utf-8") as f:
            raw_users = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {users_file}: {e}")
        raise

    if not isinstance(raw_users, list):
        logger.error(f"users.json must contain an array, got {type(raw_users)}")
        raise ValueError(f"users.json must contain an array, got {type(raw_users)}")

    user_map: Dict[str, UserMap] = {}
    errors = 0

    for raw_user in raw_users:
        try:
            user = UserMap.model_validate(raw_user)
            user_map[user.id] = user
        except Exception as e:
            errors += 1
            logger.warning(f"Failed to parse user {raw_user.get('id', 'unknown')}: {e}")
            # Continue processing - don't stop on bad data

    logger.info(f"Loaded {len(user_map)} users from {users_file} (skipped {errors} invalid entries)")

    return user_map
