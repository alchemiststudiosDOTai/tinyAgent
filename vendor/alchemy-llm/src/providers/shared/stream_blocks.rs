use serde::Deserialize;

use crate::types::{
    AssistantMessage, AssistantMessageEvent, Content, EventStreamSender, StopReason, ToolCall,
    Usage,
};

#[derive(Debug)]
pub(crate) enum CurrentBlock {
    Text {
        text: String,
    },
    Thinking {
        thinking: String,
        signature: String,
    },
    ToolCall {
        id: String,
        name: String,
        partial_args: String,
    },
}

pub(crate) struct ReasoningDelta<'a> {
    pub text: &'a str,
    pub signature: &'a str,
}

#[derive(Debug, Clone, Deserialize)]
pub(crate) struct OpenAiLikeToolCallDelta {
    pub id: Option<String>,
    pub function: Option<OpenAiLikeFunctionDelta>,
}

#[derive(Debug, Clone, Deserialize)]
pub(crate) struct OpenAiLikeFunctionDelta {
    pub name: Option<String>,
    pub arguments: Option<String>,
}

#[derive(Debug, Deserialize)]
#[serde(bound(deserialize = "TDelta: Deserialize<'de>"))]
pub(crate) struct OpenAiLikeStreamChunk<TDelta> {
    #[serde(default)]
    pub choices: Vec<OpenAiLikeStreamChoice<TDelta>>,
    pub usage: Option<OpenAiLikeStreamUsage>,
}

#[derive(Debug, Deserialize)]
#[serde(bound(deserialize = "TDelta: Deserialize<'de>"))]
pub(crate) struct OpenAiLikeStreamChoice<TDelta> {
    pub delta: Option<TDelta>,
    pub finish_reason: Option<String>,
}

pub(crate) struct OpenAiLikeChunkPrelude<'a, TDelta> {
    pub delta: &'a TDelta,
    tool_calls: Option<&'a [OpenAiLikeToolCallDelta]>,
    prioritize_tool_calls: bool,
}

