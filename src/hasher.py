"""
hasher.py
--------------
File hashing. Compute SHA-256 of a file.

"""

import hashlib
from pathlib import Path

CHUNK_SIZE = 65536  # 64 KB read chunk

def sha256(path: Path) -> str:
    # Return the SHA-256 hex digest of a file.Reads in chunks so large files don't blow memory.

    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()

def files_are_identical(path_a: Path, path_b: Path) -> bool:
    # Check if 2 files are identical
    return sha256(path_a) == sha256(path_b)