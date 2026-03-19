use crate::agent_options::{StreamFn, StreamOptions, StreamRequest};
use crate::agent_streaming::{assistant_stream_channel, AssistantStreamResponse};
use crate::agent_types::{
    AgentTool, AssistantContent, AssistantMessage, AssistantMessageEvent, Context, Message, Model,
    StopReason, TextContent, ThinkingContent, ToolCallContent, UserContent,
};
use crate::error::{AgentError, Result};
use alchemy_llm::providers::openai_completions::ReasoningEffort;
use alchemy_llm::providers::OpenAICompletionsOptions;
use alchemy_llm::types::{
    self as alchemy_types, AnthropicMessages, Api, ApiType, InputType, Message as AlchemyMessage,
    MinimaxCompletions, Model as AlchemyModel, ModelCost, OpenAICompletions, Provider,
    Tool as AlchemyTool, ToolCallId, ZaiCompletions,
};
use futures::StreamExt;
use std::collections::HashMap;
use std::str::FromStr;
use std::sync::Arc;

pub fn default_stream_fn() -> StreamFn {
    Arc::new(|request| Box::pin(stream_via_alchemy(request)))
}

pub async fn stream_via_alchemy(request: StreamRequest) -> Result<AssistantStreamResponse> {
    let resolved_model = resolve_model(&request.model)?;
    let alchemy_context = to_alchemy_context(&request.context, &request.model, &resolved_model)?;
    let alchemy_options = to_alchemy_options(&request.model, &request.options);
    let mut alchemy_stream = resolved_model.stream(&alchemy_context, alchemy_options)?;
    let (response, event_tx, result_tx) = assistant_stream_channel();

    tokio::spawn(async move {
        while let Some(event) = alchemy_stream.next().await {
            let _ = event_tx.send(normalize_event(event));
        }

        let result = alchemy_stream
            .result()
            .await
            .map(normalize_message)
            .map_err(AgentError::from);
        let _ = result_tx.send(result);
    });

    Ok(response)
}

pub(crate) fn normalize_event(
    event: alchemy_types::AssistantMessageEvent,
) -> AssistantMessageEvent {
    match event {
        alchemy_types::AssistantMessageEvent::Start { partial } => AssistantMessageEvent::Start {
            partial: normalize_message(partial),
        },
        alchemy_types::AssistantMessageEvent::TextStart {
            content_index,
            partial,
        } => AssistantMessageEvent::TextStart {
            content_index,
            partial: normalize_message(partial),
        },
        alchemy_types::AssistantMessageEvent::TextDelta {
            content_index,
            delta,
            partial,
        } => AssistantMessageEvent::TextDelta {
            content_index,
            delta,
            partial: normalize_message(partial),
        },
        alchemy_types::AssistantMessageEvent::TextEnd {
            content_index,
            content,
            partial,
        } => AssistantMessageEvent::TextEnd {
            content_index,
            content,
            partial: normalize_message(partial),
        },
        alchemy_types::AssistantMessageEvent::ThinkingStart {
            content_index,
            partial,
        } => AssistantMessageEvent::ThinkingStart {
            content_index,
            partial: normalize_message(partial),
        },
        alchemy_types::AssistantMessageEvent::ThinkingDelta {
            content_index,
            delta,
            partial,
        } => AssistantMessageEvent::ThinkingDelta {
            content_index,
            delta,
            partial: normalize_message(partial),
        },
        alchemy_types::AssistantMessageEvent::ThinkingEnd {
            content_index,
            content,
            partial,
        } => AssistantMessageEvent::ThinkingEnd {
            content_index,
            content,
            partial: normalize_message(partial),
        },
        alchemy_types::AssistantMessageEvent::ToolCallStart {
            content_index,
            partial,
        } => AssistantMessageEvent::ToolCallStart {
            content_index,
            partial: normalize_message(partial),
        },
        alchemy_types::AssistantMessageEvent::ToolCallDelta {
            content_index,
            delta,
            partial,
        } => AssistantMessageEvent::ToolCallDelta {
            content_index,
            delta,
            partial: normalize_message(partial),
        },
        alchemy_types::AssistantMessageEvent::ToolCallEnd {
            content_index,
            tool_call,
            partial,
        } => AssistantMessageEvent::ToolCallEnd {
            content_index,
            tool_call: ToolCallContent {
                kind: "tool_call".to_string(),
                id: Some(tool_call.id.into_inner()),
                name: Some(tool_call.name),
                arguments: tool_call.arguments,
                partial_json: None,
            },
            partial: normalize_message(partial),
        },
        alchemy_types::AssistantMessageEvent::Done { reason, message } => {
            AssistantMessageEvent::Done {
                reason: normalize_stop_reason(reason.into()),
                message: normalize_message(message),
            }
        }
        alchemy_types::AssistantMessageEvent::Error { reason, error } => {
            AssistantMessageEvent::Error {
                reason: normalize_stop_reason(reason.into()),
                error: normalize_message(error),
            }
        }
    }
}

