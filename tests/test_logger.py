"Tests for AgentLogger."

import io

from tinyagent.observability import AgentLogger


class TestAgentLogger:
    """Test AgentLogger output formatting."""

    def test_banner_output(self) -> None:
        """Banner should include dividers and title."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.banner("TEST BANNER")

        output = stream.getvalue()
        assert "COMMAND CENTER // TEST BANNER" in output
        assert "=" * 78 in output  # 80 chars total, so 78 = or - depending on implementation

    def test_verbose_false_suppresses_output(self) -> None:
        """When verbose=False, output should be suppressed."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=False, stream=stream)
        logger.banner("TEST")
        logger.tag("TAG", "message")
        logger.labeled("LABEL", "value")
        logger.final_answer("answer")
        logger.step_header(1, 10)
        logger.error("error message")

        assert stream.getvalue() == ""

    def test_verbose_true_produces_output(self) -> None:
        """When verbose=True, output should be produced."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.banner("TEST")

        assert "TEST" in stream.getvalue()

    def test_signal_respects_verbose(self) -> None:
        """Signal output should respect verbose flag."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=False, stream=stream)
        logger.signal("UNCERTAIN", "test message")

        assert stream.getvalue() == ""

        # Now with verbose=True
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.signal("UNCERTAIN", "test message")

        assert "[ UNCERTAIN  ]" in stream.getvalue()
        assert "test message" in stream.getvalue()

    def test_truncation_with_ellipsis(self) -> None:
        """Truncation should add ellipsis when content exceeds limit."""
        logger = AgentLogger(content_preview_len=10)
        result = logger.truncate("hello world again")
        assert result == "hello worl..."

    def test_truncation_preserves_short_text(self) -> None:
        """Short text should not be truncated."""
        logger = AgentLogger(content_preview_len=100)
        result = logger.truncate("short")
        assert result == "short"

    def test_step_header_format(self) -> None:
        """Step header should include step numbers and dividers."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.step_header(3, 10)

        output = stream.getvalue()
        assert "OPERATION 3/10" in output
        assert "STATUS :: ADVANCING" in output

    def test_tag_uppercase(self) -> None:
        """Tags should be uppercased and padded."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.tag("api", "test message")

        assert "[    API     ]" in stream.getvalue()

    def test_labeled_output(self) -> None:
        """Labeled output should show label and value."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.labeled("TASK", "do something")

        output = stream.getvalue()
        assert "[    TASK    ]" in output
        assert "do something" in output

    def test_messages_preview(self) -> None:
        """Messages preview should show last N messages."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        messages = [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "question"},
            {"role": "assistant", "content": "response"},
        ]
        logger.messages_preview(messages, last_n=2)

        output = stream.getvalue()
        assert "USER ::" in output
        assert "ASSISTANT ::" in output
        assert "SYSTEM ::" not in output  # Should only show last 2

    def test_final_answer_format(self) -> None:
        """Final answer should have prominent formatting."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.final_answer("42")

        output = stream.getvalue()
        assert "FINAL ANSWER" in output
        assert "PAYLOAD :: 42" in output

    def test_api_call_with_temperature(self) -> None:
        """API call should show model and temperature."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.api_call("gpt-4", temperature=0.7)

        output = stream.getvalue()
        assert "[    API     ]" in output
        assert "gpt-4" in output
        assert "temp=0.7" in output

    def test_api_call_without_temperature(self) -> None:
        """API call without temperature should work."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.api_call("gpt-4")

        output = stream.getvalue()
        assert "[    API     ]" in output
        assert "gpt-4" in output
        assert "temp=" not in output

    def test_tool_call_output(self) -> None:
        """Tool call should show name and arguments."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.tool_call("search", {"query": "test"})

        output = stream.getvalue()
        assert "TOOL CALL // search" in output
        assert "ARGS ::" in output
        assert "query" in output

    def test_tool_observation_normal(self) -> None:
        """Tool observation should show result."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.tool_observation("result data")

        output = stream.getvalue()
        assert "[OBSERVATION ]" in output
        assert "result data" in output

    def test_tool_observation_error(self) -> None:
        """Tool observation error should show ERROR tag."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.tool_observation("error message", is_error=True)

        output = stream.getvalue()
        assert "[   ERROR    ]" in output

    def test_tool_observation_truncated(self) -> None:
        """Tool observation should show truncation notice."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.tool_observation("short", truncated_from=1000)

        output = stream.getvalue()
        assert "[    NOTE    ]" in output
        assert "truncated" in output
        assert "1000" in output

    def test_execution_result_basic(self) -> None:
        """Execution result should show output, duration, and is_final."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.execution_result(
            output="hello",
            duration_ms=123.5,
            is_final=True,
        )

        output = stream.getvalue()
        assert "EXECUTION RESULT" in output
        assert "OUTPUT   :: hello" in output
        assert "DURATION :: 123.5ms" in output
        assert "FINAL    :: True" in output

    def test_execution_result_with_error(self) -> None:
        """Execution result should show error when present."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.execution_result(
            output="",
            duration_ms=50.0,
            is_final=False,
            error="NameError: x is not defined",
        )

        output = stream.getvalue()
        assert "ERROR    :: NameError: x is not defined" in output

    def test_execution_result_with_timeout(self) -> None:
        """Execution result should show TIMEOUT when present."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.execution_result(
            output="",
            duration_ms=5000.0,
            is_final=False,
            timeout=True,
        )

        output = stream.getvalue()
        assert "TIMEOUT  :: TRUE" in output

    def test_code_block_format(self) -> None:
        """Code block should show code with dividers."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.code_block("print('hello')")

        output = stream.getvalue()
        assert "EXTRACTED CODE" in output
        assert "1: print('hello')" in output

    def test_captured_method(self) -> None:
        """captured() should return all output when using StringIO."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger._writeln("test line")

        assert logger.captured() == "test line\n"

    def test_captured_returns_empty_for_non_stringio(self) -> None:
        """captured() should return empty string for non-StringIO streams."""
        import sys

        logger = AgentLogger(verbose=True, stream=sys.stdout)
        assert logger.captured() == ""

    def test_error_format(self) -> None:
        """Error should have [ALERT] prefix."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.error("something went wrong")

        assert "[   ALERT    ]" in stream.getvalue()
        assert "[!] something went wrong" in stream.getvalue()

    def test_scratchpad_format(self) -> None:
        """Scratchpad should have SCRATCHPAD panel."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.scratchpad("thinking about the problem")

        output = stream.getvalue()
        assert "SCRATCHPAD" in output
        assert "thinking about the problem" in output

    def test_final_attempt_header(self) -> None:
        """Final attempt header should show step limit message."""
        stream = io.StringIO()
        logger = AgentLogger(verbose=True, stream=stream)
        logger.final_attempt_header()

        output = stream.getvalue()
        assert "FINAL ATTEMPT" in output
        assert "Step limit reached" in output
