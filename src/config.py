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

# Destination for dumping the data of a SD-card or drive
DUMP_PRIMARY: Path = Path.home()/ "F:/DumpStore"
DUMP_SECONDARY: Path = Path.home()/ "F:/DumpStore"

# Where the hash is stored inside DESTINATION
DUMP_DB_FILE: Path = DUMP_PRIMARY / ".dump_db.json"