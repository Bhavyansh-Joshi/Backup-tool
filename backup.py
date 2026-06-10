"""
Drive Backup Tool
-----------------
- Auto-detects new drives
- Deduplication via SHA-256 (skips files already in backup by content)
- File integrity check (verify backup matches originals at any time)
- Format prompt only after verified copy
Cross-platform: Windows, macOS, Linux.
"""

import os
import sys
import time
import json
import shutil
import hashlib
import platform
import subprocess
from pathlib import Path
from datetime import datetime


# ── Config ──────

DESTINATION    = Path.home() / "BackupDrive"   # Where files are backed up to
POLL_INTERVAL  = 3                              # Seconds between drive checks
SKIP_EXTENSIONS = {".tmp", ".ds_store"}        # Files to always skip
HASH_DB_FILE   = DESTINATION / ".hash_db.json" # Tracks every backed-up file hash


# ── Hash Database ────
# Structure:
#   { "<sha256_hash>": { "path": "relative/path/in/backup", "ts": "timestamp" } }
#
# Key insight: keyed by HASH, not filename.
# Same content = same hash = skip copy regardless of name.

def load_hash_db() -> dict:
    """Load the hash database from disk. Returns empty dict if not found."""
    if HASH_DB_FILE.exists():
        try:
            with open(HASH_DB_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_hash_db(db: dict):
    """Persist the hash database to disk."""
    HASH_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HASH_DB_FILE, "w") as f:
        json.dump(db, f, indent=2)


def is_duplicate(file_hash: str, db: dict) -> bool:
    """Return True if this exact file content already exists in backup."""
    return file_hash in db


