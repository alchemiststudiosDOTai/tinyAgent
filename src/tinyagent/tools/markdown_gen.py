"""
Markdown Generator Tool for tinyAgent.

This tool enables the creation and updating of markdown files with structured content.
"""

import os
import json
from typing import Dict, List, Any, Optional, Union

# For typing and tool registration
try:
    from ..config import get_config_value
    from ..logging import get_logger
except ImportError:
    # For standalone testing
    def get_config_value(config, key, default=None):
        return default
    
    def get_logger(name):
        import logging
        return logging.getLogger(name)

# Set up logger
logger = get_logger(__name__)

def create_markdown(
    content: str, 
    filename: str, 
    overwrite: bool = False,
    directory: str = None
) -> Dict[str, Any]:
    """
    Create a markdown file with the provided content.
    
    Args:
        content: The markdown content to write to the file
        filename: Name of the markdown file to create (will add .md if not present)
        overwrite: Whether to overwrite an existing file
        directory: Optional directory to place the file (uses current directory if None)
        
    Returns:
        Dict with status information and file path
    """
    try:
        # Ensure filename has .md extension
        if not filename.lower().endswith('.md'):
            filename = f"{filename}.md"
        
        # Set the directory
        file_dir = os.getcwd() if directory is None else directory
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        # Create the full file path
        file_path = os.path.join(file_dir, filename)
        
        # Check if file exists and handle overwrite
        if os.path.exists(file_path) and not overwrite:
            return {
                "success": False,
                "file_path": file_path,
                "message": f"File '{filename}' already exists. Use overwrite=True to replace it."
            }
        
        # Write the content to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "file_path": file_path,
            "message": f"Successfully created markdown file: {filename}"
        }
    
    except Exception as e:
        logger.error(f"Error creating markdown file: {str(e)}")
        return {
            "success": False,
            "message": f"Error creating markdown file: {str(e)}"
        }

def update_markdown(
    filename: str,
    updates: Dict[str, str],
    create_if_missing: bool = True,
    directory: str = None
) -> Dict[str, Any]:
    """
    Update sections in an existing markdown file or create a new one.
    
    Args:
        filename: Name of the markdown file to update
        updates: Dictionary of section titles to content
        create_if_missing: Whether to create the file if it doesn't exist
        directory: Optional directory for the file (uses current directory if None)
        
    Returns:
        Dict with status information and file path
    """
    try:
        # Ensure filename has .md extension
        if not filename.lower().endswith('.md'):
            filename = f"{filename}.md"
        
        # Set the directory
        file_dir = os.getcwd() if directory is None else directory
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        # Create the full file path
        file_path = os.path.join(file_dir, filename)
        
        # If file doesn't exist, we can create it from scratch
        if not os.path.exists(file_path):
            if create_if_missing:
                # Create a new markdown file with the sections
                content = ""
                for section, text in updates.items():
                    # Determine heading level (default to h2)
                    heading_level = "##"
                    if section.startswith('#'):
                        # Count number of # and use that heading level
                        heading_count = 0
                        for char in section:
                            if char == '#':
                                heading_count += 1
                            else:
                                break
                        
                        if heading_count > 0:
                            heading_level = '#' * heading_count
                            section = section[heading_count:].lstrip()
                    
                    content += f"{heading_level} {section}\n\n{text}\n\n"
                
                return create_markdown(content, filename, True, directory)
            else:
                return {
                    "success": False,
                    "message": f"File '{filename}' does not exist and create_if_missing is False."
                }
        
        # Read the existing content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # For each section in updates, find and replace or append
        for section, new_text in updates.items():
            # Clean section name for matching
            clean_section = section
            if section.startswith('#'):
                clean_section = section.lstrip('#').lstrip()
            
            # Try to find the section in the content
            import re
            # Match any heading level for this section
            section_pattern = re.compile(r'^(#+)\s*' + re.escape(clean_section) + r'\s*$', re.MULTILINE)
            match = section_pattern.search(content)
            
            if match:
                # Found the section, now find where it ends
                heading_level = len(match.group(1))
                section_start = match.start()
                
                # Look for the next heading of same or higher level
                next_heading_pattern = re.compile(r'^(#{1,' + str(heading_level) + r'})\s+.+$', re.MULTILINE)
                next_match = next_heading_pattern.search(content, section_start + len(match.group(0)))
                
                if next_match:
                    section_end = next_match.start()
                    # Replace the section content
                    content = (
                        content[:section_start] + 
                        match.group(0) + '\n\n' + new_text + '\n\n' + 
                        content[section_end:]
                    )
                else:
                    # Section goes to the end of the file
                    content = (
                        content[:section_start] + 
                        match.group(0) + '\n\n' + new_text + '\n\n'
                    )
            else:
                # Section not found, append it
                heading_level = "##"  # default to h2
                if section.startswith('#'):
                    # Count number of # and use that heading level
                    heading_count = 0
                    for char in section:
                        if char == '#':
                            heading_count += 1
                        else:
                            break
                    
                    if heading_count > 0:
                        heading_level = '#' * heading_count
                        clean_section = section[heading_count:].lstrip()
                    
                content += f"\n\n{heading_level} {clean_section}\n\n{new_text}\n"
        
        # Write the updated content back to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "file_path": file_path,
            "message": f"Successfully updated markdown file: {filename}"
        }
    
    except Exception as e:
        logger.error(f"Error updating markdown file: {str(e)}")
        return {
            "success": False,
            "message": f"Error updating markdown file: {str(e)}"
        }

