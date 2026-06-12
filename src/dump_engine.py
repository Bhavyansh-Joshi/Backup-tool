"""
dump_engine.py
--------------------
Core dump logic:
  1. Scan source for files
  2. Hash each file
  3. Skip if hash already in database (deduplication)
  4. Copy to destination
  5. Verify hash after copy
  6. Register new file in database
"""

import shutil
import logging
from pathlib import Path
from dataclasses import dataclass, field

from src import hasher, dump_db
from src.config import SKIP_EXTENSIONS

logger = logging.getLogger("Backup")

@dataclass
class DumpResult:
    # Structured result for dump operation
    total:          int = 0
    transferred:    int = 0
    skipped:        int = 0
    failed:         int = 0
    safe_to_delete: list[str] = field(default_factory=list)
    failed_files:   list[str] = field(default_factory=list)

    @property
    def all_succeeded(self) -> bool:
        return self.failed == 0 and self.total > 0


def transfer(source_root: Path, dest_root: Path, sec_root: Path, db:dict) -> DumpResult:
    
    all_files = [
        p for p in source_root.rglob("*")
        if p.is_file() and p.suffix.lower() not in SKIP_EXTENSIONS
    ]

    result = DumpResult(total=len(all_files))

    if result.total == 0:
        return result

    for src_path in all_files:
        rel = src_path.relative_to(source_root)

        try:
            src_hash = hasher.sha256(src_path)

            # =============Deduplication=================
            if dump_db.exists(src_hash, db):
                result.skipped += 1
                existing = db[src_hash]["path"]
                _emit_skip(rel, existing)
                continue

            # ===============Dump========================
            dst_path = dest_root / rel
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)

            # =================Verify====================
            dst_hash = hasher.sha256(dst_path)

            if src_hash == dst_hash:

                # ===========Backup Dump=====================
                sec_path = sec_root / rel
                sec_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, sec_path)

                # =================Verify Backup=============
                sec_hash = hasher.sha256(sec_path)

                if src_hash == sec_hash:
                    result.transferred += 1
                    result.safe_to_delete.append(str(rel))
                    dump_db.register(src_hash, str(dst_path.relative_to(dest_root.parent)), db)
                    _emit_ok(rel)
                else:
                    dst_path.unlink()  # ← delete the primary copy
                    result.failed += 1
                    result.failed_files.append(str(rel))
                    _emit_fail(rel, "secondary hash mismatch - primary copy removed")

            else:
                result.failed += 1
                result.failed_files.append(str(rel))
                _emit_fail(rel, "hash mismatch after copy")

           
        
        except Exception as e:
            result.failed += 1
            result.failed_files.append(str(rel))
            _emit_fail(rel, str(e))

    # Persist only if something new was actually copied
    if result.transferred > 0:
        dump_db.save(db)

    return result


def delete_originals(source_root: Path, safe_to_delete: list[str]) -> None:

    for rel in safe_to_delete:
        file_path = source_root / Path(rel)
        try:
            file_path.unlink()
            logger.info(f"  [DELETED] {rel}")
        except Exception as e:
            logger.error(f"  [DELETE FAILED] {rel} <- {e}")


def cleanup_empty_folders(source_root: Path) -> None:
    #Remove empty folders left behind after file deletion.
    for folder in sorted(source_root.rglob("*"), reverse=True):
        if folder.is_dir() and not any(folder.iterdir()):
            try:
                folder.rmdir()
                logger.info(f"  [REMOVED EMPTY FOLDER] {folder.relative_to(source_root)}")
            except Exception as e:
                logger.error(f"  [REMOVE FAILED] {folder.relative_to(source_root)} <- {e}")

def _emit_ok(rel: Path):
    logger.info(f"  [OK]  {rel}")

def _emit_skip(rel: Path, duplicate_of: str):
    logger.info(f"  [SKIPPED] {rel}  <- duplicate of '{duplicate_of}', skipped")

def _emit_fail(rel: Path, reason: str):
    logger.error(f"  [FAILED]  {rel}  <- {reason}")