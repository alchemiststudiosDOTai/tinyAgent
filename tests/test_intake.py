"""Tests for L1 Intake pipeline."""

from __future__ import annotations

from tinyagent.agent_types import ImageContent, TextContent
from tinyagent.intake import (
    DEFAULT_ENRICHERS,
    Intake,
    IntakeSignal,
    _capture,
    _normalize,
    enrich_input_type,
    enrich_token_estimate,
)

# -- Signal capture --


class TestCapture:
    """_capture normalizes diverse raw inputs into IntakeSignal."""

    def test_string_input(self) -> None:
        signal = _capture("hello world")
        assert len(signal.content) == 1
        assert signal.content[0].get("type") == "text"
        assert signal.content[0].get("text") == "hello world"
        assert signal.metadata == {}

    def test_content_blocks_input(self) -> None:
        blocks: list[TextContent | ImageContent] = [
            {"type": "text", "text": "hello"},
            {"type": "image", "url": "http://example.com/img.png"},
        ]
        signal = _capture(blocks)
        assert len(signal.content) == 2
        assert signal.content[0].get("type") == "text"
        assert signal.content[1].get("type") == "image"

    def test_content_blocks_are_copied(self) -> None:
        blocks: list[TextContent | ImageContent] = [{"type": "text", "text": "hi"}]
        signal = _capture(blocks)
        signal.content.append({"type": "text", "text": "extra"})
        assert len(blocks) == 1

    def test_empty_string(self) -> None:
        signal = _capture("")
        assert signal.content[0].get("text") == ""


# -- Normalization --


class TestNormalize:
    """_normalize converts IntakeSignal to IntakeResult with UserMessage."""

    def test_produces_user_message(self) -> None:
        signal = IntakeSignal(
            content=[{"type": "text", "text": "hello"}],
            metadata={"key": "value"},
        )
        result = _normalize(signal)
        assert result.message["role"] == "user"
        assert result.message["content"] == signal.content
        assert result.message.get("timestamp") is not None
        assert result.metadata == {"key": "value"}

    def test_metadata_is_copied(self) -> None:
        meta: dict[str, object] = {"a": 1}
        signal = IntakeSignal(content=[{"type": "text", "text": "hi"}], metadata=meta)
        result = _normalize(signal)
        result.metadata["b"] = 2
        assert "b" not in meta


# -- Built-in enrichers --


class TestEnrichTokenEstimate:
    """enrich_token_estimate adds a rough token count."""

    def test_estimates_tokens(self) -> None:
        text = "hello world this is a test"
        signal = IntakeSignal(content=[{"type": "text", "text": text}])
        result = enrich_token_estimate(signal)
        assert result.metadata["token_estimate"] == len(text) // 4

    def test_empty_text(self) -> None:
        signal = IntakeSignal(content=[{"type": "text", "text": ""}])
        result = enrich_token_estimate(signal)
        assert result.metadata["token_estimate"] == 0

    def test_ignores_image_blocks(self) -> None:
        signal = IntakeSignal(
            content=[
                {"type": "text", "text": "hi"},
                {"type": "image", "url": "http://x.com/img.png"},
            ]
        )
        result = enrich_token_estimate(signal)
        assert result.metadata["token_estimate"] == len("hi") // 4

    def test_multiple_text_blocks(self) -> None:
        signal = IntakeSignal(
            content=[
                {"type": "text", "text": "hello"},
                {"type": "text", "text": "world"},
            ]
        )
        result = enrich_token_estimate(signal)
        assert result.metadata["token_estimate"] == (len("hello") + len("world")) // 4