pub(crate) fn normalize_message(message: alchemy_types::AssistantMessage) -> AssistantMessage {
    let content = message
        .content
        .into_iter()
        .map(|block| match block {
            alchemy_types::Content::Text { inner } => Some(AssistantContent::Text(TextContent {
                kind: "text".to_string(),
                text: inner.text,
                text_signature: inner.text_signature,
            })),
            alchemy_types::Content::Thinking { inner } => {
                Some(AssistantContent::Thinking(ThinkingContent {
                    kind: "thinking".to_string(),
                    thinking: inner.thinking,
                    thinking_signature: inner.thinking_signature,
                }))
            }
            alchemy_types::Content::Image { inner } => Some(AssistantContent::Text(
                TextContent::new(format!("[image:{} bytes]", inner.data.len())),
            )),
            alchemy_types::Content::ToolCall { inner } => {
                Some(AssistantContent::ToolCall(ToolCallContent {
                    kind: "tool_call".to_string(),
                    id: Some(inner.id.into_inner()),
                    name: Some(inner.name),
                    arguments: inner.arguments,
                    partial_json: None,
                }))
            }
        })
        .collect::<Vec<_>>();

    AssistantMessage {
        role: "assistant".to_string(),
        content,
        stop_reason: Some(normalize_stop_reason(message.stop_reason)),
        timestamp: Some(message.timestamp),
        api: Some(message.api.to_string()),
        provider: Some(message.provider.to_string()),
        model: Some(message.model),
        usage: serde_json::to_value(message.usage).ok(),
        error_message: message.error_message,
    }
}

fn normalize_stop_reason(reason: alchemy_types::StopReason) -> StopReason {
    match reason {
        alchemy_types::StopReason::Stop => StopReason::Stop,
        alchemy_types::StopReason::Length => StopReason::Length,
        alchemy_types::StopReason::ToolUse => StopReason::ToolUse,
        alchemy_types::StopReason::Error => StopReason::Error,
        alchemy_types::StopReason::Aborted => StopReason::Aborted,
    }
}

fn to_alchemy_options(model: &Model, options: &StreamOptions) -> OpenAICompletionsOptions {
    OpenAICompletionsOptions {
        api_key: options.api_key.clone(),
        temperature: options.temperature,
        max_tokens: options.max_tokens,
        headers: merge_headers(model.headers.as_ref(), options.headers.as_ref()),
        reasoning_effort: match model.thinking_level {
            crate::agent_types::ThinkingLevel::Minimal => Some(ReasoningEffort::Minimal),
            crate::agent_types::ThinkingLevel::Low => Some(ReasoningEffort::Low),
            crate::agent_types::ThinkingLevel::Medium => Some(ReasoningEffort::Medium),
            crate::agent_types::ThinkingLevel::High => Some(ReasoningEffort::High),
            crate::agent_types::ThinkingLevel::Xhigh => Some(ReasoningEffort::Xhigh),
            crate::agent_types::ThinkingLevel::Off => None,
        },
        ..OpenAICompletionsOptions::default()
    }
}

