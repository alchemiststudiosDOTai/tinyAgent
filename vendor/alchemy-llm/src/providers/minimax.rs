use serde::Deserialize;
use serde_json::json;

use super::openai_completions::OpenAICompletionsOptions;
#[cfg(test)]
use super::shared::finish_current_block;
use super::shared::{
    apply_deferred_tool_calls, convert_messages, convert_tools, handle_reasoning_delta,
    handle_text_delta, initialize_output, map_stop_reason, prepare_openai_like_chunk,
    push_stream_error, run_openai_like_stream, AssistantThinkingMode, CurrentBlock,
    OpenAiLikeMessageOptions, OpenAiLikeRequest, OpenAiLikeStreamChunk, OpenAiLikeToolCallDelta,
    ReasoningDelta, SystemPromptRole,
};
use crate::types::{
    Api, AssistantMessage, AssistantMessageEventStream, Context, EventStreamSender,
    MinimaxCompletions, Model,
};
use crate::utils::{ThinkFragment, ThinkTagParser};

const STREAM_INCLUDE_USAGE_FIELD: &str = "include_usage";
const MAX_TOKENS_FIELD: &str = "max_tokens";
const REASONING_SPLIT_FIELD: &str = "reasoning_split";
const REASONING_DETAILS_SIGNATURE: &str = "reasoning_details";
const REASONING_CONTENT_SIGNATURE: &str = "reasoning_content";
const REASONING_SIGNATURE: &str = "reasoning";
const REASONING_TEXT_SIGNATURE: &str = "reasoning_text";
const THINK_TAG_SIGNATURE: &str = "think_tag";
const MINIMAX_MIN_TEMPERATURE: f64 = f64::MIN_POSITIVE;
const MINIMAX_MAX_TEMPERATURE: f64 = 1.0;

/// Stream completions from MiniMax chat/completions API.
pub fn stream_minimax_completions(
    model: &Model<MinimaxCompletions>,
    context: &Context,
    options: OpenAICompletionsOptions,
) -> AssistantMessageEventStream {
    let (stream, sender) = AssistantMessageEventStream::new();

    let model = model.clone();
    let context = context.clone();

    tokio::spawn(async move {
        run_stream(model, context, options, sender).await;
    });

    stream
}

async fn run_stream(
    model: Model<MinimaxCompletions>,
    context: Context,
    options: OpenAICompletionsOptions,
    mut sender: EventStreamSender,
) {
    let mut output = initialize_output(
        Api::MinimaxCompletions,
        model.provider.clone(),
        model.id.clone(),
    );

    if let Err(error) = run_stream_inner(&model, &context, &options, &mut output, &mut sender).await
    {
        push_stream_error(&mut output, &mut sender, error);
    }
}

async fn run_stream_inner(
    model: &Model<MinimaxCompletions>,
    context: &Context,
    options: &OpenAICompletionsOptions,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
) -> Result<(), crate::Error> {
    let params = build_params(model, context, options);
    let request = OpenAiLikeRequest {
        provider: &model.provider,
        base_url: &model.base_url,
        api_key: &options.api_key,
        model_headers: model.headers.as_ref(),
        request_headers: options.headers.as_ref(),
        params: &params,
    };

    let mut think_tag_parser = ThinkTagParser::new();

    run_openai_like_stream::<StreamChunk, _, _, _>(
        request,
        output,
        sender,
        &mut think_tag_parser,
        |chunk, parser, output, sender, current_block| {
            process_chunk(&chunk, output, sender, current_block, parser);
        },
        |parser, output, sender, current_block| {
            flush_think_tag_parser(parser, output, sender, current_block);
        },
    )
    .await
}

fn build_params(
    model: &Model<MinimaxCompletions>,
    context: &Context,
    options: &OpenAICompletionsOptions,
) -> serde_json::Value {
    let message_options = OpenAiLikeMessageOptions::openai_like(
        SystemPromptRole::System,
        false,
        AssistantThinkingMode::ThinkTags,
    );

    let mut params = json!({
        "model": model.id,
        "stream": true,
        "messages": convert_messages(model, context, &message_options),
    });

    let mut stream_options = serde_json::Map::new();
    stream_options.insert(STREAM_INCLUDE_USAGE_FIELD.to_string(), json!(true));
    params["stream_options"] = serde_json::Value::Object(stream_options);

    if model.reasoning {
        params[REASONING_SPLIT_FIELD] = json!(true);
    }

    if let Some(max_tokens) = options.max_tokens {
        params[MAX_TOKENS_FIELD] = json!(max_tokens);
    }

    if let Some(temperature) = options.temperature {
        params["temperature"] = json!(clamp_temperature(temperature));
    }

    if let Some(tools) = &context.tools {
        params["tools"] = convert_tools(tools);
    }

    if let Some(tool_choice) = &options.tool_choice {
        params["tool_choice"] = serde_json::to_value(tool_choice).unwrap_or(json!("auto"));
    }

    params
}

