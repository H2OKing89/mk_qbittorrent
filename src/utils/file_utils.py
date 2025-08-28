"""
File utilities for folder information and file operations
"""
import os
from pathlib import Path
from typing import Dict, Any, List, Union, Tuple


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    i = 0
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    if i == 0:
        return f"{int(size)} {size_names[i]}"
    else:
        return f"{size:.1f} {size_names[i]} ({size_bytes:,} bytes)"


def get_folder_info(folder_path: Path) -> Dict[str, Any]:
    """
    Get comprehensive information about a folder
    
    Args:
        folder_path: Path to the folder
        
    Returns:
        Dictionary with folder information
    """
    if not folder_path.exists():
        return {
            "name": folder_path.name,
            "path": str(folder_path),
            "exists": False,
            "total_size": 0,
            "file_count": 0,
            "folder_count": 0,
            "error": "Folder does not exist"
        }
    
    if not folder_path.is_dir():
        # Handle single file
        try:
            file_size = folder_path.stat().st_size
            return {
                "name": folder_path.name,
                "path": str(folder_path),
                "exists": True,
                "total_size": file_size,
                "file_count": 1,
                "folder_count": 0,
                "is_file": True
            }
        except Exception as e:
            return {
                "name": folder_path.name,
                "path": str(folder_path),
                "exists": True,
                "total_size": 0,
                "file_count": 0,
                "folder_count": 0,
                "error": f"Cannot access file: {e}"
            }
    
    # Handle directory
    total_size = 0
    file_count = 0
    folder_count = 0
    errors = []
    
    try:
        for root, dirs, files in os.walk(folder_path):
            folder_count += len(dirs)
            
            for file in files:
                file_count += 1
                try:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
                except (OSError, IOError) as e:
                    errors.append(f"Cannot access {file}: {e}")
                    continue
    
    except Exception as e:
        return {
            "name": folder_path.name,
            "path": str(folder_path),
            "exists": True,
            "total_size": 0,
            "file_count": 0,
            "folder_count": 0,
            "error": f"Cannot scan folder: {e}"
        }
    
    info: Dict[str, Any] = {
        "name": folder_path.name,
        "path": str(folder_path),
        "exists": True,
        "total_size": total_size,
        "file_count": file_count,
        "folder_count": folder_count,
        "is_file": False
    }
    
    if errors:
        info["warnings"] = errors
    
    return info


def validate_folder_for_torrent(folder_path: Path) -> Tuple[bool, str]:
    """
    Validate if a folder is suitable for torrent creation
    
    Args:
        folder_path: Path to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    if not folder_path.exists():
        return False, "Path does not exist"
    
    if not (folder_path.is_file() or folder_path.is_dir()):
        return False, "Path is not a file or directory"
    
    # Check if we can read the path
    if not os.access(folder_path, os.R_OK):
        return False, "Cannot read the path (permission denied)"
    
    # Get basic info
    info = get_folder_info(folder_path)
    
    if info.get("error"):
        return False, str(info["error"])
    
    # Check if empty
    if info["file_count"] == 0:
        return False, "Folder is empty"
    
    # Check size limits (optional warnings)
    total_size = int(info.get("total_size", 0))
    file_count = int(info.get("file_count", 0))
    size_mb = total_size / (1024 * 1024)
    if size_mb > 10000:  # 10GB warning
        return True, f"Large folder ({format_file_size(total_size)}). Creation may take a while."
    
    return True, f"Valid folder with {file_count} files ({format_file_size(total_size)})"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file system usage
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove control characters
    filename = ''.join(c for c in filename if ord(c) >= 32)
    
    # Trim whitespace and dots
    filename = filename.strip(' .')
    
    # Ensure not empty
    if not filename:
        filename = "torrent"
    
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    
    return filename