fn merge_headers(
    model_headers: Option<&HashMap<String, String>>,
    option_headers: Option<&HashMap<String, String>>,
) -> Option<HashMap<String, String>> {
    let mut merged = HashMap::new();

    if let Some(headers) = model_headers {
        merged.extend(headers.clone());
    }
    if let Some(headers) = option_headers {
        merged.extend(headers.clone());
    }

    if merged.is_empty() {
        None
    } else {
        Some(merged)
    }
}

fn to_alchemy_context(
    context: &Context,
    _model: &Model,
    resolved_model: &ResolvedModel,
) -> Result<alchemy_types::Context> {
    let mut messages = context
        .messages
        .iter()
        .cloned()
        .map(to_alchemy_message)
        .collect::<Result<Vec<_>>>()?;

    let transformed = alchemy_llm::transform_messages_simple(
        &messages,
        &alchemy_llm::TargetModel {
            api: resolved_model.api(),
            provider: resolved_model.provider(),
            model_id: resolved_model.id().to_string(),
        },
    );
    messages = transformed;

    Ok(alchemy_types::Context {
        system_prompt: if context.system_prompt.is_empty() {
            None
        } else {
            Some(context.system_prompt.clone())
        },
        messages,
        tools: if context.tools.is_empty() {
            None
        } else {
            Some(context.tools.iter().map(to_alchemy_tool).collect())
        },
    })
}

fn to_alchemy_tool(tool: &AgentTool) -> AlchemyTool {
    AlchemyTool::new(
        tool.name.clone(),
        tool.description.clone(),
        tool.parameters.clone(),
    )
}

fn to_alchemy_message(message: Message) -> Result<AlchemyMessage> {
    match message {
        Message::User(message) => Ok(AlchemyMessage::User(alchemy_types::UserMessage {
            content: to_alchemy_user_content(message.content),
            timestamp: message.timestamp.unwrap_or_default(),
        })),
        Message::Assistant(message) => {
            Ok(AlchemyMessage::Assistant(alchemy_types::AssistantMessage {
                content: message
                    .content
                    .into_iter()
                    .flatten()
                    .map(to_alchemy_assistant_content)
                    .collect(),
                api: parse_api(message.api.as_deref().unwrap_or("openai-completions"))?,
                provider: parse_provider(message.provider.as_deref().unwrap_or("openai"))?,
                model: message.model.unwrap_or_default(),
                usage: message
                    .usage
                    .and_then(|usage| serde_json::from_value(usage).ok())
                    .unwrap_or_default(),
                stop_reason: to_alchemy_stop_reason(
                    message.stop_reason.unwrap_or(StopReason::Stop),
                ),
                error_message: message.error_message,
                timestamp: message.timestamp.unwrap_or_default(),
            }))
        }
        Message::ToolResult(message) => Ok(AlchemyMessage::ToolResult(
            alchemy_types::ToolResultMessage {
                tool_call_id: ToolCallId::from(message.tool_call_id.unwrap_or_default()),
                tool_name: message.tool_name.unwrap_or_default(),
                content: message
                    .content
                    .into_iter()
                    .map(to_alchemy_tool_result_content)
                    .collect(),
                details: Some(message.details),
                is_error: message.is_error,
                timestamp: message.timestamp.unwrap_or_default(),
            },
        )),
    }
}

