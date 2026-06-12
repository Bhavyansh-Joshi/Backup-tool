"""
Drive Backup Tool
-----------------
- Backup mode: auto-detects drives, copies with SHA-256 verification
- Dump mode: transfers SD card to primary + secondary, deletes originals after verification
- Deduplication via content hash
- File integrity check
- Structured logging

Cross-platform: Windows, macOS, Linux.
"""

from src.config import DESTINATION, DUMP_PRIMARY, DUMP_SECONDARY
from src.cli import show_header, show_menu, run_backup_loop, dump_engine_loop, run_integrity_screen, run_cleanup_screen
from src.logger import setup_logger

def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    DUMP_PRIMARY.mkdir(parents=True, exist_ok=True)
    DUMP_SECONDARY.mkdir(parents=True, exist_ok=True)

    setup_logger()
    show_header()
    choice = show_menu()

    if choice == "1":
        run_backup_loop()
    elif choice == "2":
        run_integrity_screen()
    elif choice == "3":
        dump_engine_loop()
    elif choice == "4":
        run_cleanup_screen()
    elif choice == "5":
        pass
    else:
        print("  Invalid choice.")


if __name__ == "__main__":
    main()
