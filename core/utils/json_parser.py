"""
Robust JSON parsing utility for TinyAgent.

This module provides functions for parsing JSON responses from language models
with multiple fallback strategies to handle various response formats.
"""

import re
import json
from typing import Dict, Any, Optional, Union, List, Tuple

from ..logging import get_logger

# Set up logger
logger = get_logger(__name__)


def parse_json_with_strategies(content: str, expected_keys: Optional[List[str]] = None) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Parse JSON from a string with multiple fallback strategies.
    
    Args:
        content: String potentially containing JSON
        expected_keys: List of keys that should be in the parsed result
        
    Returns:
        Tuple of (parsed data or None, strategy description)
    """
    # Strategy 1: Try to parse entire content as JSON directly
    try:
        data = json.loads(content)
        if validate_parsed_data(data, expected_keys):
            return data, "direct_parse"
    except json.JSONDecodeError:
        logger.debug("Direct JSON parsing failed")
    
    # Strategy 2: Try to find JSON object using regex for {...}
    json_match = re.search(r'({[\s\S]*})', content)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if validate_parsed_data(data, expected_keys):
                return data, "regex_curly_braces"
        except json.JSONDecodeError:
            logger.debug("Regex curly braces JSON parsing failed")
    
    # Strategy 3: Try to find JSON object with stricter pattern including key format
    json_match = re.search(r'({[\s\S]*"[\w_]+"\s*:[\s\S]*})', content)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if validate_parsed_data(data, expected_keys):
                return data, "regex_strict_keys"
        except json.JSONDecodeError:
            logger.debug("Regex strict keys JSON parsing failed")
    
    # Strategy 4: Try removing markdown code block markers
    cleaned_content = re.sub(r'```(?:json)?\n([\s\S]*?)\n```', r'\1', content)
    try:
        data = json.loads(cleaned_content)
        if validate_parsed_data(data, expected_keys):
            return data, "markdown_cleanup"
    except json.JSONDecodeError:
        logger.debug("Markdown cleanup JSON parsing failed")
    
    # Strategy 5: Try to extract JSON line by line (for multi-line formatted JSON)
    json_content = ""
    in_json = False
    bracket_count = 0
    
    for line in content.split('\n'):
        stripped = line.strip()
        
        if stripped.startswith('{') and not in_json:
            in_json = True
            bracket_count = 1
            json_content = stripped
            continue
            
        if in_json:
            json_content += stripped
            
            # Count brackets to handle nested structures
            bracket_count += stripped.count('{') - stripped.count('}')
            
            if bracket_count <= 0:
                # We've closed all brackets, try to parse
                break
    
    if json_content:
        try:
            data = json.loads(json_content)
            if validate_parsed_data(data, expected_keys):
                return data, "line_by_line"
        except json.JSONDecodeError:
            logger.debug("Line by line JSON parsing failed")
    
    # Strategy 6: Try to fix common JSON errors
    fixed_content = fix_common_json_errors(content)
    try:
        data = json.loads(fixed_content)
        if validate_parsed_data(data, expected_keys):
            return data, "error_correction"
    except json.JSONDecodeError:
        logger.debug("Error correction JSON parsing failed")
    
    # All strategies failed
    logger.debug("All JSON parsing strategies failed")
    return None, "all_failed"


def robust_json_parse(content: str, expected_keys: Optional[List[str]] = None, 
                     verbose: bool = False) -> Optional[Dict[str, Any]]:
    """
    Public function to parse JSON with all available strategies.
    
    Args:
        content: String potentially containing JSON
        expected_keys: List of keys that should be in the parsed result
        verbose: Whether to log detailed parsing information
        
    Returns:
        Dict containing parsed JSON or None if parsing fails
    """
    if verbose:
        logger.info(f"Attempting to parse content: {content[:200]}...")
    
    result, strategy = parse_json_with_strategies(content, expected_keys)
    
    if result:
        if verbose:
            logger.info(f"Successfully parsed JSON using strategy: {strategy}")
        return result
    
    if verbose:
        logger.warning(f"Failed to parse JSON content with any strategy")
    return None


def validate_parsed_data(data: Any, expected_keys: Optional[List[str]] = None) -> bool:
    """
    Validate that parsed data matches expected structure.
    
    Args:
        data: Data to validate
        expected_keys: List of keys that should be in the data
        
    Returns:
        True if data is valid, False otherwise
    """
    if not isinstance(data, dict):
        return False
    
    if expected_keys:
        return all(key in data for key in expected_keys)
    
    return True


def fix_common_json_errors(text: str) -> str:
    """
    Fix common JSON errors in a string.
    
    Args:
        text: String with potential JSON errors
        
    Returns:
        String with errors fixed
    """
    # Replace single quotes with double quotes (but not inside quotes)
    # This is a simplified approach and may not handle all edge cases
    step1 = re.sub(r"'([^']*)'", r'"\1"', text)
    
    # Try to fix unquoted keys
    step2 = re.sub(r'(\s*)(\w+)(\s*):(\s*)', r'\1"\2"\3:\4', step1)
    
    # Remove trailing commas
    step3 = re.sub(r',(\s*[\]}])', r'\1', step2)
    
    return step3


def extract_json_debug_info(content: str) -> Dict[str, Any]:
    """
    Extract debug information for JSON parsing failures.
    
    Args:
        content: String that failed to parse as JSON
        
    Returns:
        Dictionary with debugging information
    """
    # Count brackets to check for mismatched pairs
    open_curly = content.count('{')
    close_curly = content.count('}')
    open_square = content.count('[')
    close_square = content.count(']')
    
    # Check for common JSON syntax characters
    has_colon = ':' in content
    has_comma = ',' in content
    has_quotes = '"' in content
    
    # Look for truncation patterns
    appears_truncated = content.endswith('...') or content.endswith('…')
    
    # Identify potential issues
    issues = []
    if open_curly != close_curly:
        issues.append(f"Mismatched curly braces: {open_curly} open, {close_curly} close")
    if open_square != close_square:
        issues.append(f"Mismatched square brackets: {open_square} open, {close_square} close")
    if not has_colon:
        issues.append("Missing colons (required for key-value pairs)")
    if not has_quotes:
        issues.append("Missing quotes (required for JSON strings)")
    if appears_truncated:
        issues.append("Content appears to be truncated")
    
    return {
        "structure": {
            "curly_braces": (open_curly, close_curly),
            "square_brackets": (open_square, close_square),
            "has_colon": has_colon,
            "has_comma": has_comma,
            "has_quotes": has_quotes,
            "appears_truncated": appears_truncated
        },
        "identified_issues": issues,
        "content_sample": content[:100] + ("..." if len(content) > 100 else "")
    }
