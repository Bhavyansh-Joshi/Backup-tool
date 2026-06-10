"""
Drive Backup Tool
-----------------
- Auto-detects new drives
- Deduplication via SHA-256 (skips files already in backup by content)
- File integrity check (verify backup matches originals at any time)
- Format prompt only after verified copy
Cross-platform: Windows, macOS, Linux.
"""

from src.config import DESTINATION
from src.cli import show_header, show_menu, run_backup_loop, run_integrity_screen


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)

    show_header()
    choice = show_menu()

    if choice == "1":
        run_backup_loop()
    elif choice == "2":
        run_integrity_screen()
    elif choice == "3":
        pass
    else:
        print("  Invalid choice.")


if __name__ == "__main__":
    main()
