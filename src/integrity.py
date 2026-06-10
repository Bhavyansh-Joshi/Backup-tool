"""
integrity.py
-----------------
Verifies the backup folder against the hash database.
Detects: intact files, corrupted files, untracked files.

"""

from pathlib import Path
from dataclasses import dataclass, field

from src import hasher, hash_db
from src.config import DESTINATION


@dataclass
class IntegrityResult:
    # Structured result from an integrity check.
    ok:        int = 0
    corrupted: int = 0
    untracked: int = 0
    corrupted_files: list[str] = field(default_factory=list)
    untracked_files: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return self.corrupted == 0 and self.untracked == 0


def check() -> IntegrityResult | None:
    # Walk every file in DESTINATION, recompute SHA-256, compare against the hash database.

    db = hash_db.load()

    if not db:
        return None

    path_to_hash = hash_db.get_path_to_hash_map(db)
    result = IntegrityResult()

    backup_files = [
        p for p in DESTINATION.rglob("*")
        if p.is_file() and p.name != ".hash_db.json"
    ]

    for backup_file in backup_files:
        parts = backup_file.relative_to(DESTINATION).parts
        rel = str(backup_file.relative_to(DESTINATION)).replace("\\", "/")

        if rel not in path_to_hash:
            result.untracked += 1
            result.untracked_files.append(rel)
            _emit_untracked(rel)
            continue

        expected = path_to_hash[rel]
        actual   = hasher.sha256(backup_file)

        if actual == expected:
            result.ok += 1
            _emit_ok(rel)
        else:
            result.corrupted += 1
            result.corrupted_files.append(rel)
            _emit_corrupted(rel)

    return result


# ================ Internal event emitters =====================

def _emit_ok(rel: str):
    print(f"  ✅  {rel}")

def _emit_corrupted(rel: str):
    print(f"  🔄️  {rel}  ← CORRUPTED")

def _emit_untracked(rel: str):
    print(f"  ⚠️   {rel}  ← untracked")