# Tool definition for registration
markdown_gen_tool = {
    "name": "markdown_gen",
    "description": "Create or update markdown files with structured content",
    "parameters": {
        "action": {
            "type": "string",
            "description": "Action to perform: 'create' or 'update'",
            "enum": ["create", "update"]
        },
        "filename": {
            "type": "string",
            "description": "Name of the markdown file (.md extension will be added if missing)"
        },
        "content": {
            "type": "string",
            "description": "Markdown content to write (for 'create' action)",
            "required": False
        },
        "updates": {
            "type": "object",
            "description": "Dictionary of section titles to content (for 'update' action)",
            "required": False
        },
        "overwrite": {
            "type": "boolean",
            "description": "Whether to overwrite existing file (for 'create' action)",
            "default": False
        },
        "create_if_missing": {
            "type": "boolean",
            "description": "Whether to create the file if it doesn't exist (for 'update' action)",
            "default": True
        },
        "directory": {
            "type": "string",
            "description": "Directory to place the file (uses current directory if not specified)",
            "required": False
        }
    },
    "function": lambda **kwargs: markdown_gen(**kwargs)
}

def markdown_gen(**kwargs) -> Dict[str, Any]:
    """
    Unified function for the markdown_gen tool.
    
    Args:
        action: 'create' or 'update'
        filename: Name of the markdown file
        content: Content for 'create' action
        updates: Section updates for 'update' action
        overwrite: Whether to overwrite for 'create'
        create_if_missing: Whether to create if missing for 'update'
        directory: Directory to place the file
    
    Returns:
        Dict with status information
    """
    action = kwargs.get('action')
    filename = kwargs.get('filename')
    
    if action == 'create':
        content = kwargs.get('content', '')
        overwrite = kwargs.get('overwrite', False)
        directory = kwargs.get('directory')
        return create_markdown(content, filename, overwrite, directory)
    
    elif action == 'update':
        updates = kwargs.get('updates', {})
        create_if_missing = kwargs.get('create_if_missing', True)
        directory = kwargs.get('directory')
        return update_markdown(filename, updates, create_if_missing, directory)
    
    else:
        return {
            "success": False,
            "message": f"Invalid action: {action}. Must be 'create' or 'update'."
        }

# This allows the tool to be imported directly
__all__ = ['markdown_gen_tool', 'markdown_gen', 'create_markdown', 'update_markdown']
