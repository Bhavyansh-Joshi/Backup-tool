"""
dump_db.py
--------------
Manages the persistent hash database (JSON file on disk).

Schema:
    {
        "<sha256_hex>": {
            "path": "relative/path/in/DumpStore",
            "ts":   "2024-01-01 12:00:00"
        }
    }

Keyed by content hash — not filename.
"""

import json
from pathlib import Path
from datetime import datetime

from src.config import DUMP_DB_FILE

def load() -> dict:
    # load the hash database from the disk return empty dict if missing
    if DUMP_DB_FILE.exists():
        try:
            with open(DUMP_DB_FILE, "r") as f:
                return json.load(f)
        except(json.JSONDecodeError, IOError):
            return{}
    return{}

def save(db: dict) -> None:
    # Persist the dump hash database to disk.
    DUMP_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DUMP_DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def exists(file_hash:str, db: dict) -> bool:
    # If correct hash is already in the database
    return file_hash in db

def register(file_hash: str, rel_path: str, db:dict) -> None:
    # Record new enty in the database
    db[file_hash] = {
        "path": rel_path.replace("\\", "/"),
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def get_path_to_hash_map(db: dict) -> dict[str, str]:
    # Return a reverse map of { relative_path -> hash }.
    return {v["path"]: k for k, v in db.items()}