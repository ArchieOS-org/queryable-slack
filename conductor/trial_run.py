"""
Trial run script for testing Conductor with a small subset of data.

This script allows you to test the ingestion pipeline with a limited number
of conversations or messages before running on the full dataset.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from conductor.ingest import main as ingest_main

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_trial_export(
    source_export: Path,
    trial_export: Path,
    max_conversations: int = 3,
    max_days_per_conversation: int = 5,
) -> Path:
    """
    Create a trial export with limited data for testing.

    Args:
        source_export: Path to full Slack export
        trial_export: Path where trial export will be created
        max_conversations: Maximum number of conversations to include
        max_days_per_conversation: Maximum number of daily files per conversation

    Returns:
        Path to the trial export directory
    """
    if trial_export.exists():
        logger.warning(f"Trial export directory already exists: {trial_export}")
        response = input("Delete and recreate? (y/N): ")
        if response.lower() != "y":
            logger.info("Using existing trial export")
            return trial_export
        shutil.rmtree(trial_export)

    trial_export.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Creating trial export at {trial_export}")
    print(f"📁 Creating trial export directory: {trial_export.name}")

    # Copy essential metadata files
    essential_files = ["users.json", "channels.json", "dms.json", "mpims.json", "groups.json"]
    logger.info(f"📋 Copying {len(essential_files)} essential metadata files...")
    print(f"📋 Copying metadata files...")
    for filename in essential_files:
        source_file = source_export / filename
        if source_file.exists():
            shutil.copy2(source_file, trial_export / filename)
            logger.debug(f"Copied {filename}")
        else:
            logger.warning(f"Metadata file not found: {filename}")
    print(f"✅ Metadata files copied")

    # Get list of conversation directories
    logger.info(f"🔍 Scanning for conversation directories...")
    print(f"🔍 Scanning source export for conversations...")
    conversations = []
    for item in source_export.iterdir():
        if item.is_dir() and item.name != "attachments":
            # Check if it's a conversation directory (has JSON files)
            json_files = list(item.glob("*.json"))
            if json_files:
                conversations.append(item)

    logger.info(f"Found {len(conversations)} total conversations in source export")
    
    # Limit conversations
    conversations = conversations[:max_conversations]
    logger.info(f"✅ Selected {len(conversations)} conversations for trial")
    print(f"✅ Selected {len(conversations)} conversations for trial export")

    # Copy conversation directories with limited daily files
    logger.info(f"📦 Copying conversation data...")
    print(f"📦 Copying conversation data...")
    for idx, conv_dir in enumerate(conversations, 1):
        logger.info(f"  [{idx}/{len(conversations)}] Processing: {conv_dir.name}")
        print(f"  [{idx}/{len(conversations)}] Processing: {conv_dir.name}")
        dest_dir = trial_export / conv_dir.name
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Get daily JSON files, sorted by date
        daily_files = sorted([f for f in conv_dir.iterdir() if f.is_file() and f.suffix == ".json"])
        logger.debug(f"    Found {len(daily_files)} daily files in {conv_dir.name}")

        # Limit daily files
        daily_files = daily_files[:max_days_per_conversation]
        logger.info(f"    Limiting to {len(daily_files)} daily files")

        # Copy daily files
        for daily_file in daily_files:
            shutil.copy2(daily_file, dest_dir / daily_file.name)

        # Copy attachments directory if it exists (with all files)
        attachments_dir = conv_dir / "attachments"
        if attachments_dir.exists() and attachments_dir.is_dir():
            dest_attachments = dest_dir / "attachments"
            attachment_count = len(list(attachments_dir.rglob("*")))
            shutil.copytree(attachments_dir, dest_attachments, dirs_exist_ok=True)
            logger.info(f"    Copied {attachment_count} attachment(s) from {conv_dir.name}")
            print(f"      ✅ Copied {attachment_count} attachment(s)")

        logger.info(f"    ✅ Copied {len(daily_files)} daily files from {conv_dir.name}")
        print(f"      ✅ Copied {len(daily_files)} daily files")

    logger.info(f"✅ Trial export created successfully at {trial_export}")
    print(f"✅ Trial export created: {trial_export.name}")
    return trial_export


def main(
    source_export: Path,
    trial_export_path: Optional[Path] = None,
    max_conversations: int = 3,
    max_days_per_conversation: int = 5,
    run_ingestion: bool = True,
) -> None:
    """
    Create a trial export and optionally run ingestion.

    Args:
        source_export: Path to full Slack export
        trial_export_path: Path for trial export (defaults to source_export.parent / "trial_export")
        max_conversations: Maximum number of conversations to include
        max_days_per_conversation: Maximum number of daily files per conversation
        run_ingestion: Whether to run ingestion after creating trial export
    """
    if trial_export_path is None:
        # Add datestamp to trial export folder name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trial_export_path = source_export.parent / f"trial_export_{timestamp}"

    logger.info("=" * 80)
    logger.info("TRIAL RUN MODE (PREVIEW)")
    logger.info("=" * 80)
    logger.info(f"Source export: {source_export}")
    logger.info(f"Trial export: {trial_export_path}")
    logger.info(f"Max conversations: {max_conversations}")
    logger.info(f"Max days per conversation: {max_days_per_conversation}")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    # Create trial export
    trial_export = create_trial_export(
        source_export=source_export,
        trial_export=trial_export_path,
        max_conversations=max_conversations,
        max_days_per_conversation=max_days_per_conversation,
    )

    if run_ingestion:
        logger.info("🚀 Running ingestion on trial export...")
        print(f"\n🚀 Starting ingestion process...")
        # Use datestamped database path for trial runs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trial_db_path = Path(f"./conductor_db_preview_{timestamp}")
        ingest_main(trial_export, db_path=trial_db_path)
        logger.info("=" * 80)
        logger.info("✅ Trial run complete!")
        logger.info(f"📊 Trial export location: {trial_export}")
        logger.info(f"💾 Database location: conductor_db/")
        logger.info(f"🔍 You can now query the system with:")
        logger.info(f'   python -m conductor.ask "your question here"')
        logger.info(f"⏱️  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)
        print(f"\n✅ Trial run complete!")
        print(f"📊 Trial export: {trial_export.name}")
        print(f"💾 Database: conductor_db/")
        print(f"🔍 Query with: python -m conductor.ask \"your question\"")
    else:
        logger.info("Trial export created. Run ingestion manually with:")
        logger.info(f"  python -m conductor.ingest {trial_export}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m conductor.trial_run <path_to_slack_export> [trial_export_path] [--max-conversations N] [--max-days N] [--no-ingest]")
        print("\nExample:")
        print("  python -m conductor.trial_run /path/to/export")
        print("  python -m conductor.trial_run /path/to/export --max-conversations 5 --max-days 10")
        print("  python -m conductor.trial_run /path/to/export /custom/trial/path --no-ingest")
        sys.exit(1)

    source_path = Path(sys.argv[1])
    if not source_path.exists():
        print(f"Error: Source export path does not exist: {source_path}")
        sys.exit(1)

    # Parse optional arguments
    trial_path = None
    max_conv = 3
    max_days = 5
    run_ingest = True

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--max-conversations" and i + 1 < len(sys.argv):
            max_conv = int(sys.argv[i + 1])
            i += 2
        elif arg == "--max-days" and i + 1 < len(sys.argv):
            max_days = int(sys.argv[i + 1])
            i += 2
        elif arg == "--no-ingest":
            run_ingest = False
            i += 1
        elif not arg.startswith("--"):
            trial_path = Path(arg)
            i += 1
        else:
            i += 1

    main(
        source_export=source_path,
        trial_export_path=trial_path,
        max_conversations=max_conv,
        max_days_per_conversation=max_days,
        run_ingestion=run_ingest,
    )

