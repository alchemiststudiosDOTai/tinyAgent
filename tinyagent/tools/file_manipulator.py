"""
File manipulation tool for the tinyAgent framework.

This module provides a tool for performing CRUD operations on files in a safe and
configurable manner. It includes features for creating, reading, updating, and
deleting files, with proper error handling and security measures.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from ..logging import get_logger
from ..tool import Tool, ParamType
from ..exceptions import ToolError
from ..config import load_config

# Set up logger
logger = get_logger(__name__)

class FileManipulator:
    """Handles file operations with safety checks and configuration."""
    
    def __init__(self):
        self.config = load_config()
        self.file_ops_config = self.config.get('file_operations', {})
        self.allowed_extensions = self.file_ops_config.get('allowed_extensions', [])
        self.max_file_size = self.file_ops_config.get('max_file_size', 10485760)
        self.create_subdirs = self.file_ops_config.get('create_subdirs', True)
        self.allow_overwrite = self.file_ops_config.get('allow_overwrite', True)
    
    def _ensure_directory(self, path: Path) -> None:
        """Ensure the directory exists, creating parent directories if needed."""
        try:
            if self.create_subdirs:
                path.parent.mkdir(parents=True, exist_ok=True)
            else:
                if not path.parent.exists():
                    raise ToolError(f"Parent directory does not exist: {path.parent}")
        except Exception as e:
            logger.error(f"Failed to ensure directory: {str(e)}")
            raise ToolError(f"Failed to ensure directory: {str(e)}")
    
    def _validate_path(self, path: str) -> Path:
        """Validate and sanitize file path."""
        try:
            # Convert to Path object
            file_path = Path(path)
            
            # Handle relative vs absolute paths
            if file_path.is_absolute():
                if not self.file_ops_config.get('allow_absolute_paths', False):
                    raise ValueError(f"Absolute paths are not allowed: {path}")
                full_path = file_path
            else:
                # For relative paths, use the current directory as base
                full_path = Path.cwd() / file_path
            
            # Check file extension if restrictions are set
            if self.allowed_extensions and full_path.suffix and full_path.suffix not in self.allowed_extensions:
                allowed = ', '.join(self.allowed_extensions)
                raise ValueError(f"File extension '{full_path.suffix}' not allowed. Allowed: {allowed}")
            
            return full_path
        except Exception as e:
            logger.error(f"Path validation failed for '{path}': {str(e)}")
            raise ToolError(f"Invalid path '{path}': {str(e)}")
    
    def _check_file_size(self, content: Union[str, bytes]) -> None:
        """Check if content size exceeds limit."""
        try:
            size = len(content) if isinstance(content, bytes) else len(content.encode())
            if size > self.max_file_size:
                raise ToolError(f"Content size ({size} bytes) exceeds limit ({self.max_file_size} bytes)")
        except Exception as e:
            logger.error(f"File size check failed: {str(e)}")
            raise ToolError(f"File size check failed: {str(e)}")
    
    def _check_file_permissions(self, path: Path, operation: str) -> None:
        """Check if the operation is allowed on the file."""
        try:
            if operation in ["create", "update"]:
                if path.exists() and not self.allow_overwrite:
                    raise ToolError(f"File already exists and overwrite is not allowed: {path}")
            
            if operation in ["read", "update", "delete"]:
                if not path.exists():
                    raise FileNotFoundError(f"File not found: {path}")
                
                if operation in ["update", "delete"]:
                    if not os.access(path, os.W_OK):
                        raise PermissionError(f"No write permission for file: {path}")
                else:  # read
                    if not os.access(path, os.R_OK):
                        raise PermissionError(f"No read permission for file: {path}")
        except Exception as e:
            logger.error(f"Permission check failed: {str(e)}")
            raise ToolError(f"Permission check failed: {str(e)}")
    
    def create_file(self, path: str, content: str) -> Dict[str, Any]:
        """Create a new file with the given content."""
        try:
            full_path = self._validate_path(path)
            self._check_file_size(content)
            self._check_file_permissions(full_path, "create")
            self._ensure_directory(full_path)
            
            full_path.write_text(content)
            logger.info(f"Created file: {full_path}")
            return {"status": "success", "path": str(full_path)}
        except Exception as e:
            logger.error(f"File creation failed: {str(e)}")
            raise ToolError(f"Failed to create file: {str(e)}")
    
    def read_file(self, path: str) -> Dict[str, Any]:
        """Read content from a file."""
        try:
            full_path = self._validate_path(path)
            self._check_file_permissions(full_path, "read")
            
            content = full_path.read_text()
            logger.info(f"Read file: {full_path}")
            return {"status": "success", "content": content}
        except Exception as e:
            logger.error(f"File read failed: {str(e)}")
            raise ToolError(f"Failed to read file: {str(e)}")
    
    def update_file(self, path: str, content: str) -> Dict[str, Any]:
        """Update content of an existing file."""
        try:
            full_path = self._validate_path(path)
            self._check_file_size(content)
            self._check_file_permissions(full_path, "update")
            
            full_path.write_text(content)
            logger.info(f"Updated file: {full_path}")
            return {"status": "success", "path": str(full_path)}
        except Exception as e:
            logger.error(f"File update failed: {str(e)}")
            raise ToolError(f"Failed to update file: {str(e)}")
    
    def delete_file(self, path: str) -> Dict[str, Any]:
        """Delete a file."""
        try:
            full_path = self._validate_path(path)
            self._check_file_permissions(full_path, "delete")
            
            full_path.unlink()
            logger.info(f"Deleted file: {full_path}")
            return {"status": "success", "path": str(full_path)}
        except Exception as e:
            logger.error(f"File deletion failed: {str(e)}")
            raise ToolError(f"Failed to delete file: {str(e)}")
    
    def list_directory(self, path: Optional[str] = None) -> Dict[str, Any]:
        """List contents of a directory."""
        try:
            target_path = self._validate_path(path) if path else Path.cwd()
            
            if not target_path.exists():
                raise FileNotFoundError(f"Directory not found: {target_path}")
            
            if not target_path.is_dir():
                raise NotADirectoryError(f"Not a directory: {target_path}")
            
            if not os.access(target_path, os.R_OK):
                raise PermissionError(f"No read permission for directory: {target_path}")
            
            items = []
            try:
                for item in target_path.iterdir():
                    try:
                        items.append({
                            "name": item.name,
                            "type": "directory" if item.is_dir() else "file",
                            "size": item.stat().st_size if item.is_file() else None,
                            "permissions": oct(item.stat().st_mode)[-3:] if item.exists() else None
                        })
                    except Exception as e:
                        logger.warning(f"Failed to get info for {item}: {str(e)}")
                        items.append({
                            "name": item.name,
                            "type": "unknown",
                            "error": str(e)
                        })
            except Exception as e:
                logger.error(f"Failed to iterate directory {target_path}: {str(e)}")
                raise ToolError(f"Failed to list directory contents: {str(e)}")
            
            logger.info(f"Listed directory: {target_path}")
            return {"status": "success", "items": items}
        except Exception as e:
            logger.error(f"Directory listing failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "path": str(path) if path else str(Path.cwd()),
                "operation": "list"
            }

# Create the tool instance
file_manipulator = FileManipulator()

def handle_file_operation(operation: str, path: str, content: str = None) -> Dict[str, Any]:
    """Handle file operations with safety checks."""
    try:
        operations = {
            "create": file_manipulator.create_file,
            "read": file_manipulator.read_file,
            "update": file_manipulator.update_file,
            "delete": file_manipulator.delete_file,
            "list": file_manipulator.list_directory
        }
        
        if operation not in operations:
            raise ValueError(f"Unknown operation: '{operation}'. Supported operations: {', '.join(operations.keys())}")
        
        func = operations[operation]
        if operation in ["create", "update"]:
            if content is None:
                raise ValueError(f"Content is required for '{operation}' operation")
            return func(path, content)
        elif operation == "list":
            return func(path)
        else:
            return func(path)
    except Exception as e:
        logger.error(f"File operation '{operation}' failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "operation": operation,
            "path": path
        }

# Create the tool instance
file_manipulator_tool = Tool(
    name="file_manipulator",
    description="""
    Perform CRUD operations on files in a safe and configurable manner.
    
    Features:
    - Create new files with content
    - Read file contents
    - Update existing files
    - Delete files
    - List directory contents
    
    Configuration options:
    - allowed_extensions: List of allowed file extensions
    - max_file_size: Maximum file size in bytes
    - create_subdirs: Whether to create parent directories
    - allow_overwrite: Whether to allow overwriting existing files
    - allow_absolute_paths: Whether to allow absolute paths
    
    All operations include safety checks and proper error handling.
    """,
    parameters={
        "operation": ParamType.STRING,
        "path": ParamType.STRING,
        "content": ParamType.STRING
    },
    func=handle_file_operation
)

def get_tool() -> Tool:
    """
    Return the file_manipulator tool instance for tinyAgent integration.
    
    Returns:
        Tool: The file_manipulator tool object
    """
    return file_manipulator_tool 