fn to_alchemy_user_content(content: Vec<UserContent>) -> alchemy_types::UserContent {
    if content.len() == 1 {
        match content.into_iter().next().expect("single item exists") {
            UserContent::Text(text) => return alchemy_types::UserContent::Text(text.text),
            UserContent::Image(image) => {
                return alchemy_types::UserContent::Multi(vec![
                    alchemy_types::UserContentBlock::Image(alchemy_types::ImageContent {
                        data: image.url.into_bytes(),
                        mime_type: image
                            .mime_type
                            .unwrap_or_else(|| "application/octet-stream".to_string()),
                    }),
                ])
            }
        }
    }

    alchemy_types::UserContent::Multi(
        content
            .into_iter()
            .map(|item| match item {
                UserContent::Text(text) => {
                    alchemy_types::UserContentBlock::Text(alchemy_types::TextContent {
                        text: text.text,
                        text_signature: text.text_signature,
                    })
                }
                UserContent::Image(image) => {
                    alchemy_types::UserContentBlock::Image(alchemy_types::ImageContent {
                        data: image.url.into_bytes(),
                        mime_type: image
                            .mime_type
                            .unwrap_or_else(|| "application/octet-stream".to_string()),
                    })
                }
            })
            .collect(),
    )
}

fn to_alchemy_assistant_content(content: AssistantContent) -> alchemy_types::Content {
    match content {
        AssistantContent::Text(text) => alchemy_types::Content::Text {
            inner: alchemy_types::TextContent {
                text: text.text,
                text_signature: text.text_signature,
            },
        },
        AssistantContent::Thinking(thinking) => alchemy_types::Content::Thinking {
            inner: alchemy_types::ThinkingContent {
                thinking: thinking.thinking,
                thinking_signature: thinking.thinking_signature,
            },
        },
        AssistantContent::ToolCall(tool_call) => alchemy_types::Content::ToolCall {
            inner: alchemy_types::ToolCall {
                id: ToolCallId::from(tool_call.id.unwrap_or_default()),
                name: tool_call.name.unwrap_or_default(),
                arguments: tool_call.arguments,
                thought_signature: None,
            },
        },
    }
}

fn to_alchemy_tool_result_content(content: UserContent) -> alchemy_types::ToolResultContent {
    match content {
        UserContent::Text(text) => {
            alchemy_types::ToolResultContent::Text(alchemy_types::TextContent {
                text: text.text,
                text_signature: text.text_signature,
            })
        }
        UserContent::Image(image) => {
            alchemy_types::ToolResultContent::Image(alchemy_types::ImageContent {
                data: image.url.into_bytes(),
                mime_type: image
                    .mime_type
                    .unwrap_or_else(|| "application/octet-stream".to_string()),
            })
        }
    }
}

fn to_alchemy_stop_reason(reason: StopReason) -> alchemy_types::StopReason {
    match reason {
        StopReason::Complete | StopReason::Stop => alchemy_types::StopReason::Stop,
        StopReason::Length => alchemy_types::StopReason::Length,
        StopReason::ToolCalls | StopReason::ToolUse => alchemy_types::StopReason::ToolUse,
        StopReason::Error => alchemy_types::StopReason::Error,
        StopReason::Aborted => alchemy_types::StopReason::Aborted,
    }
}

fn parse_api(value: &str) -> Result<Api> {
    Api::from_str(value).map_err(AgentError::from)
}

fn parse_provider(value: &str) -> Result<Provider> {
    Provider::from_str(value).map_err(AgentError::from)
}

const ZERO_MODEL_COST: ModelCost = ModelCost {
    input: 0.0,
    output: 0.0,
    cache_read: 0.0,
    cache_write: 0.0,
};

#[derive(Debug, Clone)]
enum ResolvedModel {
    Anthropic(AlchemyModel<AnthropicMessages>),
    OpenAi(AlchemyModel<OpenAICompletions>),
    Minimax(AlchemyModel<MinimaxCompletions>),
    Zai(AlchemyModel<ZaiCompletions>),
}

impl ResolvedModel {
    fn api(&self) -> Api {
        match self {
            Self::Anthropic(model) => model.api.api(),
            Self::OpenAi(model) => model.api.api(),
            Self::Minimax(model) => model.api.api(),
            Self::Zai(model) => model.api.api(),
        }
    }

