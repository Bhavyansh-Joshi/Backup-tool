"""
config.py
---------
Single source of truth for all configurable values.
Change settings here — nowhere else.
"""

from pathlib import Path

# The main BackUp-Directory
DESTINATION: Path = Path.home()/ "F:/Backup"

# Where the hash is stored inside DESTINATION
HASH_DB_FILE: Path = DESTINATION / ".hash_db.json"

# How often to poll for new drive
POLL_INTERVAL: int = 3

# File extention to always skip
SKIP_EXTENSIONS: set[str] = {".tmp", ".ds_store", ".hash_db", ".pif"}

# Log file to add logs
LOG_DIR: Path = DESTINATION / "logs/backup.log"