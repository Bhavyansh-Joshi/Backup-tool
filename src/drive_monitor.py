"""
drive_monitor.py
----------------
Drive detection only. Polls the OS for newly mounted drives.
No copy logic, no hashing, no UI — just detection.
"""

import psutil

def get_mounted_drives() -> set[str]:
    # return the set of all current mounted drive
    return {p.mountpoint for p in psutil.disk_partitions (all=False)}

def find_new_drive(known_drives: set[str]) -> set | None:
    # compare the current mount againt the known drive and return the mount point of newly connected drive
    current = get_mounted_drives()
    new = current - known_drives
    return new.pop() if new else None