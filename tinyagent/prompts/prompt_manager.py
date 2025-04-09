"""
Prompt management system for tinyAgent.

This module provides a centralized system for managing and processing prompts,
including template loading, variable substitution, and validation.
"""

import os
import re
import string
from typing import Dict, Any, Optional
from pathlib import Path
import importlib.resources as pkg_resources

from ..logging import get_logger

# Set up logger
logger = get_logger(__name__)

class PromptManager:
    """
    Manages prompt templates and their processing.
    
    This class handles loading, caching, and processing of prompt templates,
    including variable substitution and validation.
    """
    
    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize the PromptManager.
        
        Args:
            project_root: Optional path to project root directory for development mode
        """
        # Get the directory containing this file
        self.prompts_dir = os.path.dirname(os.path.abspath(__file__))
        self._template_cache: Dict[str, str] = {}
        
    def _resolve_template_path(self, template_path: str) -> str:
        """
        Resolve a template path to its full filesystem path.
        
        Args:
            template_path: Relative or absolute path to template
            
        Returns:
            str: Full filesystem path to the template
            
        Raises:
            FileNotFoundError: If template doesn't exist
        """
        # If it's an absolute path and exists, use it
        if os.path.isabs(template_path) and os.path.exists(template_path):
            return template_path
            
        # Try relative to prompts directory
        full_path = os.path.join(self.prompts_dir, template_path)
        if os.path.exists(full_path):
            return full_path
            
        # Try package resources
        try:
            with pkg_resources.path('tinyagent.prompts', template_path) as path:
                if path.exists():
                    return str(path)
        except Exception:
            pass
            
        raise FileNotFoundError(f"Template '{template_path}' not found")
        
    def load_template(self, template_path: str) -> str:
        """
        Load a template from file or resolve a template name.
        
        Args:
            template_path: Path to template file or template name in format {{name}}
            
        Returns:
            str: The template content
            
        Raises:
            FileNotFoundError: If template file doesn't exist
            ValueError: If template name is invalid
        """
        # Check cache first
        if template_path in self._template_cache:
            return self._template_cache[template_path]
            
        try:
            # Check if the template path is in the format {{template_name}}
            template_match = re.match(r'{{(\w+)}}', template_path)
            
            if template_match:
                # Extract the template name and resolve to a file path
                template_name = template_match.group(1)
                
                # Try to find the template in different directories
                possible_paths = [
                    f'{template_name}.md',
                    os.path.join('system', f'{template_name}.md'),
                    os.path.join('tools', f'{template_name}.md'),
                    os.path.join('workflows', f'{template_name}.md')
                ]
                
                for path in possible_paths:
                    try:
                        resolved_path = self._resolve_template_path(path)
                        template_path = resolved_path
                        break
                    except FileNotFoundError:
                        continue
                else:
                    raise FileNotFoundError(f"Template '{template_name}' not found in any prompt directory")
            else:
                # If not a template name, resolve the path
                template_path = self._resolve_template_path(template_path)
            
            # Load the template file
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Cache the content
            self._template_cache[template_path] = content
            return content
            
        except Exception as e:
            logger.error(f"Error loading template {template_path}: {str(e)}")
            raise
            
    def process_template(self, template: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a template by replacing variables with their values.
        
        Args:
            template: The template string
            variables: Dictionary of variable names and their values
            
        Returns:
            str: The processed template with variables replaced
        """
        if not variables:
            return template
            
        # Create a template with Python's string.Template
        template_obj = string.Template(template.replace("{{", "${").replace("}}", "}"))
        
        # Replace variables using safe_substitute to avoid KeyError for missing variables
        return template_obj.safe_substitute(variables)
        
    def validate_template(self, template: str, required_vars: Optional[list[str]] = None) -> bool:
        """
        Validate a template's syntax and required variables.
        
        Args:
            template: The template string to validate
            required_vars: Optional list of required variable names
            
        Returns:
            bool: True if template is valid
            
        Raises:
            ValueError: If template is invalid or missing required variables
        """
        # Check for basic template syntax
        if not isinstance(template, str):
            raise ValueError("Template must be a string")
            
        # Extract variables from template
        variables = re.findall(r'\{\{(\w+)\}\}', template)
        
        # Check for required variables
        if required_vars:
            missing_vars = [var for var in required_vars if var not in variables]
            if missing_vars:
                raise ValueError(f"Template missing required variables: {', '.join(missing_vars)}")
                
        return True
        
    def get_template_path(self, template_name: str) -> str:
        """
        Get the full path for a template file.
        
        Args:
            template_name: Name of the template
            
        Returns:
            str: Full path to the template file
            
        Raises:
            FileNotFoundError: If template doesn't exist
        """
        # Try to find the template in different directories
        possible_paths = [
            f'{template_name}.md',
            f'system/{template_name}.md',
            f'tools/{template_name}.md',
            f'workflows/{template_name}.md'
        ]
        
        for path in possible_paths:
            try:
                return self._get_template_path(path)
            except FileNotFoundError:
                continue
                
        raise FileNotFoundError(f"Template '{template_name}' not found in any prompt directory") 