class TestEnrichInputType:
    """enrich_input_type classifies input modality."""

    def test_text_only(self) -> None:
        signal = IntakeSignal(content=[{"type": "text", "text": "hi"}])
        result = enrich_input_type(signal)
        assert result.metadata["input_type"] == "text"

    def test_image_only(self) -> None:
        signal = IntakeSignal(content=[{"type": "image", "url": "http://x.com/img.png"}])
        result = enrich_input_type(signal)
        assert result.metadata["input_type"] == "image"

    def test_multimodal(self) -> None:
        signal = IntakeSignal(
            content=[
                {"type": "text", "text": "describe this"},
                {"type": "image", "url": "http://x.com/img.png"},
            ]
        )
        result = enrich_input_type(signal)
        assert result.metadata["input_type"] == "multimodal"

    def test_empty_content(self) -> None:
        signal = IntakeSignal(content=[])
        result = enrich_input_type(signal)
        assert result.metadata["input_type"] == "text"


# -- Intake pipeline --


async def test_default_enrichers_applied() -> None:
    intake = Intake()
    result = await intake.process("hello world")
    assert "token_estimate" in result.metadata
    assert "input_type" in result.metadata
    assert result.metadata["input_type"] == "text"
    assert result.message["role"] == "user"


async def test_custom_enrichers_replace_defaults() -> None:
    def add_source(signal: IntakeSignal) -> IntakeSignal:
        signal.metadata["source"] = "test"
        return signal

    intake = Intake(enrichers=[add_source])
    result = await intake.process("hi")
    assert result.metadata["source"] == "test"
    assert "token_estimate" not in result.metadata


async def test_async_enricher() -> None:
    async def async_enrich(signal: IntakeSignal) -> IntakeSignal:
        signal.metadata["async"] = True
        return signal

    intake = Intake(enrichers=[async_enrich])
    result = await intake.process("hi")
    assert result.metadata["async"] is True


async def test_add_enricher_chaining() -> None:
    def e1(s: IntakeSignal) -> IntakeSignal:
        s.metadata["e1"] = True
        return s

    def e2(s: IntakeSignal) -> IntakeSignal:
        s.metadata["e2"] = True
        return s

    intake = Intake(enrichers=[]).add_enricher(e1).add_enricher(e2)
    result = await intake.process("test")
    assert result.metadata["e1"] is True
    assert result.metadata["e2"] is True


async def test_enricher_ordering() -> None:
    order: list[str] = []

    def first(s: IntakeSignal) -> IntakeSignal:
        order.append("first")
        return s

    def second(s: IntakeSignal) -> IntakeSignal:
        order.append("second")
        return s

    intake = Intake(enrichers=[first, second])
    await intake.process("test")
    assert order == ["first", "second"]


async def test_empty_enrichers() -> None:
    intake = Intake(enrichers=[])
    result = await intake.process("bare input")
    assert result.metadata == {}
    assert result.message["role"] == "user"


async def test_content_blocks_input() -> None:
    blocks: list[TextContent | ImageContent] = [
        {"type": "text", "text": "look at this"},
        {"type": "image", "url": "http://example.com/img.png"},
    ]
    intake = Intake()
    result = await intake.process(blocks)
    assert result.metadata["input_type"] == "multimodal"
    assert len(result.message["content"]) == 2


def test_enrichers_property_returns_copy() -> None:
    intake = Intake(enrichers=[])
    enrichers = intake.enrichers
    enrichers.append(enrich_token_estimate)
    assert len(intake.enrichers) == 0


async def test_enricher_can_modify_content() -> None:
    def prepend_tag(signal: IntakeSignal) -> IntakeSignal:
        prefix: TextContent = {"type": "text", "text": "[SYS] "}
        signal.content = [prefix, *signal.content]
        return signal

    intake = Intake(enrichers=[prepend_tag])
    result = await intake.process("user query")
    assert len(result.message["content"]) == 2
    assert result.message["content"][0].get("text") == "[SYS] "


async def test_process_sets_timestamp() -> None:
    intake = Intake(enrichers=[])
    result = await intake.process("test")
    assert isinstance(result.message.get("timestamp"), int)


def test_default_enrichers_list() -> None:
    assert len(DEFAULT_ENRICHERS) == 2
    assert enrich_token_estimate in DEFAULT_ENRICHERS
    assert enrich_input_type in DEFAULT_ENRICHERS
