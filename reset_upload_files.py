# reset_files.py
"""
Script to delete the public folder for testing and debugging purposes.
Use with caution in production!
"""

# imports built-in modules
import shutil
from pathlib import Path


def reset_public_folder():
    """Delete entire public folder."""
    public_dir = Path("public")
    if public_dir.exists():
        shutil.rmtree(public_dir)
        print("✅ Public folder deleted")
    else:
        print("ℹ️ Public folder doesn't exist")


if __name__ == "__main__":
    reset_public_folder()
