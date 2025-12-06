# scripts/dev/reset_logs_files.py
"""
Script to delete all log files (*.log) from the logs folder.

WARNING: This will permanently delete log data.

Usage:
    python scripts/dev/reset_logs_files.py
"""

# imports built-in modules
import logging
import sys
from pathlib import Path


def main():
    """
    Set up paths, validate config, and delete all .log files in the logs folder.
    """
    # Add project root to path to allow local imports
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    # Local imports are here to avoid ruff E402
    from src.config import config  # noqa: E402

    # Validate config before proceeding
    config.validate_or_exit()

    # Use a console-only logger to avoid file lock issues
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    logs_dir = Path(config.LOGS_DIR)

    logger.warning(f"⚠️ This will delete all *.log files in the '{logs_dir}' folder!")
    confirm = input("Are you sure? (type 'yes' to confirm): ").strip().lower()

    if confirm != "yes":
        logger.info("❌ Operation aborted by user.")
        return

    if not logs_dir.is_dir():
        logger.info(f"ℹ️ The logs directory '{logs_dir}' does not exist. Nothing to do.")
        return

    log_files_deleted = 0
    for log_file in logs_dir.glob("*.log"):
        log_file.unlink()
        log_files_deleted += 1

    logger.info(
        f"✅ Successfully deleted {log_files_deleted} log file(s) from '{logs_dir}'."
    )


if __name__ == "__main__":
    main()