    fn provider(&self) -> Provider {
        match self {
            Self::Anthropic(model) => model.provider.clone(),
            Self::OpenAi(model) => model.provider.clone(),
            Self::Minimax(model) => model.provider.clone(),
            Self::Zai(model) => model.provider.clone(),
        }
    }

    fn id(&self) -> &str {
        match self {
            Self::Anthropic(model) => &model.id,
            Self::OpenAi(model) => &model.id,
            Self::Minimax(model) => &model.id,
            Self::Zai(model) => &model.id,
        }
    }

    fn stream(
        &self,
        context: &alchemy_types::Context,
        options: OpenAICompletionsOptions,
    ) -> Result<alchemy_types::AssistantMessageEventStream> {
        match self {
            Self::Anthropic(model) => {
                alchemy_llm::stream(model, context, Some(options)).map_err(AgentError::from)
            }
            Self::OpenAi(model) => {
                alchemy_llm::stream(model, context, Some(options)).map_err(AgentError::from)
            }
            Self::Minimax(model) => {
                alchemy_llm::stream(model, context, Some(options)).map_err(AgentError::from)
            }
            Self::Zai(model) => {
                alchemy_llm::stream(model, context, Some(options)).map_err(AgentError::from)
            }
        }
    }
}

fn resolve_model(model: &Model) -> Result<ResolvedModel> {
    match (
        model.provider.as_str(),
        model.api.as_str(),
        model.id.as_str(),
    ) {
        ("anthropic", "anthropic-messages", "claude-opus-4-6") => {
            Ok(ResolvedModel::Anthropic(alchemy_llm::claude_opus_4_6()))
        }
        ("anthropic", "anthropic-messages", "claude-sonnet-4-6") => {
            Ok(ResolvedModel::Anthropic(alchemy_llm::claude_sonnet_4_6()))
        }
        ("anthropic", "anthropic-messages", "claude-haiku-4-5-20251001") => {
            Ok(ResolvedModel::Anthropic(alchemy_llm::claude_haiku_4_5()))
        }
        ("kimi", "anthropic-messages", "kimi-coding") => {
            Ok(ResolvedModel::Anthropic(alchemy_llm::kimi_k2_5()))
        }
        ("featherless", "openai-completions", id) => {
            Ok(ResolvedModel::OpenAi(alchemy_llm::featherless_model(id)))
        }
        ("minimax", "minimax-completions", "MiniMax-M2.5") => {
            Ok(ResolvedModel::Minimax(alchemy_llm::minimax_m2_5()))
        }
        ("minimax", "minimax-completions", "MiniMax-M2.5-highspeed") => {
            Ok(ResolvedModel::Minimax(alchemy_llm::minimax_m2_5_highspeed()))
        }
        ("minimax", "minimax-completions", "MiniMax-M2.1") => {
            Ok(ResolvedModel::Minimax(alchemy_llm::minimax_m2_1()))
        }
        ("minimax", "minimax-completions", "MiniMax-M2.1-highspeed") => {
            Ok(ResolvedModel::Minimax(alchemy_llm::minimax_m2_1_highspeed()))
        }
        ("minimax", "minimax-completions", "MiniMax-M2") => {
            Ok(ResolvedModel::Minimax(alchemy_llm::minimax_m2()))
        }
        ("minimax-cn", "minimax-completions", "MiniMax-M2.5") => {
            Ok(ResolvedModel::Minimax(alchemy_llm::minimax_cn_m2_5()))
        }
        ("minimax-cn", "minimax-completions", "MiniMax-M2.5-highspeed") => Ok(
            ResolvedModel::Minimax(alchemy_llm::minimax_cn_m2_5_highspeed()),
        ),
        ("minimax-cn", "minimax-completions", "MiniMax-M2.1") => {
            Ok(ResolvedModel::Minimax(alchemy_llm::minimax_cn_m2_1()))
        }
        ("minimax-cn", "minimax-completions", "MiniMax-M2.1-highspeed") => Ok(
            ResolvedModel::Minimax(alchemy_llm::minimax_cn_m2_1_highspeed()),
        ),
        ("minimax-cn", "minimax-completions", "MiniMax-M2") => {
            Ok(ResolvedModel::Minimax(alchemy_llm::minimax_cn_m2()))
        }
        ("zai", "zai-completions", "glm-5") => Ok(ResolvedModel::Zai(alchemy_llm::glm_5())),
        ("zai", "zai-completions", "glm-4.7") => Ok(ResolvedModel::Zai(alchemy_llm::glm_4_7())),
        ("zai", "zai-completions", "glm-4.7-flash") => {
            Ok(ResolvedModel::Zai(alchemy_llm::glm_4_7_flash()))
        }
        ("zai", "zai-completions", "glm-4.7-flashx") => {
            Ok(ResolvedModel::Zai(alchemy_llm::glm_4_7_flashx()))
        }
        ("zai", "zai-completions", "glm-4.6") => Ok(ResolvedModel::Zai(alchemy_llm::glm_4_6())),
        ("zai", "zai-completions", "glm-4.5") => Ok(ResolvedModel::Zai(alchemy_llm::glm_4_5())),
        ("zai", "zai-completions", "glm-4.5-air") => {
            Ok(ResolvedModel::Zai(alchemy_llm::glm_4_5_air()))
        }
        ("zai", "zai-completions", "glm-4.5-x") => Ok(ResolvedModel::Zai(alchemy_llm::glm_4_5_x())),
        ("zai", "zai-completions", "glm-4.5-airx") => {
            Ok(ResolvedModel::Zai(alchemy_llm::glm_4_5_airx()))
        }
        ("zai", "zai-completions", "glm-4.5-flash") => {
            Ok(ResolvedModel::Zai(alchemy_llm::glm_4_5_flash()))
        }
        ("zai", "zai-completions", "glm-4-32b-0414-128k") => {
            Ok(ResolvedModel::Zai(alchemy_llm::glm_4_32b_0414_128k()))
        }
        _ => resolve_custom_model(model),
    }
}

