"""
copy_engine.py
--------------------
Core backup logic:
  1. Scan source for files
  2. Hash each file
  3. Skip if hash already in database (deduplication)
  4. Copy to destination
  5. Verify hash after copy
  6. Register new file in database
"""

import shutil
from pathlib import Path
from dataclasses import dataclass, field

from src import hasher, hash_db
from src.config import SKIP_EXTENSIONS


@dataclass
class CopyResult:
    #Structured result from a copy operation.
    total:    int = 0
    copied:   int = 0
    skipped:  int = 0
    failed:   int = 0
    failed_files: list[str] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        return self.failed == 0 and self.total > 0


def backup(source_root: Path, dest_root: Path, db: dict) -> CopyResult:
    """
    Copy files from source_root → dest_root with dedup and verification.

    Args:
        source_root: Path to the drive/folder being backed up
        dest_root:   Path to the timestamped destination folder
        db:          The in-memory hash database (mutated in place)

    Returns:
        CopyResult with counts and any failed file paths
    """
    all_files = [
        p for p in source_root.rglob("*")
        if p.is_file() and p.suffix.lower() not in SKIP_EXTENSIONS
    ]

    result = CopyResult(total=len(all_files))

    if result.total == 0:
        return result

    for src_path in all_files:
        rel = src_path.relative_to(source_root)

        try:
            src_hash = hasher.sha256(src_path)

            # ========== Deduplication ===============
            if hash_db.exists(src_hash, db):
                result.skipped += 1
                existing = db[src_hash]["path"]
                _emit_skip(rel, existing)
                continue

            # ============== Copy ====================
            dst_path = dest_root / rel
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)

            # ============= Verify ===================
            dst_hash = hasher.sha256(dst_path)

            if src_hash == dst_hash:
                hash_db.register(src_hash, str(dst_path.relative_to(dest_root.parent)), db)
                result.copied += 1
                _emit_ok(rel)
            else:
                result.failed += 1
                result.failed_files.append(str(rel))
                _emit_fail(rel, "hash mismatch after copy")

        except Exception as e:
            result.failed += 1
            result.failed_files.append(str(rel))
            _emit_fail(rel, str(e))

    # Persist only if something new was actually copied
    if result.copied > 0:
        hash_db.save(db)

    return result


# Internal event emitters (simple print for now, easy to swap for callbacks) ──

def _emit_ok(rel: Path):
    print(f"  ✅  {rel}")

def _emit_skip(rel: Path, duplicate_of: str):
    print(f"  🔄️  {rel}  ← duplicate of '{duplicate_of}', skipped")

def _emit_fail(rel: Path, reason: str):
    print(f"  ⛔  {rel}  ← {reason}")
