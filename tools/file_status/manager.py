"""File status management functionality"""

import json
import hashlib
import fnmatch
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime


class FileStatusManager:
    """Manages file audit status tracking"""
    
    def __init__(self, project_root: Optional[str] = None):
        """Initialize file status manager
        
        Args:
            project_root: Root directory of the project. If None, uses current directory
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.meta_file = self.project_root / "project_meta.json"
        self.auditignore_file = self.project_root / ".auditignore"
        self._ensure_meta_file()
        self._load_auditignore()
    
    def _ensure_meta_file(self):
        """Ensure project meta file exists with default structure"""
        if not self.meta_file.exists():
            default_meta = {
                "file_status": {}
            }
            self._save_meta(default_meta)
    
    def _load_meta(self) -> Dict[str, Any]:
        """Load project metadata from file"""
        try:
            with open(self.meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self._ensure_meta_file()
            with open(self.meta_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    def _save_meta(self, meta: Dict[str, Any]):
        """Save project metadata to file"""
        try:
            # Ensure directory exists
            self.meta_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first
            temp_file = self.meta_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)
            
            # Atomically replace the original file
            temp_file.replace(self.meta_file)
                
        except Exception as e:
            print(f"[ERROR] Failed to save metadata: {str(e)}")
            raise
    
    def _load_auditignore(self):
        """Load patterns from .auditignore file"""
        self.ignore_patterns = []
        if self.auditignore_file.exists():
            try:
                with open(self.auditignore_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith('#'):
                            self.ignore_patterns.append(line)
            except Exception:
                pass
    
    def _should_ignore(self, file_path: str) -> bool:
        """Check if a file should be ignored based on .auditignore patterns"""
        # Convert to relative path for pattern matching
        self._load_auditignore()
        try:
            rel_path = Path(file_path).relative_to(self.project_root).as_posix()
        except ValueError:
            rel_path = file_path
        
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
        return False
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read and update hash in chunks
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except FileNotFoundError:
            return ""
    
    def update_file_status(self, file_path: str, audited: bool = True) -> bool:
        """Update file audit status"""
        meta = self._load_meta()
        
        # Convert relative path to absolute and then back to relative for storage
        abs_path = Path(file_path).absolute()
        
        try:
            rel_path = abs_path.relative_to(self.project_root).as_posix()
        except ValueError:
            # File is outside project root, use absolute path
            rel_path = str(abs_path)
        
        if audited:
            # Calculate file hash
            file_hash = self._calculate_file_hash(str(abs_path))
            if not file_hash:
                return False  # File doesn't exist
            
            # Mark as audited with timestamp and hash
            meta["file_status"][rel_path] = {
                "audited": True,
                "audited_at": datetime.now().isoformat(),
                "file_hash": file_hash
            }
        else:
            # Remove audit status
            if rel_path in meta["file_status"]:
                del meta["file_status"][rel_path]
        
        self._save_meta(meta)
        return True
    
    def get_file_status(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file audit status with hash verification"""
        meta = self._load_meta()
        
        # Convert to relative path for lookup
        abs_path = Path(file_path).absolute()
        try:
            rel_path = abs_path.relative_to(self.project_root).as_posix()
        except ValueError:
            rel_path = str(abs_path)
        
        status = meta["file_status"].get(rel_path)
        if not status:
            return None
            
        # Check if file still exists and hash matches
        current_hash = self._calculate_file_hash(str(abs_path))
        if not current_hash:
            return None  # File doesn't exist
            
        # Create a copy of status to avoid modifying the original
        result = status.copy()
        
        # Check if file has been modified since audit
        stored_hash = status.get("file_hash")
        if stored_hash and current_hash != stored_hash:
            result["audited"] = False
            result["modified_after_audit"] = True
            result["current_hash"] = current_hash
            
        return result
    
    def list_file_status(self, directory: Optional[str] = None) -> str:
        """List files and their audit status as markdown table
        
        Args:
            directory: Optional directory to filter files (relative to project root)
            
        Returns:
            Markdown table with files and audit status
        """
        meta = self._load_meta()
        file_statuses = meta.get("file_status", {})
        
        # Get all files in directory
        if directory:
            search_path = self.project_root / directory
            if not search_path.exists():
                return f"Directory not found: {directory}"
            
            # Find all Python files in directory
            all_files = []
            for file_path in search_path.rglob("*.py"):
                if file_path.is_file() and file_path.name != "__init__.py":
                    try:
                        rel_path = file_path.relative_to(self.project_root).as_posix()
                        all_files.append(rel_path)
                    except ValueError:
                        # File outside project root
                        all_files.append(str(file_path))
        else:
            # If no directory specified, just list tracked files
            all_files = list(file_statuses.keys())
        
        if not all_files:
            return "No files found to track."
        
        # Build markdown table
        table_lines = [
            "| File | Status | Last Audited | Modified Since |",
            "|------|--------|--------------|----------------|"
        ]
        
        # Sort files for consistent output
        all_files.sort()
        
        for file_path in all_files:
            # Check if file should be ignored
            if self._should_ignore(file_path):
                table_lines.append(f"| {file_path} | 🚫 Ignored | N/A | N/A |")
                continue
            
            status = self.get_file_status(file_path) if file_path in file_statuses else None
            
            if status:
                audited = "✅ Audited" if status.get("audited") else "❌ Not Audited"
                last_audited = status.get("audited_at", "N/A")
                if last_audited != "N/A":
                    # Format date nicely
                    try:
                        dt = datetime.fromisoformat(last_audited)
                        last_audited = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass
                
                modified = "⚠️ Yes" if status.get("modified_after_audit") else "No"
                
                table_lines.append(f"| {file_path} | {audited} | {last_audited} | {modified} |")
            else:
                table_lines.append(f"| {file_path} | ❌ Not Tracked | N/A | N/A |")
        
        # Add summary
        ignored_files = sum(1 for f in all_files if self._should_ignore(f))
        tracked_files = [f for f in all_files if not self._should_ignore(f)]
        total_tracked = len(tracked_files)
        audited_files = sum(1 for f in tracked_files if f in file_statuses and 
                          file_statuses.get(f, {}).get("audited", False))
        
        summary = f"\n**Summary**: {audited_files}/{total_tracked} files audited"
        if ignored_files > 0:
            summary += f" ({ignored_files} files ignored)"
        
        return "\n".join(table_lines) + "\n" + summary