fn resolve_custom_model(model: &Model) -> Result<ResolvedModel> {
    let provider = parse_provider(&model.provider)?;
    let reasoning = !matches!(model.thinking_level, crate::agent_types::ThinkingLevel::Off);
    let base_url = model
        .base_url
        .clone()
        .ok_or_else(|| AgentError::UnsupportedModel {
            provider: model.provider.clone(),
            api: model.api.clone(),
            id: model.id.clone(),
        })?;
    let headers = model.headers.clone();

    match parse_api(&model.api)? {
        Api::AnthropicMessages => Ok(ResolvedModel::Anthropic(AlchemyModel {
            id: model.id.clone(),
            name: model.id.clone(),
            api: AnthropicMessages,
            provider,
            base_url,
            reasoning,
            input: vec![InputType::Text, InputType::Image],
            cost: ZERO_MODEL_COST,
            context_window: 200_000,
            max_tokens: 64_000,
            headers,
            compat: None,
        })),
        Api::OpenAICompletions => Ok(ResolvedModel::OpenAi(AlchemyModel {
            id: model.id.clone(),
            name: model.id.clone(),
            api: OpenAICompletions,
            provider,
            base_url,
            reasoning,
            input: vec![InputType::Text],
            cost: ZERO_MODEL_COST,
            context_window: 128_000,
            max_tokens: 16_384,
            headers,
            compat: None,
        })),
        Api::MinimaxCompletions => Ok(ResolvedModel::Minimax(AlchemyModel {
            id: model.id.clone(),
            name: model.id.clone(),
            api: MinimaxCompletions,
            provider,
            base_url,
            reasoning: true,
            input: vec![InputType::Text],
            cost: ZERO_MODEL_COST,
            context_window: 204_800,
            max_tokens: 16_384,
            headers,
            compat: None,
        })),
        Api::ZaiCompletions => Ok(ResolvedModel::Zai(AlchemyModel {
            id: model.id.clone(),
            name: model.id.clone(),
            api: ZaiCompletions,
            provider,
            base_url,
            reasoning: true,
            input: vec![InputType::Text],
            cost: ZERO_MODEL_COST,
            context_window: 200_000,
            max_tokens: 128_000,
            headers,
            compat: None,
        })),
        unsupported => Err(AgentError::UnsupportedApi(unsupported.to_string())),
    }
}