#[derive(Debug, Deserialize)]
pub(crate) struct OpenAiLikeStreamUsage {
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
    pub total_tokens: Option<u32>,
    pub cache_read_input_tokens: Option<u32>,
    pub cache_creation_input_tokens: Option<u32>,
    pub cost: Option<f64>,
    pub cost_details: Option<StreamCostDetails>,
    pub prompt_tokens_details: Option<PromptTokensDetails>,
    #[serde(rename = "completion_tokens_details")]
    _completion_tokens_details: Option<CompletionTokensDetails>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct StreamCostDetails {
    upstream_inference_prompt_cost: Option<f64>,
    upstream_inference_completions_cost: Option<f64>,
    upstream_inference_cost: Option<f64>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct PromptTokensDetails {
    cached_tokens: Option<u32>,
    cache_write_tokens: Option<u32>,
}

#[derive(Debug, Deserialize)]
struct CompletionTokensDetails {
    #[serde(rename = "reasoning_tokens")]
    _reasoning_tokens: Option<u32>,
}

pub(crate) fn update_usage_from_chunk(
    usage: &OpenAiLikeStreamUsage,
    output: &mut AssistantMessage,
) {
    let cache_read_tokens = usage
        .cache_read_input_tokens
        .or_else(|| {
            usage
                .prompt_tokens_details
                .as_ref()
                .and_then(|details| details.cached_tokens)
        })
        .unwrap_or(0);

    let cache_write_tokens = usage
        .cache_creation_input_tokens
        .or_else(|| {
            usage
                .prompt_tokens_details
                .as_ref()
                .and_then(|details| details.cache_write_tokens)
        })
        .unwrap_or(0);

    let input_tokens = usage.prompt_tokens;
    let output_tokens = usage.completion_tokens;
    let total_tokens = usage.total_tokens.unwrap_or(input_tokens + output_tokens);

    let cost_input = usage
        .cost_details
        .as_ref()
        .and_then(|details| details.upstream_inference_prompt_cost)
        .unwrap_or(0.0);

    let cost_output = usage
        .cost_details
        .as_ref()
        .and_then(|details| details.upstream_inference_completions_cost)
        .unwrap_or(0.0);

    let cost_cache_read = 0.0;
    let cost_cache_write = 0.0;

    let has_component_cost = usage.cost_details.as_ref().is_some_and(|details| {
        details.upstream_inference_prompt_cost.is_some()
            || details.upstream_inference_completions_cost.is_some()
    });

    let component_total_cost =
        has_component_cost.then_some(cost_input + cost_output + cost_cache_read + cost_cache_write);

    let cost_total = usage
        .cost_details
        .as_ref()
        .and_then(|details| details.upstream_inference_cost)
        .or(usage.cost)
        .or(component_total_cost)
        .unwrap_or(0.0);

    output.usage = Usage {
        input: input_tokens,
        output: output_tokens,
        cache_read: cache_read_tokens,
        cache_write: cache_write_tokens,
        total_tokens,
        cost: crate::types::Cost {
            input: cost_input,
            output: cost_output,
            cache_read: cost_cache_read,
            cache_write: cost_cache_write,
            total: cost_total,
        },
    };
}

pub(crate) fn prepare_openai_like_chunk<'a, TDelta, FStopReason, FToolCalls>(
    chunk: &'a OpenAiLikeStreamChunk<TDelta>,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
    map_stop_reason: FStopReason,
    delta_tool_calls: FToolCalls,
) -> Option<OpenAiLikeChunkPrelude<'a, TDelta>>
where
    FStopReason: Fn(&str) -> StopReason,
    FToolCalls: Fn(&'a TDelta) -> Option<&'a [OpenAiLikeToolCallDelta]>,
{
    if let Some(usage) = &chunk.usage {
        update_usage_from_chunk(usage, output);
    }

    let choice = chunk.choices.first()?;

    if let Some(reason) = &choice.finish_reason {
        output.stop_reason = map_stop_reason(reason);
    }

    let delta = choice.delta.as_ref()?;
    let tool_calls = delta_tool_calls(delta);
    let prioritize_tool_calls =
        matches!(current_block, Some(CurrentBlock::ToolCall { .. })) && tool_calls.is_some();

    if prioritize_tool_calls {
        if let Some(tool_call_deltas) = tool_calls {
            handle_tool_calls(tool_call_deltas, output, sender, current_block);
        }
    }

    Some(OpenAiLikeChunkPrelude {
        delta,
        tool_calls,
        prioritize_tool_calls,
    })
}

pub(crate) fn apply_deferred_tool_calls<TDelta>(
    prelude: OpenAiLikeChunkPrelude<'_, TDelta>,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
) {
    if prelude.prioritize_tool_calls {
        return;
    }

    if let Some(tool_call_deltas) = prelude.tool_calls {
        handle_tool_calls(tool_call_deltas, output, sender, current_block);
    }
}

pub(crate) fn handle_text_delta(
    content: &str,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
) {
    if content.is_empty() {
        return;
    }

    match current_block {
        Some(CurrentBlock::Text { text }) => {
            text.push_str(content);
            sender.push(AssistantMessageEvent::TextDelta {
                content_index: output.content.len().saturating_sub(1),
                delta: content.to_string(),
                partial: output.clone(),
            });
        }
        _ => {
            finish_current_block(current_block, output, sender);

            let text = content.to_string();
            *current_block = Some(CurrentBlock::Text { text: text.clone() });
            output.content.push(Content::text(""));
            let content_index = output.content.len() - 1;

            sender.push(AssistantMessageEvent::TextStart {
                content_index,
                partial: output.clone(),
            });
            sender.push(AssistantMessageEvent::TextDelta {
                content_index,
                delta: text,
                partial: output.clone(),
            });
        }
    }
}

pub(crate) fn handle_reasoning_delta(
    reasoning: ReasoningDelta<'_>,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
) {
    if reasoning.text.is_empty() {
        return;
    }

    match current_block {
        Some(CurrentBlock::Thinking { thinking, .. }) => {
            thinking.push_str(reasoning.text);
            sender.push(AssistantMessageEvent::ThinkingDelta {
                content_index: output.content.len().saturating_sub(1),
                delta: reasoning.text.to_string(),
                partial: output.clone(),
            });
        }
        _ => {
            finish_current_block(current_block, output, sender);

            let thinking = reasoning.text.to_string();
            *current_block = Some(CurrentBlock::Thinking {
                thinking: thinking.clone(),
                signature: reasoning.signature.to_string(),
            });
            output.content.push(Content::thinking(""));
            let content_index = output.content.len() - 1;

            sender.push(AssistantMessageEvent::ThinkingStart {
                content_index,
                partial: output.clone(),
            });
            sender.push(AssistantMessageEvent::ThinkingDelta {
                content_index,
                delta: thinking,
                partial: output.clone(),
            });
        }
    }
}

pub(crate) fn handle_tool_calls(
    tool_calls: &[OpenAiLikeToolCallDelta],
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
) {
    for tool_call in tool_calls {
        if should_start_new_tool_call(current_block, tool_call) {
            start_tool_call_block(tool_call, output, sender, current_block);
        }

        apply_tool_call_delta(tool_call, output, sender, current_block);
    }
}

fn should_start_new_tool_call(
    current_block: &Option<CurrentBlock>,
    tool_call: &OpenAiLikeToolCallDelta,
) -> bool {
    match current_block {
        Some(CurrentBlock::ToolCall { id, .. }) => tool_call
            .id
            .as_ref()
            .is_some_and(|new_id| !new_id.is_empty() && !id.is_empty() && new_id != id),
        _ => has_tool_call_identity(tool_call),
    }
}

fn has_tool_call_identity(tool_call: &OpenAiLikeToolCallDelta) -> bool {
    if tool_call
        .id
        .as_ref()
        .is_some_and(|tool_call_id| !tool_call_id.is_empty())
    {
        return true;
    }

    tool_call
        .function
        .as_ref()
        .and_then(|function| function.name.as_ref())
        .is_some_and(|tool_name| !tool_name.is_empty())
}

fn start_tool_call_block(
    tool_call: &OpenAiLikeToolCallDelta,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
) {
    finish_current_block(current_block, output, sender);

    let id = tool_call.id.clone().unwrap_or_default();
    let name = tool_call
        .function
        .as_ref()
        .and_then(|function| function.name.clone())
        .unwrap_or_default();

    *current_block = Some(CurrentBlock::ToolCall {
        id: id.clone(),
        name: name.clone(),
        partial_args: String::new(),
    });

    output.content.push(Content::tool_call(
        id,
        name,
        serde_json::Value::Object(serde_json::Map::new()),
    ));

    sender.push(AssistantMessageEvent::ToolCallStart {
        content_index: output.content.len() - 1,
        partial: output.clone(),
    });
}

fn apply_tool_call_delta(
    tool_call: &OpenAiLikeToolCallDelta,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
) {
    let Some(CurrentBlock::ToolCall {
        id,
        name,
        partial_args,
    }) = current_block
    else {
        return;
    };

    if let Some(new_id) = &tool_call.id {
        *id = new_id.clone();
    }

    if let Some(function) = &tool_call.function {
        if let Some(new_name) = &function.name {
            *name = new_name.clone();
        }

        if let Some(arguments) = &function.arguments {
            partial_args.push_str(arguments);

            sender.push(AssistantMessageEvent::ToolCallDelta {
                content_index: output.content.len() - 1,
                delta: arguments.clone(),
                partial: output.clone(),
            });
        }
    }
}

pub(crate) fn finish_current_block(
    current_block: &mut Option<CurrentBlock>,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
) {
    let Some(block) = current_block.take() else {
        return;
    };

    let content_index = output.content.len().saturating_sub(1);

    match block {
        CurrentBlock::Text { text } => {
            if let Some(Content::Text { inner }) = output.content.get_mut(content_index) {
                inner.text = text.clone();
            }

            sender.push(AssistantMessageEvent::TextEnd {
                content_index,
                content: text,
                partial: output.clone(),
            });
        }
        CurrentBlock::Thinking {
            thinking,
            signature,
        } => {
            if let Some(Content::Thinking { inner }) = output.content.get_mut(content_index) {
                inner.thinking = thinking.clone();
                inner.thinking_signature = Some(signature);
            }

            sender.push(AssistantMessageEvent::ThinkingEnd {
                content_index,
                content: thinking,
                partial: output.clone(),
            });
        }
        CurrentBlock::ToolCall {
            id,
            name,
            partial_args,
        } => {
            let arguments: serde_json::Value = serde_json::from_str(&partial_args)
                .unwrap_or_else(|_| serde_json::Value::Object(serde_json::Map::new()));

            if let Some(Content::ToolCall { inner }) = output.content.get_mut(content_index) {
                inner.id = id.clone().into();
                inner.name = name.clone();
                inner.arguments = arguments.clone();
            }

            sender.push(AssistantMessageEvent::ToolCallEnd {
                content_index,
                tool_call: ToolCall {
                    id: id.into(),
                    name,
                    arguments,
                    thought_signature: None,
                },
                partial: output.clone(),
            });
        }
    }
}

pub(crate) fn map_stop_reason(reason: &str) -> StopReason {
    match reason {
        "stop" => StopReason::Stop,
        "length" => StopReason::Length,
        "function_call" | "tool_calls" => StopReason::ToolUse,
        "content_filter" => StopReason::Error,
        _ => StopReason::Stop,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{Api, AssistantMessageEventStream, KnownProvider, Provider};

    fn make_output_message() -> AssistantMessage {
        AssistantMessage {
            content: vec![],
            api: Api::OpenAICompletions,
            provider: Provider::Known(KnownProvider::OpenAI),
            model: "test-model".to_string(),
            usage: Usage::default(),
            stop_reason: StopReason::Stop,
            error_message: None,
            timestamp: 0,
        }
    }

    #[test]
    fn map_stop_reason_matches_openai_contract() {
        assert_eq!(map_stop_reason("stop"), StopReason::Stop);
        assert_eq!(map_stop_reason("length"), StopReason::Length);
        assert_eq!(map_stop_reason("tool_calls"), StopReason::ToolUse);
        assert_eq!(map_stop_reason("function_call"), StopReason::ToolUse);
        assert_eq!(map_stop_reason("content_filter"), StopReason::Error);
        assert_eq!(map_stop_reason("unknown"), StopReason::Stop);
    }

    #[test]
    fn handle_tool_calls_ignores_orphan_argument_delta_without_identity() {
        let (_stream, mut sender) = AssistantMessageEventStream::new();
        let mut output = make_output_message();
        let mut current_block: Option<CurrentBlock> = None;

        let orphan_delta = OpenAiLikeToolCallDelta {
            id: None,
            function: Some(OpenAiLikeFunctionDelta {
                name: None,
                arguments: Some("{\"a\": 15, \"b\": ".to_string()),
            }),
        };

        handle_tool_calls(
            &[orphan_delta],
            &mut output,
            &mut sender,
            &mut current_block,
        );

        assert!(current_block.is_none());
        assert!(output.content.is_empty());
    }

    #[test]
    fn handle_tool_calls_merges_idless_continuation_into_active_tool_call() {
        let (_stream, mut sender) = AssistantMessageEventStream::new();
        let mut output = make_output_message();
        let mut current_block: Option<CurrentBlock> = None;

        let start_delta = OpenAiLikeToolCallDelta {
            id: Some("call_123".to_string()),
            function: Some(OpenAiLikeFunctionDelta {
                name: Some("multiply".to_string()),
                arguments: Some("{\"a\": 15, \"b\": ".to_string()),
            }),
        };

        let continuation_delta = OpenAiLikeToolCallDelta {
            id: None,
            function: Some(OpenAiLikeFunctionDelta {
                name: None,
                arguments: Some("3}".to_string()),
            }),
        };

        handle_tool_calls(&[start_delta], &mut output, &mut sender, &mut current_block);
        handle_tool_calls(
            &[continuation_delta],
            &mut output,
            &mut sender,
            &mut current_block,
        );
        finish_current_block(&mut current_block, &mut output, &mut sender);

        assert_eq!(output.content.len(), 1);
        match &output.content[0] {
            Content::ToolCall { inner } => {
                assert_eq!(inner.id.as_str(), "call_123");
                assert_eq!(inner.name, "multiply");
                assert_eq!(inner.arguments, serde_json::json!({"a": 15, "b": 3}));
            }
            _ => panic!("expected tool call content"),
        }
    }

    #[test]
    fn update_usage_uses_provider_raw_totals() {
        let usage: OpenAiLikeStreamUsage = serde_json::from_value(serde_json::json!({
            "prompt_tokens": 79,
            "completion_tokens": 114,
            "completion_tokens_details": {
                "reasoning_tokens": 91
            },
            "total_tokens": 193
        }))
        .expect("valid usage payload");

        let mut output = make_output_message();
        update_usage_from_chunk(&usage, &mut output);

        assert_eq!(output.usage.input, 79);
        assert_eq!(output.usage.output, 114);
        assert_eq!(output.usage.total_tokens, 193);
    }

    #[test]
    fn update_usage_uses_provider_cache_tokens_when_present() {
        let usage: OpenAiLikeStreamUsage = serde_json::from_value(serde_json::json!({
            "prompt_tokens": 100,
            "completion_tokens": 25,
            "total_tokens": 125,
            "cache_read_input_tokens": 12,
            "cache_creation_input_tokens": 9,
            "prompt_tokens_details": {
                "cached_tokens": 7,
                "cache_write_tokens": 5
            }
        }))
        .expect("valid usage payload");

        let mut output = make_output_message();
        update_usage_from_chunk(&usage, &mut output);

        assert_eq!(output.usage.cache_read, 12);
        assert_eq!(output.usage.cache_write, 9);
    }

    #[test]
    fn update_usage_falls_back_to_prompt_details() {
        let usage: OpenAiLikeStreamUsage = serde_json::from_value(serde_json::json!({
            "prompt_tokens": 80,
            "completion_tokens": 20,
            "prompt_tokens_details": {
                "cached_tokens": 15,
                "cache_write_tokens": 4
            }
        }))
        .expect("valid usage payload");

        let mut output = make_output_message();
        update_usage_from_chunk(&usage, &mut output);

        assert_eq!(output.usage.cache_read, 15);
        assert_eq!(output.usage.cache_write, 4);
        assert_eq!(output.usage.total_tokens, 100);
    }

    #[test]
    fn update_usage_maps_cost_details() {
        let usage: OpenAiLikeStreamUsage = serde_json::from_value(serde_json::json!({
            "prompt_tokens": 16,
            "completion_tokens": 4,
            "total_tokens": 20,
            "cost": 0.0001782,
            "cost_details": {
                "upstream_inference_prompt_cost": 0.00008,
                "upstream_inference_completions_cost": 0.0001,
                "upstream_inference_cost": 0.00018
            }
        }))
        .expect("valid usage payload");

        let mut output = make_output_message();
        update_usage_from_chunk(&usage, &mut output);

        assert_eq!(output.usage.cost.input, 0.00008);
        assert_eq!(output.usage.cost.output, 0.0001);
        assert_eq!(output.usage.cost.total, 0.00018);
    }

    #[test]
    fn update_usage_uses_top_level_cost_when_details_missing() {
        let usage: OpenAiLikeStreamUsage = serde_json::from_value(serde_json::json!({
            "prompt_tokens": 16,
            "completion_tokens": 4,
            "total_tokens": 20,
            "cost": 0.0001782
        }))
        .expect("valid usage payload");

        let mut output = make_output_message();
        update_usage_from_chunk(&usage, &mut output);

        assert_eq!(output.usage.cost.input, 0.0);
        assert_eq!(output.usage.cost.output, 0.0);
        assert_eq!(output.usage.cost.total, 0.0001782);
    }

    #[test]
    fn update_usage_falls_back_to_component_sum_when_total_missing() {
        let usage: OpenAiLikeStreamUsage = serde_json::from_value(serde_json::json!({
            "prompt_tokens": 16,
            "completion_tokens": 4,
            "total_tokens": 20,
            "cost_details": {
                "upstream_inference_prompt_cost": 0.00008,
                "upstream_inference_completions_cost": 0.0001
            }
        }))
        .expect("valid usage payload");

        let mut output = make_output_message();
        update_usage_from_chunk(&usage, &mut output);

        assert_eq!(output.usage.cost.input, 0.00008);
        assert_eq!(output.usage.cost.output, 0.0001);
        assert_eq!(output.usage.cost.total, 0.00018);
    }

    #[test]
    fn update_usage_defaults_cost_to_zero_when_missing() {
        let usage: OpenAiLikeStreamUsage = serde_json::from_value(serde_json::json!({
            "prompt_tokens": 16,
            "completion_tokens": 4,
            "total_tokens": 20
        }))
        .expect("valid usage payload");

        let mut output = make_output_message();
        update_usage_from_chunk(&usage, &mut output);

        assert_eq!(output.usage.cost.input, 0.0);
        assert_eq!(output.usage.cost.output, 0.0);
        assert_eq!(output.usage.cost.cache_read, 0.0);
        assert_eq!(output.usage.cost.cache_write, 0.0);
        assert_eq!(output.usage.cost.total, 0.0);
    }
}
