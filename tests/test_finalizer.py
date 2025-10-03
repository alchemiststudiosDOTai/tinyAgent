"""
Tests for tinyagent.finalizer module.
"""

import threading
import time
from unittest.mock import patch

import pytest

from tinyagent import FinalAnswer, Finalizer, MultipleFinalAnswers


class TestFinalizer:
    """Test Finalizer class."""

    def test_initial_state(self):
        """Test initial state of Finalizer."""
        finalizer = Finalizer()
        assert not finalizer.is_set()
        assert finalizer.get() is None

    def test_set_and_get(self):
        """Test setting and getting final answer."""
        finalizer = Finalizer()
        finalizer.set("test answer")

        assert finalizer.is_set()
        final_answer = finalizer.get()
        assert isinstance(final_answer, FinalAnswer)
        assert final_answer.value == "test answer"
        assert final_answer.source == "normal"

    def test_set_with_source(self):
        """Test setting final answer with custom source."""
        finalizer = Finalizer()
        finalizer.set("test answer", source="final_attempt")

        final_answer = finalizer.get()
        assert final_answer.source == "final_attempt"

    def test_set_with_metadata(self):
        """Test setting final answer with metadata."""
        metadata = {"key": "value", "step": 5}
        finalizer = Finalizer()
        finalizer.set("test answer", metadata=metadata)

        final_answer = finalizer.get()
        assert final_answer.metadata == metadata

    def test_multiple_set_raises_exception(self):
        """Test that setting multiple final answers raises exception."""
        finalizer = Finalizer()
        finalizer.set("first answer")

        with pytest.raises(MultipleFinalAnswers) as exc_info:
            finalizer.set("second answer")

        assert "Final answer already set" in str(exc_info.value)
        assert exc_info.value.first_answer == "first answer"
        assert exc_info.value.attempted_answer == "second answer"

    def test_reset(self):
        """Test reset functionality."""
        finalizer = Finalizer()
        finalizer.set("test answer")
        assert finalizer.is_set()

        finalizer.reset()
        assert not finalizer.is_set()
        assert finalizer.get() is None

        # Should be able to set again after reset
        finalizer.set("new answer")
        assert finalizer.is_set()
        assert finalizer.get().value == "new answer"

    def test_thread_safety_basic(self):
        """Test basic thread safety."""
        finalizer = Finalizer()
        results = []
        errors = []

        def set_answer(value):
            try:
                finalizer.set(f"answer_{value}")
                results.append(f"success_{value}")
            except MultipleFinalAnswers:
                errors.append(f"error_{value}")

        # Start multiple threads trying to set answers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=set_answer, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Exactly one should succeed, others should fail
        assert len(results) == 1
        assert len(errors) == 4
        assert finalizer.is_set()

    def test_thread_safety_get_while_setting(self):
        """Test thread safety when getting while setting."""
        finalizer = Finalizer()
        get_results = []

        def getter():
            for _ in range(100):
                result = finalizer.get()
                get_results.append(result)
                time.sleep(0.001)

        def setter():
            time.sleep(0.05)  # Let getter run for a bit
            finalizer.set("test answer")

        # Start getter and setter threads
        getter_thread = threading.Thread(target=getter)
        setter_thread = threading.Thread(target=setter)

        getter_thread.start()
        setter_thread.start()

        getter_thread.join()
        setter_thread.join()

        # Should have some None results and some FinalAnswer results
        none_count = sum(1 for r in get_results if r is None)
        answer_count = sum(1 for r in get_results if r is not None)

        assert none_count > 0  # Some calls before setting
        assert answer_count > 0  # Some calls after setting
        assert none_count + answer_count == len(get_results)

    def test_timestamp_generation(self):
        """Test that timestamp is properly generated."""
        with patch("time.time", return_value=123456.789):
            finalizer = Finalizer()
            finalizer.set("test answer")

            final_answer = finalizer.get()
            assert final_answer.timestamp == 123456.789

    def test_different_value_types(self):
        """Test Finalizer with different value types."""
        test_cases = [
            "string answer",
            {"key": "value"},
            42,
            [1, 2, 3],
            None,
        ]

        for value in test_cases:
            finalizer = Finalizer()
            finalizer.set(value)

            final_answer = finalizer.get()
            assert final_answer.value == value