fn clamp_temperature(temperature: f64) -> f64 {
    temperature.clamp(MINIMAX_MIN_TEMPERATURE, MINIMAX_MAX_TEMPERATURE)
}

fn process_chunk(
    chunk: &StreamChunk,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
    think_tag_parser: &mut ThinkTagParser,
) {
    let Some(prelude) = prepare_openai_like_chunk(
        chunk,
        output,
        sender,
        current_block,
        map_stop_reason,
        delta_tool_calls,
    ) else {
        return;
    };

    let delta = prelude.delta;
    let explicit_reasoning = emit_explicit_reasoning(delta, output, sender, current_block);

    if let Some(content) = delta.content.as_deref() {
        if explicit_reasoning {
            handle_text_delta(content, output, sender, current_block);
        } else {
            process_content_with_fallback(content, think_tag_parser, output, sender, current_block);
        }
    }

    apply_deferred_tool_calls(prelude, output, sender, current_block);
}

fn delta_tool_calls(delta: &StreamDelta) -> Option<&[OpenAiLikeToolCallDelta]> {
    delta.tool_calls.as_deref()
}

fn emit_explicit_reasoning(
    delta: &StreamDelta,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
) -> bool {
    let mut emitted_reasoning = false;

    if let Some(details) = &delta.reasoning_details {
        for detail in details {
            if let Some(text) = detail.text.as_deref() {
                if text.is_empty() {
                    continue;
                }

                emitted_reasoning = true;
                handle_reasoning_delta(
                    ReasoningDelta {
                        text,
                        signature: REASONING_DETAILS_SIGNATURE,
                    },
                    output,
                    sender,
                    current_block,
                );
            }
        }
    }

    if emitted_reasoning {
        return true;
    }

    for (text, signature) in [
        (
            delta.reasoning_content.as_deref(),
            REASONING_CONTENT_SIGNATURE,
        ),
        (delta.reasoning.as_deref(), REASONING_SIGNATURE),
        (delta.reasoning_text.as_deref(), REASONING_TEXT_SIGNATURE),
    ] {
        if let Some(reasoning_text) = text {
            if reasoning_text.is_empty() {
                continue;
            }

            handle_reasoning_delta(
                ReasoningDelta {
                    text: reasoning_text,
                    signature,
                },
                output,
                sender,
                current_block,
            );
            return true;
        }
    }

    false
}

fn process_content_with_fallback(
    content: &str,
    think_tag_parser: &mut ThinkTagParser,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
) {
    for fragment in think_tag_parser.feed(content) {
        match fragment {
            ThinkFragment::Text(text) => {
                handle_text_delta(&text, output, sender, current_block);
            }
            ThinkFragment::Thinking(thinking) => {
                handle_reasoning_delta(
                    ReasoningDelta {
                        text: &thinking,
                        signature: THINK_TAG_SIGNATURE,
                    },
                    output,
                    sender,
                    current_block,
                );
            }
        }
    }
}

fn flush_think_tag_parser(
    think_tag_parser: &mut ThinkTagParser,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
) {
    for fragment in think_tag_parser.flush() {
        match fragment {
            ThinkFragment::Text(text) => {
                handle_text_delta(&text, output, sender, current_block);
            }
            ThinkFragment::Thinking(thinking) => {
                handle_reasoning_delta(
                    ReasoningDelta {
                        text: &thinking,
                        signature: THINK_TAG_SIGNATURE,
                    },
                    output,
                    sender,
                    current_block,
                );
            }
        }
    }
}

type StreamChunk = OpenAiLikeStreamChunk<StreamDelta>;

