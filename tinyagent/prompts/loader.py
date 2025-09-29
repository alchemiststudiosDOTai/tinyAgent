"""
tinyagent.prompt_loader
Simple utility for loading prompts from text files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

__all__ = ["load_prompt_from_file"]


def load_prompt_from_file(file_path: str) -> Optional[str]:
    """
    Load a prompt from a text file.

    Parameters
    ----------
    file_path
        Path to the text file containing the prompt

    Returns
    -------
    Optional[str]
        The prompt content as a string, or None if loading fails

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist
    PermissionError
        If the file cannot be read due to permissions
    ValueError
        If the file cannot be decoded as text or has other issues
    """
    if not file_path or not file_path.strip():
        return None

    # Convert to Path object for better handling
    path = Path(file_path)

    # Check if file exists
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {file_path}")

    # Check if it's a file (not directory)
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    # Check file extension (basic validation for text files)
    if path.suffix and path.suffix.lower() not in [".txt", ".md", ".prompt", ".xml"]:
        raise ValueError(
            f"File type '{path.suffix}' not supported. Use .txt, .md, .prompt, or .xml files"
        )

    try:
        # Read the file content
        content = path.read_text(encoding="utf-8").strip()

        # Return empty string for empty files (None is for loading failures)
        if not content:
            return ""

        return content

    except PermissionError:
        raise PermissionError(f"Permission denied reading file: {file_path}")
    except UnicodeDecodeError:
        raise ValueError(f"File encoding error for {file_path}")


def get_prompt_fallback(system_prompt: str, file_path: str | None = None) -> str:
    """
    Get prompt from file or fall back to system prompt.

    Parameters
    ----------
    system_prompt
        The default system prompt to use as fallback
    file_path
        Optional path to the prompt file

    Returns
    -------
    str
        The prompt content from file or the system prompt
    """
    if not file_path:
        return system_prompt

    try:
        prompt_content = load_prompt_from_file(file_path)
        if prompt_content is not None:
            # If the loaded prompt is empty, use the system prompt
            if not prompt_content.strip():
                return system_prompt
            return prompt_content
    except (FileNotFoundError, PermissionError, ValueError):
        # Log the error but continue with fallback
        import logging

        logging.warning(f"Failed to load prompt from {file_path}, using system prompt")

    return system_prompt
