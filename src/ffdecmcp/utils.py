"""Utility functions for path conversion and validation."""

import os
import platform
import re
from pathlib import Path
from typing import Optional


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system() == "Windows"


def windows_to_wsl_path(windows_path: str) -> str:
    """
    Convert Windows path to WSL path.

    Examples:
        C:\\Users\\foo\\file.swf -> /mnt/c/Users/foo/file.swf
        D:\\Projects\\test.swf -> /mnt/d/Projects/test.swf

    Args:
        windows_path: Windows-style path

    Returns:
        WSL-style path
    """
    # Normalize path separators
    path = windows_path.replace("\\", "/")

    # Handle drive letter (e.g., C: -> /mnt/c)
    if re.match(r"^[A-Za-z]:", path):
        drive = path[0].lower()
        rest = path[2:]  # Skip drive letter and colon
        return f"/mnt/{drive}{rest}"

    return path


def normalize_path(path: str, for_wsl: bool = False) -> str:
    """
    Normalize path for FFDec execution.

    Args:
        path: Input path
        for_wsl: If True, convert Windows paths to WSL format

    Returns:
        Normalized path
    """
    # Resolve to absolute path
    abs_path = str(Path(path).resolve())

    # Convert to WSL format if needed
    if for_wsl and is_windows():
        return windows_to_wsl_path(abs_path)

    return abs_path


def validate_swf_path(path: str) -> tuple[bool, Optional[str]]:
    """
    Validate SWF file path.

    Args:
        path: Path to SWF file

    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is None
    """
    path_obj = Path(path)

    # Check if path exists
    if not path_obj.exists():
        return False, f"File does not exist: {path}"

    # Check if it's a file (not directory)
    if not path_obj.is_file():
        return False, f"Path is not a file: {path}"

    # Check if it's readable
    if not os.access(path, os.R_OK):
        return False, f"File is not readable: {path}"

    # Check file extension
    if path_obj.suffix.lower() != ".swf":
        return False, f"File is not a SWF file (expected .swf extension): {path}"

    # Check if file is not empty
    if path_obj.stat().st_size == 0:
        return False, f"SWF file is empty: {path}"

    return True, None


def validate_output_dir(path: str, create: bool = True) -> tuple[bool, Optional[str]]:
    """
    Validate output directory path.

    Args:
        path: Path to output directory
        create: If True, create directory if it doesn't exist

    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is None
    """
    path_obj = Path(path)

    # Check if path exists
    if path_obj.exists():
        # Check if it's a directory
        if not path_obj.is_dir():
            return False, f"Path exists but is not a directory: {path}"

        # Check if it's writable
        if not os.access(path, os.W_OK):
            return False, f"Directory is not writable: {path}"

    elif create:
        # Try to create directory
        try:
            path_obj.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return False, f"Failed to create directory: {e}"
    else:
        return False, f"Directory does not exist: {path}"

    return True, None


def safe_filename(filename: str) -> str:
    """
    Convert filename to safe version by removing/replacing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Safe filename
    """
    # Remove/replace characters that are invalid in filenames
    invalid_chars = r'[<>:"/\\|?*]'
    safe = re.sub(invalid_chars, "_", filename)

    # Remove leading/trailing spaces and dots
    safe = safe.strip(". ")

    # Ensure filename is not empty
    if not safe:
        safe = "unnamed"

    return safe


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def get_file_info(path: str) -> dict:
    """
    Get file information.

    Args:
        path: Path to file

    Returns:
        Dictionary with file information
    """
    path_obj = Path(path)

    if not path_obj.exists():
        return {"exists": False}

    stat = path_obj.stat()

    return {
        "exists": True,
        "path": str(path_obj.resolve()),
        "name": path_obj.name,
        "size": stat.st_size,
        "size_formatted": format_file_size(stat.st_size),
        "is_file": path_obj.is_file(),
        "is_dir": path_obj.is_dir(),
        "readable": os.access(path, os.R_OK),
        "writable": os.access(path, os.W_OK),
    }
