"""FastMCP tool for listing file audit status"""

from typing import Optional
from .manager import FileStatusManager

# Create a global instance - can be configured later
manager = None


def get_manager():
    """Get or create the file status manager"""
    global manager
    if manager is None:
        # Look for project_meta.json in parent directories
        from pathlib import Path
        current = Path.cwd()
        
        # Search up to 5 levels up for project_meta.json
        for _ in range(5):
            if (current / "project_meta.json").exists():
                manager = FileStatusManager(str(current))
                break
            parent = current.parent
            if parent == current:  # Reached root
                break
            current = parent
        
        # If not found, use current directory
        if manager is None:
            manager = FileStatusManager()
    
    return manager


async def list_file_status(directory: Optional[str] = None) -> str:
    """
    List file audit status in a markdown table format.
    
    This tool shows which files have been audited and tracks their modification status.
    
    Args:
        directory: Optional directory path to filter files (relative to project root).
                  If not provided, lists all tracked files.
    
    Returns:
        Markdown table showing file paths, audit status, last audit time, and modification status.
    
    Example:
        >>> await list_file_status("tools/")
        | File | Status | Last Audited | Modified Since |
        |------|--------|--------------|----------------|
        | tools/file_status/tool.py | ✅ Audited | 2025-01-15 10:30 | No |
        | tools/audit/tool.py | ❌ Not Tracked | N/A | N/A |
        
        **Summary**: 1/2 files audited
    """
    try:
        mgr = get_manager()
        return mgr.list_file_status(directory)
    except Exception as e:
        return f"Error listing file status: {str(e)}"