#[cfg(test)]
mod tests {
    use super::{default_stream_fn, normalize_event, normalize_message};
    use crate::agent_types::{AssistantContent, StopReason};
    use alchemy_llm::types::{
        Api, AssistantMessage, AssistantMessageEvent, Content, Provider, StopReasonSuccess, Usage,
    };
    use serde_json::json;

    fn sample_alchemy_message() -> AssistantMessage {
        AssistantMessage {
            content: vec![
                Content::text("hello"),
                Content::thinking("reason"),
                Content::tool_call("call-1", "search", json!({"query": "rust"})),
            ],
            api: Api::OpenAICompletions,
            provider: Provider::Custom("test".to_string()),
            model: "test-model".to_string(),
            usage: Usage::default(),
            stop_reason: alchemy_llm::types::StopReason::ToolUse,
            error_message: None,
            timestamp: 123,
        }
    }

    #[test]
    fn normalizes_alchemy_message() {
        let message = normalize_message(sample_alchemy_message());
        assert_eq!(message.api.as_deref(), Some("openai-completions"));
        assert_eq!(message.provider.as_deref(), Some("test"));
        assert_eq!(message.stop_reason, Some(StopReason::ToolUse));
        assert!(matches!(
            message.content[0],
            Some(AssistantContent::Text(_))
        ));
        assert!(matches!(
            message.content[1],
            Some(AssistantContent::Thinking(_))
        ));
        assert!(matches!(
            message.content[2],
            Some(AssistantContent::ToolCall(_))
        ));
    }

    #[tokio::test]
    async fn normalizes_synthetic_event_sequence() {
        let partial = sample_alchemy_message();
        let events = vec![
            AssistantMessageEvent::Start {
                partial: partial.clone(),
            },
            AssistantMessageEvent::TextDelta {
                content_index: 0,
                delta: "hello".to_string(),
                partial: partial.clone(),
            },
            AssistantMessageEvent::ThinkingDelta {
                content_index: 1,
                delta: "reason".to_string(),
                partial: partial.clone(),
            },
            AssistantMessageEvent::ToolCallEnd {
                content_index: 2,
                tool_call: alchemy_llm::types::ToolCall {
                    id: "call-1".into(),
                    name: "search".to_string(),
                    arguments: json!({"query": "rust"}),
                    thought_signature: None,
                },
                partial: partial.clone(),
            },
            AssistantMessageEvent::Done {
                reason: StopReasonSuccess::ToolUse,
                message: partial,
            },
        ]
        .into_iter()
        .map(normalize_event)
        .collect::<Vec<_>>();

        match &events[1] {
            crate::agent_types::AssistantMessageEvent::TextDelta { delta, .. } => {
                assert_eq!(delta, "hello");
            }
            other => panic!("unexpected event: {other:?}"),
        }

        match &events[2] {
            crate::agent_types::AssistantMessageEvent::ThinkingDelta { delta, .. } => {
                assert_eq!(delta, "reason");
            }
            other => panic!("unexpected event: {other:?}"),
        }

        match &events[3] {
            crate::agent_types::AssistantMessageEvent::ToolCallEnd { tool_call, .. } => {
                assert_eq!(tool_call.name.as_deref(), Some("search"));
            }
            other => panic!("unexpected event: {other:?}"),
        }

        match &events[4] {
            crate::agent_types::AssistantMessageEvent::Done { reason, .. } => {
                assert_eq!(*reason, StopReason::ToolUse);
            }
            other => panic!("unexpected event: {other:?}"),
        }
    }

    #[test]
    fn builds_default_stream_function() {
        let _ = default_stream_fn();
    }
}