def register_file(file_hash: str, rel_path: str, db: dict):
    """Record a newly backed-up file in the hash database."""
    db[file_hash] = {
        "path": rel_path,
        "ts":   datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


# ── Utilities ─────

def sha256(path: Path, chunk_size: int = 65536) -> str:
    """Return SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def separator():
    print("─" * 60)


# ── Drive Detection ───

def get_mounted_drives() -> set:
    import psutil
    return {p.mountpoint for p in psutil.disk_partitions(all=False)}


def detect_new_drive(known_drives: set):
    current = get_mounted_drives()
    new = current - known_drives
    return new.pop() if new else None


# ── Copy with Dedup ────

def copy_and_verify(source_root: Path, dest_root: Path, db: dict):
    """
    Copy files from source_root → dest_root.
    - Skips files whose hash already exists in db (deduplication)
    - Verifies each copied file with SHA-256
    - Updates db with newly copied files

    Returns: (copied, skipped, failed, failed_list)
    """
    all_files = [
        p for p in source_root.rglob("*")
        if p.is_file() and p.suffix.lower() not in SKIP_EXTENSIONS
    ]

    total   = len(all_files)
    copied  = 0
    skipped = 0
    failed  = 0
    failed_list = []

    if total == 0:
        log("No files found on drive.")
        return 0, 0, 0, []

    log(f"Scanning {total} file(s)...")
    separator()

    for i, src_path in enumerate(all_files, 1):
        rel = src_path.relative_to(source_root)

        try:
            src_hash = sha256(src_path)

            # ── Deduplication check ──
            if is_duplicate(src_hash, db):
                existing = db[src_hash]["path"]
                skipped += 1
                print(f"  [{i}/{total}] ⟳  {rel}  ← duplicate of '{existing}', skipped")
                continue

            # ── Copy ──
            dst_path = dest_root / rel
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, dst_path)

            # ── Verify ──
            dst_hash = sha256(dst_path)

            if src_hash == dst_hash:
                register_file(src_hash, str(rel), db)
                copied += 1
                print(f"  [{i}/{total}] ✓  {rel}")
            else:
                failed += 1
                failed_list.append(str(rel))
                print(f"  [{i}/{total}] ✗  {rel}  ← HASH MISMATCH after copy")

        except Exception as e:
            failed += 1
            failed_list.append(str(rel))
            print(f"  [{i}/{total}] ✗  {rel}  ← ERROR: {e}")

    # Save updated db only if something new was copied
    if copied > 0:
        save_hash_db(db)

    return copied, skipped, failed, failed_list


# ── Integrity Check ─────

def run_integrity_check():
    """
    Walk every file in DESTINATION, recompute its hash,
    compare against the hash database. Report any corruption or missing entries.
    """
    db = load_hash_db()

    if not db:
        log("Hash database is empty — no integrity check possible.")
        log("Run a backup first to populate the database.")
        return

    separator()
    log("Running integrity check on backup...")
    separator()

    # Build reverse map: path → expected_hash
    path_to_hash = {v["path"]: k for k, v in db.items()}

    ok      = 0
    corrupt = 0
    missing = 0

    all_backup_files = [
        p for p in DESTINATION.rglob("*")
        if p.is_file() and p.name != ".hash_db.json"
    ]

    for backup_file in all_backup_files:
        rel = str(backup_file.relative_to(DESTINATION))

        if rel not in path_to_hash:
            print(f"  ⚠️   {rel}  ← not in database (untracked file)")
            missing += 1
            continue

        expected_hash = path_to_hash[rel]
        actual_hash   = sha256(backup_file)

        if actual_hash == expected_hash:
            ok += 1
            print(f"  ✓  {rel}")
        else:
            corrupt += 1
            print(f"  ✗  {rel}  ← CORRUPTED (hash mismatch)")

    separator()
    log(f"Integrity check complete:")
    print(f"     ✓  {ok} file(s) intact")
    if corrupt:
        print(f"     ✗  {corrupt} file(s) CORRUPTED")
    if missing:
        print(f"     ⚠️   {missing} file(s) untracked")

    if corrupt == 0 and missing == 0:
        log("✅  Backup is fully intact.")
    else:
        log("⚠️  Issues found. See above.")


# ── Format ───

def format_drive(mount_point: str) -> bool:
    system = platform.system()
    try:
        if system == "Windows":
            drive_letter = Path(mount_point).drive
            result = subprocess.run(
                ["format", drive_letter, "/FS:FAT32", "/Q", "/Y"],
                capture_output=True, text=True, timeout=120
            )
            return result.returncode == 0

        elif system == "Darwin":
            result = subprocess.run(
                ["diskutil", "eraseDisk", "FAT32", "BACKUP", mount_point],
                capture_output=True, text=True, timeout=120
            )
            return result.returncode == 0

        elif system == "Linux":
            result = subprocess.run(
                ["findmnt", "-n", "-o", "SOURCE", mount_point],
                capture_output=True, text=True
            )
            device = result.stdout.strip()
            if not device:
                log("Could not determine device for format.")
                return False
            subprocess.run(["umount", mount_point], capture_output=True)
            fmt = subprocess.run(
                ["mkfs.vfat", "-F", "32", device],
                capture_output=True, text=True, timeout=120
            )
            return fmt.returncode == 0

        else:
            log(f"Format not supported on {system}.")
            return False

    except subprocess.TimeoutExpired:
        log("Format timed out.")
        return False
    except Exception as e:
        log(f"Format error: {e}")
        return False


# ── User Prompts ────

def confirm(prompt: str) -> bool:
    while True:
        answer = input(f"{prompt} [yes/no]: ").strip().lower()
        if answer in ("yes", "y"):
            return True
        if answer in ("no", "n"):
            return False
        print("  Please type 'yes' or 'no'.")


def prompt_format(mount_point: str, source_root: Path):
    separator()
    print()
    print("  ✅  All files copied and verified successfully.")
    print(f"  Drive       : {mount_point}")
    print(f"  Backed up to: {DESTINATION}")
    print()
    print("  ⚠️   WARNING: Formatting will PERMANENTLY erase all data on the drive.")
    print()

    if confirm("  Do you want to format this drive?"):
        double_check = input(
            f"\n  Type the drive path exactly to confirm [{mount_point}]: "
        ).strip()
        if double_check == mount_point:
            log("Formatting drive...")
            if format_drive(mount_point):
                log("✅  Drive formatted successfully.")
            else:
                log("❌  Format failed. Drive was NOT modified.")
        else:
            log("Path didn't match. Format cancelled.")
    else:
        log("Format skipped. Drive untouched.")


# ── Main Menu ───

def print_menu():
    print()
    print("  What do you want to do?")
    print("  [1] Wait for a drive and back it up")
    print("  [2] Run integrity check on existing backup")
    print("  [3] Exit")
    print()


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)

    separator()
    print("  Drive Backup Tool  v2")
    print(f"  Destination : {DESTINATION}")
    print(f"  Platform    : {platform.system()}")
    separator()

    print_menu()
    choice = input("  Enter choice [1/2/3]: ").strip()

    if choice == "2":
        run_integrity_check()
        return

    if choice == "3":
        return

    # Backup mode
    print()
    log(f"Polling every {POLL_INTERVAL}s for new drives. Press Ctrl+C to exit.")
    print()

    db = load_hash_db()
    known_drives = get_mounted_drives()

    try:
        while True:
            new_mount = detect_new_drive(known_drives)

            if new_mount:
                known_drives = get_mounted_drives()
                source_root  = Path(new_mount)

                separator()
                log(f"New drive detected: {new_mount}")
                separator()

                if not confirm(f"  Back up files from '{new_mount}' to '{DESTINATION}'?"):
                    log("Backup cancelled.")
                    print()
                    continue

                ts_folder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                dest = DESTINATION / ts_folder
                dest.mkdir(parents=True, exist_ok=True)

                log(f"Starting backup → {dest}")
                separator()

                copied, skipped, fail, failed_list = copy_and_verify(source_root, dest, db)

                separator()
                log(f"Done — {copied} copied, {skipped} skipped (duplicates), {fail} failed.")

                if failed_list:
                    print("\n  Failed files:")
                    for f in failed_list:
                        print(f"    - {f}")
                    print()
                    log("⚠️  NOT prompting format — some files failed.")
                else:
                    prompt_format(new_mount, source_root)

                print()
                log("Ready for next drive.")
                print()

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print()
        log("Exiting.")


if __name__ == "__main__":
    main()