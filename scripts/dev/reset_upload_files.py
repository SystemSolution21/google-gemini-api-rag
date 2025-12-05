# scripts/dev/reset_upload_files.py
"""
Script to delete the public folder for testing and debugging purposes.

WARNING: Use with caution in production!

Usage:
    python scripts/dev/reset_upload_files.py
"""

# imports built-in modules
import logging
import shutil
import sys
from pathlib import Path


def main():
    """
    Set up paths, validate config, and reset the public folder.
    """
    # Add project root to path to allow local imports
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    # Local module imports(avoid ruff E402 error)
    from src.config import config

    # Validate config before proceeding
    config.validate_or_exit()

    # Use a console-only logger
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    public_dir = Path(config.PUBLIC_DIR)

    logger.warning(f"⚠️ This will delete the '{public_dir}' folder!")
    confirm = input("Are you sure? (type 'yes' to confirm): ").strip().lower()

    if confirm != "yes":
        logger.info("❌ Operation aborted by user.")
        return

    if public_dir.exists():
        shutil.rmtree(public_dir)
        logger.info(f"✅ Successfully deleted the '{public_dir}' folder.")
    else:
        logger.info(f"ℹ️ The '{public_dir}' folder does not exist. Nothing to do.")


if __name__ == "__main__":
    main()
