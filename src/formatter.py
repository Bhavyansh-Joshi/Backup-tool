"""
formatter.py
-----------------
OS-specific drive formatting. Nothing else.

"""

import platform
import subprocess
from pathlib import Path


class FormatError(Exception):
    # Raised when formatting fails.
    pass


def format_drive(mount_point: str) -> None:
    """
    Format the drive at mount_point as FAT32.

    Raises:
        FormatError: if formatting fails for any reason
    """
    system = platform.system()

    if system == "Windows":
        _format_windows(mount_point)
    elif system == "Darwin":
        _format_macos(mount_point)
    elif system == "Linux":
        _format_linux(mount_point)
    else:
        raise FormatError(f"Formatting not supported on {system}.")


# ================= Platform implementations ===================

def _format_windows(mount_point: str) -> None:
    drive_letter = Path(mount_point).drive  # e.g. "E:"
    result = subprocess.run(
        ["format", drive_letter, "/FS:FAT32", "/Q", "/Y"],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        raise FormatError(f"Windows format failed: {result.stderr.strip()}")


def _format_macos(mount_point: str) -> None:
    result = subprocess.run(
        ["diskutil", "eraseDisk", "FAT32", "BACKUP", mount_point],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode != 0:
        raise FormatError(f"macOS format failed: {result.stderr.strip()}")


def _format_linux(mount_point: str) -> None:
    # Find the block device behind this mount point
    result = subprocess.run(
        ["findmnt", "-n", "-o", "SOURCE", mount_point],
        capture_output=True, text=True
    )
    device = result.stdout.strip()

    if not device:
        raise FormatError("Could not determine block device for this mount point.")

    subprocess.run(["umount", mount_point], capture_output=True)

    fmt = subprocess.run(
        ["mkfs.vfat", "-F", "32", device],
        capture_output=True, text=True, timeout=120
    )
    if fmt.returncode != 0:
        raise FormatError(f"Linux mkfs.vfat failed: {fmt.stderr.strip()}")