#[derive(Debug, Deserialize)]
struct StreamDelta {
    content: Option<String>,
    reasoning_details: Option<Vec<ReasoningDetail>>,
    reasoning_content: Option<String>,
    reasoning: Option<String>,
    reasoning_text: Option<String>,
    tool_calls: Option<Vec<OpenAiLikeToolCallDelta>>,
}

#[derive(Debug, Deserialize)]
struct ReasoningDetail {
    #[serde(rename = "type")]
    _detail_type: Option<String>,
    _id: Option<String>,
    _format: Option<String>,
    _index: Option<u32>,
    text: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::test_helpers::{
        assert_final_message_shape, build_final_message_shape_chunks, ExpectedFinalMessageShape,
    };
    use crate::types::{
        AssistantMessageEvent, Content, InputType, KnownProvider, Message, ModelCost, Provider,
        StopReason, Usage, UserContent, UserMessage,
    };
    use futures::executor::block_on;
    use futures::StreamExt;

    const TEST_BASE_URL: &str = "https://api.minimax.io/v1/chat/completions";

    fn make_model(reasoning: bool) -> Model<MinimaxCompletions> {
        Model {
            id: "MiniMax-M2.5".to_string(),
            name: "MiniMax M2.5".to_string(),
            api: MinimaxCompletions,
            provider: Provider::Known(KnownProvider::Minimax),
            base_url: TEST_BASE_URL.to_string(),
            reasoning,
            input: vec![InputType::Text],
            cost: ModelCost {
                input: 0.0,
                output: 0.0,
                cache_read: 0.0,
                cache_write: 0.0,
            },
            context_window: 204_800,
            max_tokens: 16_384,
            headers: None,
            compat: None,
        }
    }

    fn make_context() -> Context {
        Context {
            system_prompt: Some("You are concise".to_string()),
            messages: vec![crate::types::Message::User(UserMessage {
                content: UserContent::Text("Hello".to_string()),
                timestamp: 0,
            })],
            tools: None,
        }
    }

    fn make_output_message() -> AssistantMessage {
        AssistantMessage {
            content: vec![],
            api: Api::MinimaxCompletions,
            provider: Provider::Known(KnownProvider::Minimax),
            model: "MiniMax-M2.5".to_string(),
            usage: Usage::default(),
            stop_reason: StopReason::Stop,
            error_message: None,
            timestamp: 0,
        }
    }

    fn process_chunks_for_test(
        chunks: Vec<StreamChunk>,
    ) -> (Vec<AssistantMessageEvent>, AssistantMessage) {
        let (mut stream, mut sender) = AssistantMessageEventStream::new();
        let mut output = make_output_message();
        let mut current_block = None;
        let mut parser = ThinkTagParser::new();

        for chunk in chunks {
            process_chunk(
                &chunk,
                &mut output,
                &mut sender,
                &mut current_block,
                &mut parser,
            );
        }

        flush_think_tag_parser(&mut parser, &mut output, &mut sender, &mut current_block);
        finish_current_block(&mut current_block, &mut output, &mut sender);

        drop(sender);

        let events = block_on(async move { stream.by_ref().collect::<Vec<_>>().await });
        (events, output)
    }

