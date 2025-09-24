"""
Tests for tinyagent.exceptions module.
"""

from tinyagent.exceptions import InvalidFinalAnswer, MultipleFinalAnswers, StepLimitReached


class TestStepLimitReached:
    """Test StepLimitReached exception."""

    def test_basic_creation(self):
        """Test basic exception creation."""
        exc = StepLimitReached()
        assert str(exc) == "Exceeded max steps without an answer."
        assert exc.steps_taken is None
        assert exc.final_attempt_made is False
        assert exc.context == {}

    def test_creation_with_message(self):
        """Test exception creation with custom message."""
        exc = StepLimitReached("Custom error message")
        assert str(exc) == "Custom error message"

    def test_creation_with_context(self):
        """Test exception creation with context."""
        exc = StepLimitReached(
            "Test message",
            steps_taken=5,
            final_attempt_made=True,
            context={"key": "value"},
        )
        assert str(exc) == "Test message"
        assert exc.steps_taken == 5
        assert exc.final_attempt_made is True
        assert exc.context == {"key": "value"}

    def test_inheritance(self):
        """Test that StepLimitReached inherits from RuntimeError."""
        exc = StepLimitReached()
        assert isinstance(exc, RuntimeError)


class TestMultipleFinalAnswers:
    """Test MultipleFinalAnswers exception."""

    def test_basic_creation(self):
        """Test basic exception creation."""
        exc = MultipleFinalAnswers()
        assert str(exc) == "Multiple final answers attempted."
        assert exc.first_answer is None
        assert exc.attempted_answer is None

    def test_creation_with_message(self):
        """Test exception creation with custom message."""
        exc = MultipleFinalAnswers("Custom error message")
        assert str(exc) == "Custom error message"

    def test_creation_with_answers(self):
        """Test exception creation with answer context."""
        exc = MultipleFinalAnswers(
            "Test message",
            first_answer="first",
            attempted_answer="second",
        )
        assert str(exc) == "Test message"
        assert exc.first_answer == "first"
        assert exc.attempted_answer == "second"

    def test_inheritance(self):
        """Test that MultipleFinalAnswers inherits from RuntimeError."""
        exc = MultipleFinalAnswers()
        assert isinstance(exc, RuntimeError)


class TestInvalidFinalAnswer:
    """Test InvalidFinalAnswer exception."""

    def test_basic_creation(self):
        """Test basic exception creation."""
        exc = InvalidFinalAnswer()
        assert str(exc) == "Final answer failed validation."
        assert exc.raw_content is None
        assert exc.validation_error is None

    def test_creation_with_message(self):
        """Test exception creation with custom message."""
        exc = InvalidFinalAnswer("Custom error message")
        assert str(exc) == "Custom error message"

    def test_creation_with_context(self):
        """Test exception creation with context."""
        validation_error = ValueError("Invalid JSON")
        exc = InvalidFinalAnswer(
            "Test message",
            raw_content='{"invalid": json}',
            validation_error=validation_error,
        )
        assert str(exc) == "Test message"
        assert exc.raw_content == '{"invalid": json}'
        assert exc.validation_error == validation_error

    def test_inheritance(self):
        """Test that InvalidFinalAnswer inherits from ValueError."""
        exc = InvalidFinalAnswer()
        assert isinstance(exc, ValueError)


class TestExceptionIntegration:
    """Test exception integration scenarios."""

    def test_exception_chaining(self):
        """Test exception chaining scenarios."""
        original_error = ValueError("Original error")

        # Test InvalidFinalAnswer with chained exception
        exc = InvalidFinalAnswer(
            "Validation failed",
            validation_error=original_error,
        )
        assert exc.validation_error == original_error

    def test_exception_context_preservation(self):
        """Test that exception context is preserved."""
        context = {
            "step": 5,
            "model": "gpt-4",
            "temperature": 0.0,
            "messages": ["msg1", "msg2"],
        }

        exc = StepLimitReached(
            "Context test",
            steps_taken=5,
            final_attempt_made=True,
            context=context,
        )

        # Context should be preserved exactly
        assert exc.context == context
        assert exc.context["step"] == 5
        assert exc.context["model"] == "gpt-4"
