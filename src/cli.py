"""
cli.py
------
All terminal UI: menus, prompts, status output.
No business logic here — only user interaction and
calling into the right module.
"""

import time
import platform
from pathlib import Path
from datetime import datetime

from src import copy_engine, integrity, hash_db, drive_monitor
from src.formatter import format_drive, FormatError
from src.config import DESTINATION, POLL_INTERVAL


#===============Output Header========================

def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def sep():
    print("-" * 60)

#===============Prompts==============================

def confirm(prompt: str) -> bool:
    # Ask yes/no. Returns True only on explicit yes.
    while True:
        answer = input(f"{prompt} [yes/no]: ").strip().lower()
        if answer in ("yes", "y"):
            return True
        if answer in ("no", "n"):
            return False
        print("  Type 'yes' or 'no'.")


def prompt_format(mount_point: str):
    # Double-confirmed format prompt.
    sep()
    print()
    print(" ✅ All files copied and verified.")
    print(f"  Drive       : {mount_point}")
    print(f"  Backed up to: {DESTINATION}")
    print()
    print(" ⚠️ WARNING: Formatting PERMANENTLY erases the drive.")
    print()

    if not confirm("  Format this drive?"):
        log("Format skipped. Drive untouched.")
        return

    typed = input(f"\n  Type the drive path to confirm [{mount_point}]: ").strip()
    if typed != mount_point:
        log("Path didn't match. Format cancelled.")
        return

    log("Formatting...")
    try:
        format_drive(mount_point)
        log("✅  Drive formatted.")
    except FormatError as e:
        log(f"❌  Format failed: {e}")

#===============Display==============================

def show_header():
    sep()
    print("====Backup Tool====")
    print(f" Destination : {DESTINATION}")
    print(f" Platform : {platform.system()}")
    sep()

def show_menu() -> str:
    print()
    print(" [1] Wait for a drive to backup.")
    print(" [2] Run integrity check on backup.")
    print(" [3] Exit.")
    print()
    return input(" Choice [1/2/3] : ").strip()

def run_integrity_screen():
    # Shows the result of integrity check
    sep()
    log("Running integrity check....")
    sep()

    result = integrity.check()

    if result is None:
        log("No data found in the backup")
        return
    
    sep()
    log("Integrity Check Successful: ")
    print(f"  ✅ {result.ok} files(s) intact!!!")

    if result.corrupted:
        print(f"  ⛔ {result.corrupted} file(s) CORRUPTED:")
        for f in result.corrupted_files:
            print(f"      -{f}")

    if result.untracked:
        print(f"  ⚠️ {result.untracked} untracked file(s)")

    if result.is_clean:
        log("✅  Backup is fully intact.")
    else:
        log("⚠️  Issues found. See above.")



def run_backup_loop():
    # Poll for drives and run backup when one appears.
    log(f"Polling every {POLL_INTERVAL}s. Press Ctrl+C to stop.")
    print()

    db = hash_db.load()
    known_drives = drive_monitor.get_mounted_drives()

    try:
        while True:
            new_mount = drive_monitor.find_new_drive(known_drives)

            if new_mount:
                known_drives = drive_monitor.get_mounted_drives()
                source_root  = Path(new_mount)

                sep()
                log(f"New drive detected: {new_mount}")
                sep()

                if not confirm(f"  Back up '{new_mount}' → '{DESTINATION}'?"):
                    log("Cancelled.")
                    print()
                    continue

                ts_folder = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                dest = DESTINATION / ts_folder
                dest.mkdir(parents=True, exist_ok=True)

                log(f"Starting backup → {dest}")
                sep()

                result = copy_engine.backup(source_root, dest, db)

                sep()
                log(
                    f"Done — {result.copied} copied, "
                    f"{result.skipped} skipped (duplicates), "
                    f"{result.failed} failed."
                )

                if result.failed_files:
                    print("\n  Failed:")
                    for f in result.failed_files:
                        print(f"    - {f}")
                    print()
                    log("⚠️  Not prompting format — failures detected.")
                else:
                    prompt_format(new_mount)

                print()
                log("Ready for next drive.")

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print()
        log("Stopped.")
