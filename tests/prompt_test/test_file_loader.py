"""Tests for prompt_loader.py module."""

import os
import tempfile

import pytest

from tinyagent.prompt_loader import get_prompt_fallback, load_prompt_from_file


class TestLoadPromptFromFile:
    """Test the load_prompt_from_file function."""

    def test_load_existing_file(self):
        """Test loading from an existing text file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test prompt content")
            temp_file = f.name

        try:
            result = load_prompt_from_file(temp_file)
            assert result == "Test prompt content"
        finally:
            os.unlink(temp_file)

    def test_load_empty_file(self):
        """Test loading from an empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("")
            temp_file = f.name

        try:
            result = load_prompt_from_file(temp_file)
            assert result == ""
        finally:
            os.unlink(temp_file)

    def test_load_markdown_file(self):
        """Test loading from a markdown file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Prompt\n\nThis is a test prompt.")
            temp_file = f.name

        try:
            result = load_prompt_from_file(temp_file)
            assert result == "# Test Prompt\n\nThis is a test prompt."
        finally:
            os.unlink(temp_file)

    def test_load_prompt_file(self):
        """Test loading from a .prompt file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".prompt", delete=False) as f:
            f.write("Custom prompt format")
            temp_file = f.name

        try:
            result = load_prompt_from_file(temp_file)
            assert result == "Custom prompt format"
        finally:
            os.unlink(temp_file)

    def test_file_not_found(self):
        """Test handling of missing file."""
        with pytest.raises(FileNotFoundError, match="Prompt file not found"):
            load_prompt_from_file("nonexistent_file.txt")

    def test_directory_instead_of_file(self):
        """Test handling of directory path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="Path is not a file"):
                load_prompt_from_file(temp_dir)

    def test_unsupported_file_extension(self):
        """Test handling of unsupported file types."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".exe", delete=False) as f:
            f.write("executable content")
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="File type '.exe' not supported"):
                load_prompt_from_file(temp_file)
        finally:
            os.unlink(temp_file)

    def test_permission_error(self):
        """Test handling of permission errors."""
        # Create a file and make it unreadable
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("restricted content")
            temp_file = f.name

        try:
            # Make file unreadable
            os.chmod(temp_file, 0o000)
            with pytest.raises(PermissionError, match="Permission denied"):
                load_prompt_from_file(temp_file)
        finally:
            os.chmod(temp_file, 0o644)  # Restore permissions
            os.unlink(temp_file)

    def test_encoding_error(self):
        """Test handling of encoding errors."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            # Write non-UTF-8 bytes
            f.write(b"\xff\xfe\x00\x41")  # UTF-16 BOM + 'A'
            temp_file = f.name

        try:
            with pytest.raises(ValueError, match="File encoding error"):
                load_prompt_from_file(temp_file)
        finally:
            os.unlink(temp_file)

    def test_empty_path(self):
        """Test handling of empty path."""
        result = load_prompt_from_file("")
        assert result is None

    def test_whitespace_path(self):
        """Test handling of whitespace-only path."""
        result = load_prompt_from_file("   ")
        assert result is None


class TestGetPromptFallback:
    """Test the get_prompt_fallback function."""

    def test_with_valid_file(self):
        """Test with a valid prompt file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Custom system prompt")
            temp_file = f.name

        try:
            result = get_prompt_fallback("default prompt", temp_file)
            assert result == "Custom system prompt"
        finally:
            os.unlink(temp_file)

    def test_with_missing_file(self):
        """Test with a missing file - should fallback."""
        result = get_prompt_fallback("default prompt", "nonexistent.txt")
        assert result == "default prompt"

    def test_with_none_path(self):
        """Test with None path - should use default."""
        result = get_prompt_fallback("default prompt", None)
        assert result == "default prompt"

    def test_with_empty_path(self):
        """Test with empty path - should use default."""
        result = get_prompt_fallback("default prompt", "")
        assert result == "default prompt"

    def test_with_permission_error(self):
        """Test with permission error - should fallback."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("restricted content")
            temp_file = f.name

        try:
            # Make file unreadable
            os.chmod(temp_file, 0o000)
            result = get_prompt_fallback("default prompt", temp_file)
            assert result == "default prompt"
        finally:
            os.chmod(temp_file, 0o644)  # Restore permissions
            os.unlink(temp_file)

    def test_with_encoding_error(self):
        """Test with encoding error - should fallback."""
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            # Write non-UTF-8 bytes
            f.write(b"\xff\xfe\x00\x41")  # UTF-16 BOM + 'A'
            temp_file = f.name

        try:
            result = get_prompt_fallback("default prompt", temp_file)
            assert result == "default prompt"
        finally:
            os.unlink(temp_file)
