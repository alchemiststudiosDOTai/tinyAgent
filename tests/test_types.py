"""
Tests for tinyagent.types module.
"""

from unittest.mock import patch

import pytest

from tinyagent.types import FinalAnswer, RunResult


class TestFinalAnswer:
    """Test FinalAnswer data class."""

    def test_basic_creation(self):
        """Test basic FinalAnswer creation."""
        answer = FinalAnswer(value="test answer")
        assert answer.value == "test answer"
        assert answer.source == "normal"
        assert isinstance(answer.timestamp, float)
        assert answer.metadata == {}

    def test_creation_with_all_fields(self):
        """Test FinalAnswer creation with all fields."""
        metadata = {"key": "value"}
        answer = FinalAnswer(
            value="test answer",
            source="final_attempt",
            metadata=metadata,
        )
        assert answer.value == "test answer"
        assert answer.source == "final_attempt"
        assert answer.metadata == metadata

    def test_timestamp_auto_generation(self):
        """Test that timestamp is automatically generated."""
        with patch("time.time", return_value=123456.789):
            answer = FinalAnswer(value="test")
            assert answer.timestamp == 123456.789

    def test_immutable(self):
        """Test that FinalAnswer is immutable."""
        answer = FinalAnswer(value="test")
        with pytest.raises(AttributeError):
            answer.value = "new value"

    def test_different_value_types(self):
        """Test FinalAnswer with different value types."""
        # String
        answer1 = FinalAnswer(value="string answer")
        assert answer1.value == "string answer"
        
        # Dict
        answer2 = FinalAnswer(value={"key": "value"})
        assert answer2.value == {"key": "value"}
        
        # Number
        answer3 = FinalAnswer(value=42)
        assert answer3.value == 42
        
        # List
        answer4 = FinalAnswer(value=[1, 2, 3])
        assert answer4.value == [1, 2, 3]


class TestRunResult:
    """Test RunResult data class."""

    def test_basic_creation(self):
        """Test basic RunResult creation."""
        result = RunResult(output="test output")
        assert result.output == "test output"
        assert result.final_answer is None
        assert result.state == "completed"
        assert result.steps_taken == 0
        assert result.duration_seconds == 0.0
        assert result.error is None
        assert result.metadata == {}

    def test_creation_with_all_fields(self):
        """Test RunResult creation with all fields."""
        final_answer = FinalAnswer(value="answer")
        error = Exception("test error")
        metadata = {"key": "value"}
        
        result = RunResult(
            output="test output",
            final_answer=final_answer,
            state="error",
            steps_taken=5,
            duration_seconds=1.5,
            error=error,
            metadata=metadata,
        )
        
        assert result.output == "test output"
        assert result.final_answer == final_answer
        assert result.state == "error"
        assert result.steps_taken == 5
        assert result.duration_seconds == 1.5
        assert result.error == error
        assert result.metadata == metadata

    def test_immutable(self):
        """Test that RunResult is immutable."""
        result = RunResult(output="test")
        with pytest.raises(AttributeError):
            result.output = "new output"

    def test_valid_states(self):
        """Test that all valid states work."""
        states = ["completed", "step_limit_reached", "error"]
        for state in states:
            result = RunResult(output="test", state=state)
            assert result.state == state

    def test_with_final_answer(self):
        """Test RunResult with FinalAnswer."""
        final_answer = FinalAnswer(value="test answer", source="final_attempt")
        result = RunResult(
            output="test output",
            final_answer=final_answer,
            state="step_limit_reached",
        )
        
        assert result.final_answer == final_answer
        assert result.final_answer.value == "test answer"
        assert result.final_answer.source == "final_attempt"