    fn tool_call_start_chunk(call_id: &str) -> StreamChunk {
        serde_json::from_value(serde_json::json!({
            "choices": [{
                "delta": {
                    "tool_calls": [{
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": "multiply",
                            "arguments": "{\"a\": 15, \"b\": "
                        },
                        "index": 0
                    }]
                }
            }]
        }))
        .expect("valid first tool-call chunk")
    }

    fn tool_call_continuation_with_content_chunk(content: &str) -> StreamChunk {
        serde_json::from_value(serde_json::json!({
            "choices": [{
                "finish_reason": "tool_calls",
                "delta": {
                    "content": content,
                    "tool_calls": [{
                        "type": "function",
                        "function": {
                            "arguments": "3}"
                        },
                        "index": 0
                    }]
                }
            }]
        }))
        .expect("valid interleaved continuation chunk")
    }

    fn tool_call_continuation_with_reasoning_chunk(reasoning_text: &str) -> StreamChunk {
        serde_json::from_value(serde_json::json!({
            "choices": [{
                "finish_reason": "tool_calls",
                "delta": {
                    "reasoning_details": [{
                        "type": "reasoning",
                        "id": "r-1",
                        "format": "text",
                        "index": 0,
                        "text": reasoning_text
                    }],
                    "tool_calls": [{
                        "type": "function",
                        "function": {
                            "arguments": "3}"
                        },
                        "index": 0
                    }]
                }
            }]
        }))
        .expect("valid interleaved reasoning continuation chunk")
    }

    fn assert_multiply_tool_call(content: &Content, expected_call_id: &str) {
        match content {
            Content::ToolCall { inner } => {
                assert_eq!(inner.id.as_str(), expected_call_id);
                assert_eq!(inner.name, "multiply");
                assert_eq!(inner.arguments, serde_json::json!({"a": 15, "b": 3}));
            }
            _ => panic!("expected tool call content"),
        }
    }

    fn run_interleaved_tool_call_case(
        chunks: Vec<StreamChunk>,
        expected_call_id: &str,
    ) -> AssistantMessage {
        let (_events, output) = process_chunks_for_test(chunks);

        assert_eq!(output.stop_reason, StopReason::ToolUse);
        assert_eq!(output.content.len(), 2);
        assert_multiply_tool_call(&output.content[0], expected_call_id);

        output
    }

    fn assert_thinking_event_sequence(events: &[AssistantMessageEvent]) {
        assert!(matches!(
            events[0],
            AssistantMessageEvent::ThinkingStart { .. }
        ));
        assert!(matches!(
            events[1],
            AssistantMessageEvent::ThinkingDelta { .. }
        ));
        assert!(matches!(
            events[2],
            AssistantMessageEvent::ThinkingEnd { .. }
        ));
    }

    fn assert_text_event_sequence(events: &[AssistantMessageEvent], start_index: usize) {
        assert!(matches!(
            events[start_index],
            AssistantMessageEvent::TextStart { .. }
        ));
        assert!(matches!(
            events[start_index + 1],
            AssistantMessageEvent::TextDelta { .. }
        ));
        assert!(matches!(
            events[start_index + 2],
            AssistantMessageEvent::TextEnd { .. }
        ));
    }

    fn assert_thinking_content(content: &Content, expected_text: &str, expected_signature: &str) {
        match content {
            Content::Thinking { inner } => {
                assert_eq!(inner.thinking, expected_text);
                assert_eq!(
                    inner.thinking_signature.as_deref(),
                    Some(expected_signature)
                );
            }
            _ => panic!("expected thinking content"),
        }
    }

    fn assert_text_content(content: &Content, expected_text: &str) {
        match content {
            Content::Text { inner } => {
                assert_eq!(inner.text, expected_text);
            }
            _ => panic!("expected text content"),
        }
    }

    #[test]
    fn build_params_for_reasoning_model_uses_minimax_semantics() {
        let model = make_model(true);
        let context = make_context();
        let options = OpenAICompletionsOptions {
            temperature: Some(1.2),
            max_tokens: Some(512),
            ..OpenAICompletionsOptions::default()
        };

        let params = build_params(&model, &context, &options);

        assert_eq!(params["stream"], true);
        assert_eq!(params["stream_options"][STREAM_INCLUDE_USAGE_FIELD], true);
        assert_eq!(params[REASONING_SPLIT_FIELD], true);
        assert_eq!(params[MAX_TOKENS_FIELD], 512);
        assert_eq!(params["temperature"], MINIMAX_MAX_TEMPERATURE);
        assert_eq!(params["messages"][0]["role"], "system");
        assert_eq!(params["messages"][0]["content"], "You are concise");
        assert!(params.get("n").is_none());
        assert!(params.get("max_completion_tokens").is_none());
    }

    #[test]
    fn build_params_for_non_reasoning_model_omits_reasoning_split() {
        let model = make_model(false);
        let context = make_context();
        let options = OpenAICompletionsOptions::default();

        let params = build_params(&model, &context, &options);

        assert!(params.get(REASONING_SPLIT_FIELD).is_none());
    }

    #[test]
    fn build_params_clamps_temperature_to_positive_lower_bound() {
        let model = make_model(true);
        let context = make_context();
        let options = OpenAICompletionsOptions {
            temperature: Some(0.0),
            ..OpenAICompletionsOptions::default()
        };

        let params = build_params(&model, &context, &options);

        assert_eq!(params["temperature"], MINIMAX_MIN_TEMPERATURE);
    }

    #[test]
    fn build_params_wraps_assistant_thinking_with_think_tags_for_replay() {
        let model = make_model(true);
        let assistant = AssistantMessage {
            content: vec![Content::thinking("step"), Content::text("answer")],
            api: Api::MinimaxCompletions,
            provider: Provider::Known(KnownProvider::Minimax),
            model: model.id.clone(),
            usage: Usage::default(),
            stop_reason: StopReason::Stop,
            error_message: None,
            timestamp: 0,
        };
        let context = Context {
            system_prompt: None,
            messages: vec![Message::Assistant(assistant)],
            tools: None,
        };

        let params = build_params(&model, &context, &OpenAICompletionsOptions::default());

        assert_eq!(params["messages"][0]["role"], "assistant");
        assert_eq!(
            params["messages"][0]["content"][0]["text"],
            "<think>step</think>"
        );
        assert_eq!(params["messages"][0]["content"][1]["text"], "answer");
    }

    #[test]
    fn process_chunk_maps_reasoning_details_to_thinking_events() {
        let chunk: StreamChunk = serde_json::from_value(serde_json::json!({
            "choices": [{
                "delta": {
                    "reasoning_details": [
                        { "type": "reasoning", "id": "r-1", "format": "text", "index": 0, "text": "step one" }
                    ]
                }
            }]
        }))
        .expect("valid reasoning details payload");

        let (events, output) = process_chunks_for_test(vec![chunk]);

        assert_thinking_event_sequence(&events);
        assert_thinking_content(&output.content[0], "step one", REASONING_DETAILS_SIGNATURE);
    }

    #[test]
    fn process_chunk_with_inline_think_tags_emits_expected_event_order() {
        let chunk: StreamChunk = serde_json::from_value(serde_json::json!({
            "choices": [{
                "delta": {
                    "content": "<think>reason</think>answer"
                }
            }]
        }))
        .expect("valid think-tag payload");

        let (events, output) = process_chunks_for_test(vec![chunk]);

        assert_thinking_event_sequence(&events);
        assert_text_event_sequence(&events, 3);

        assert_eq!(output.content.len(), 2);
        assert_thinking_content(&output.content[0], "reason", THINK_TAG_SIGNATURE);
        assert_text_content(&output.content[1], "answer");
    }

    #[test]
    fn process_chunk_prioritizes_tool_call_continuations_before_text_fallback() {
        let output = run_interleaved_tool_call_case(
            vec![
                tool_call_start_chunk("call_function_1"),
                tool_call_continuation_with_content_chunk("tail"),
            ],
            "call_function_1",
        );

        match &output.content[1] {
            Content::Text { inner } => {
                assert_eq!(inner.text, "tail");
            }
            _ => panic!("expected text content"),
        }
    }

    #[test]
    fn process_chunk_prioritizes_tool_call_continuations_before_reasoning_details() {
        let output = run_interleaved_tool_call_case(
            vec![
                tool_call_start_chunk("call_function_2"),
                tool_call_continuation_with_reasoning_chunk("next step"),
            ],
            "call_function_2",
        );

        match &output.content[1] {
            Content::Thinking { inner } => {
                assert_eq!(inner.thinking, "next step");
                assert_eq!(
                    inner.thinking_signature.as_deref(),
                    Some(REASONING_DETAILS_SIGNATURE)
                );
            }
            _ => panic!("expected thinking content"),
        }
    }

    #[test]
    fn usage_only_chunk_updates_output_usage() {
        let chunk: StreamChunk = serde_json::from_value(serde_json::json!({
            "choices": [],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 8,
                "total_tokens": 20
            }
        }))
        .expect("valid usage-only payload");

        let (_events, output) = process_chunks_for_test(vec![chunk]);

        assert_eq!(output.usage.input, 12);
        assert_eq!(output.usage.output, 8);
        assert_eq!(output.usage.total_tokens, 20);
    }

    #[test]
    fn stream_minimax_completions_final_message_shape() {
        let chunks = build_final_message_shape_chunks::<StreamChunk>(serde_json::json!({
            "reasoning_details": [{"text": "reason"}]
        }));
        let (_events, output) = process_chunks_for_test(chunks);

        assert_final_message_shape(
            &output,
            ExpectedFinalMessageShape {
                api: Api::MinimaxCompletions,
                provider: Provider::Known(KnownProvider::Minimax),
                model: "MiniMax-M2.5",
                stop_reason: StopReason::Stop,
                total_tokens: 15,
            },
        );
    }
}
