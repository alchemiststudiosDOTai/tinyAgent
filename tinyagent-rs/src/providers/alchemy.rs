use anyhow::{Result, anyhow};
use async_trait::async_trait;
use futures::StreamExt;

use crate::{
    providers::{ProviderAdapter, ProviderTurnRequest, ProviderTurnResponse},
    types::{
        AgentContext, AgentMessage, AssistantMessage, AssistantMessageEvent,
        AssistantMessageEventType, ImageContent, MessageContent, TextContent, ThinkingContent,
        ToolCallContent, ToolDefinition, ToolResultMessage,
    },
};

pub struct AlchemyMinimaxProvider {
    model_id: String,
}

impl Default for AlchemyMinimaxProvider {
    fn default() -> Self {
        Self::new("MiniMax-M2.1")
    }
}

impl AlchemyMinimaxProvider {
    pub fn new(model_id: impl Into<String>) -> Self {
        Self {
            model_id: model_id.into(),
        }
    }
}

#[async_trait]
impl ProviderAdapter for AlchemyMinimaxProvider {
    async fn stream_turn(&mut self, request: ProviderTurnRequest) -> Result<ProviderTurnResponse> {
        let mut model = minimax_model(if request.model.id.is_empty() {
            &self.model_id
        } else {
            &request.model.id
        });
        model.reasoning = request.model.thinking_level != crate::types::ThinkingLevel::Off;

        let context = to_alchemy_context(&request.context, &request.tools)?;
        let options = alchemy_llm::OpenAICompletionsOptions {
            api_key: None,
            temperature: request.options.temperature.map(f64::from),
            max_tokens: request.options.max_tokens,
            tool_choice: None,
            reasoning_effort: None,
            headers: None,
            zai: None,
        };

        let stream = alchemy_llm::stream(&model, &context, Some(options))?;
        let events = stream.map(|event| Ok(from_alchemy_event(event))).boxed();

        Ok(ProviderTurnResponse {
            events,
            continuation: None,
        })
    }
}

fn minimax_model(
    model_id: &str,
) -> alchemy_llm::types::Model<alchemy_llm::types::MinimaxCompletions> {
    let mut model = match model_id {
        "MiniMax-M2.5" => alchemy_llm::minimax_m2_5(),
        "MiniMax-M2.5-highspeed" => alchemy_llm::minimax_m2_5_highspeed(),
        "MiniMax-M2.1" => alchemy_llm::minimax_m2_1(),
        "MiniMax-M2.1-highspeed" => alchemy_llm::minimax_m2_1_highspeed(),
        "MiniMax-M2" => alchemy_llm::minimax_m2(),
        other => {
            let mut model = alchemy_llm::minimax_m2_1();
            model.id = other.to_string();
            model.name = other.to_string();
            model
        }
    };
    model.id = model_id.to_string();
    model.name = model_id.to_string();
    model
}

fn to_alchemy_context(
    context: &AgentContext,
    tools: &[ToolDefinition],
) -> Result<alchemy_llm::types::Context> {
    let messages = context
        .messages
        .iter()
        .map(to_alchemy_message)
        .collect::<Result<Vec<_>>>()?;
    let tools = if tools.is_empty() {
        None
    } else {
        Some(
            tools
                .iter()
                .map(|tool| {
                    alchemy_llm::types::Tool::new(
                        tool.name.clone(),
                        tool.description.clone(),
                        tool.parameters.clone(),
                    )
                })
                .collect(),
        )
    };

    Ok(alchemy_llm::types::Context {
        system_prompt: if context.system_prompt.is_empty() {
            None
        } else {
            Some(context.system_prompt.clone())
        },
        messages,
        tools,
    })
}

fn to_alchemy_message(message: &AgentMessage) -> Result<alchemy_llm::types::Message> {
    match message {
        AgentMessage::User(user) => Ok(alchemy_llm::types::Message::User(
            alchemy_llm::types::UserMessage {
                content: to_alchemy_user_content(&user.content)?,
                timestamp: 0,
            },
        )),
        AgentMessage::Assistant(assistant) => Ok(alchemy_llm::types::Message::Assistant(
            to_alchemy_assistant_message(assistant),
        )),
        AgentMessage::ToolResult(tool_result) => Ok(alchemy_llm::types::Message::ToolResult(
            to_alchemy_tool_result(tool_result)?,
        )),
    }
}

fn to_alchemy_user_content(content: &[MessageContent]) -> Result<alchemy_llm::types::UserContent> {
    if content.len() == 1 {
        if let MessageContent::Text(text) = &content[0] {
            return Ok(alchemy_llm::types::UserContent::Text(text.text.clone()));
        }
    }

    let mut blocks = Vec::new();
    for block in content {
        match block {
            MessageContent::Text(text) => {
                blocks.push(alchemy_llm::types::UserContentBlock::Text(
                    alchemy_llm::types::TextContent {
                        text: text.text.clone(),
                        text_signature: None,
                    },
                ));
            }
            MessageContent::Image(image) => {
                blocks.push(alchemy_llm::types::UserContentBlock::Image(
                    to_alchemy_image(image)?,
                ));
            }
            MessageContent::Thinking(_) | MessageContent::ToolCall(_) => {}
        }
    }

    Ok(alchemy_llm::types::UserContent::Multi(blocks))
}

fn to_alchemy_assistant_message(
    assistant: &AssistantMessage,
) -> alchemy_llm::types::AssistantMessage {
    alchemy_llm::types::AssistantMessage {
        content: assistant
            .content
            .iter()
            .filter_map(|content| match content {
                MessageContent::Text(text) => Some(alchemy_llm::types::Content::Text {
                    inner: alchemy_llm::types::TextContent {
                        text: text.text.clone(),
                        text_signature: None,
                    },
                }),
                MessageContent::Thinking(thinking) => Some(alchemy_llm::types::Content::Thinking {
                    inner: alchemy_llm::types::ThinkingContent {
                        thinking: thinking.text.clone(),
                        thinking_signature: thinking.signature.clone(),
                    },
                }),
                MessageContent::ToolCall(tool_call) => {
                    Some(alchemy_llm::types::Content::ToolCall {
                        inner: alchemy_llm::types::ToolCall {
                            id: tool_call.id.clone().into(),
                            name: tool_call.name.clone(),
                            arguments: tool_call.arguments.clone(),
                            thought_signature: None,
                        },
                    })
                }
                MessageContent::Image(_) => None,
            })
            .collect(),
        api: alchemy_llm::types::Api::MinimaxCompletions,
        provider: alchemy_llm::types::Provider::Known(alchemy_llm::types::KnownProvider::Minimax),
        model: "MiniMax".to_string(),
        usage: alchemy_llm::types::Usage::default(),
        stop_reason: to_alchemy_stop_reason(assistant.stop_reason.as_deref()),
        error_message: None,
        timestamp: 0,
    }
}

fn to_alchemy_tool_result(
    result: &ToolResultMessage,
) -> Result<alchemy_llm::types::ToolResultMessage> {
    let mut content = Vec::new();
    for block in &result.content {
        match block {
            MessageContent::Text(text) => {
                content.push(alchemy_llm::types::ToolResultContent::Text(
                    alchemy_llm::types::TextContent {
                        text: text.text.clone(),
                        text_signature: None,
                    },
                ));
            }
            MessageContent::Image(image) => {
                content.push(alchemy_llm::types::ToolResultContent::Image(
                    to_alchemy_image(image)?,
                ));
            }
            MessageContent::Thinking(_) | MessageContent::ToolCall(_) => {}
        }
    }

    Ok(alchemy_llm::types::ToolResultMessage {
        tool_call_id: result.tool_call_id.clone().into(),
        tool_name: result.tool_name.clone(),
        content,
        details: if result.details.is_empty() {
            None
        } else {
            Some(serde_json::Value::Object(result.details.clone()))
        },
        is_error: result.is_error,
        timestamp: 0,
    })
}

fn to_alchemy_image(image: &ImageContent) -> Result<alchemy_llm::types::ImageContent> {
    let url = image.url.as_str();
    let Some(rest) = url.strip_prefix("data:") else {
        return Err(anyhow!(
            "only data: image URLs are supported in the alchemy adapter"
        ));
    };
    let Some((mime_type, data)) = rest.split_once(";base64,") else {
        return Err(anyhow!("invalid data URL for image content"));
    };
    Ok(alchemy_llm::types::ImageContent::from_base64(
        data,
        mime_type.to_string(),
    )?)
}

fn from_alchemy_event(event: alchemy_llm::types::AssistantMessageEvent) -> AssistantMessageEvent {
    match event {
        alchemy_llm::types::AssistantMessageEvent::Start { partial } => AssistantMessageEvent {
            event_type: AssistantMessageEventType::Start,
            partial: Some(from_alchemy_message(&partial)),
            content_index: None,
            delta: None,
            content: None,
            tool_call: None,
            reason: None,
            message: None,
            error: None,
        },
        alchemy_llm::types::AssistantMessageEvent::TextStart {
            content_index,
            partial,
        } => AssistantMessageEvent {
            event_type: AssistantMessageEventType::TextStart,
            partial: Some(from_alchemy_message(&partial)),
            content_index: Some(content_index),
            delta: None,
            content: None,
            tool_call: None,
            reason: None,
            message: None,
            error: None,
        },
        alchemy_llm::types::AssistantMessageEvent::TextDelta {
            content_index,
            delta,
            partial,
        } => AssistantMessageEvent {
            event_type: AssistantMessageEventType::TextDelta,
            partial: Some(from_alchemy_message(&partial)),
            content_index: Some(content_index),
            delta: Some(delta),
            content: None,
            tool_call: None,
            reason: None,
            message: None,
            error: None,
        },
        alchemy_llm::types::AssistantMessageEvent::TextEnd {
            content_index,
            content,
            partial,
        } => AssistantMessageEvent {
            event_type: AssistantMessageEventType::TextEnd,
            partial: Some(from_alchemy_message(&partial)),
            content_index: Some(content_index),
            delta: None,
            content: Some(MessageContent::Text(TextContent::new(content))),
            tool_call: None,
            reason: None,
            message: None,
            error: None,
        },
        alchemy_llm::types::AssistantMessageEvent::ThinkingStart {
            content_index,
            partial,
        } => AssistantMessageEvent {
            event_type: AssistantMessageEventType::ThinkingStart,
            partial: Some(from_alchemy_message(&partial)),
            content_index: Some(content_index),
            delta: None,
            content: None,
            tool_call: None,
            reason: None,
            message: None,
            error: None,
        },
        alchemy_llm::types::AssistantMessageEvent::ThinkingDelta {
            content_index,
            delta,
            partial,
        } => AssistantMessageEvent {
            event_type: AssistantMessageEventType::ThinkingDelta,
            partial: Some(from_alchemy_message(&partial)),
            content_index: Some(content_index),
            delta: Some(delta),
            content: None,
            tool_call: None,
            reason: None,
            message: None,
            error: None,
        },
        alchemy_llm::types::AssistantMessageEvent::ThinkingEnd {
            content_index,
            content,
            partial,
        } => AssistantMessageEvent {
            event_type: AssistantMessageEventType::ThinkingEnd,
            partial: Some(from_alchemy_message(&partial)),
            content_index: Some(content_index),
            delta: None,
            content: Some(MessageContent::Thinking(ThinkingContent {
                text: content,
                signature: None,
            })),
            tool_call: None,
            reason: None,
            message: None,
            error: None,
        },
        alchemy_llm::types::AssistantMessageEvent::ToolCallStart {
            content_index,
            partial,
        } => AssistantMessageEvent {
            event_type: AssistantMessageEventType::ToolCallStart,
            partial: Some(from_alchemy_message(&partial)),
            content_index: Some(content_index),
            delta: None,
            content: None,
            tool_call: None,
            reason: None,
            message: None,
            error: None,
        },
        alchemy_llm::types::AssistantMessageEvent::ToolCallDelta {
            content_index,
            delta,
            partial,
        } => AssistantMessageEvent {
            event_type: AssistantMessageEventType::ToolCallDelta,
            partial: Some(from_alchemy_message(&partial)),
            content_index: Some(content_index),
            delta: Some(delta),
            content: None,
            tool_call: None,
            reason: None,
            message: None,
            error: None,
        },
        alchemy_llm::types::AssistantMessageEvent::ToolCallEnd {
            content_index,
            tool_call,
            partial,
        } => AssistantMessageEvent {
            event_type: AssistantMessageEventType::ToolCallEnd,
            partial: Some(from_alchemy_message(&partial)),
            content_index: Some(content_index),
            delta: None,
            content: None,
            tool_call: Some(ToolCallContent {
                id: tool_call.id.into_inner(),
                name: tool_call.name,
                arguments: tool_call.arguments,
            }),
            reason: None,
            message: None,
            error: None,
        },
        alchemy_llm::types::AssistantMessageEvent::Done { reason, message } => {
            AssistantMessageEvent {
                event_type: AssistantMessageEventType::Done,
                partial: None,
                content_index: None,
                delta: None,
                content: None,
                tool_call: None,
                reason: Some(
                    match reason {
                        alchemy_llm::types::StopReasonSuccess::Stop => "stop",
                        alchemy_llm::types::StopReasonSuccess::Length => "length",
                        alchemy_llm::types::StopReasonSuccess::ToolUse => "tool_use",
                    }
                    .to_string(),
                ),
                message: Some(from_alchemy_message(&message)),
                error: None,
            }
        }
        alchemy_llm::types::AssistantMessageEvent::Error { reason, error } => {
            AssistantMessageEvent {
                event_type: AssistantMessageEventType::Error,
                partial: None,
                content_index: None,
                delta: None,
                content: None,
                tool_call: None,
                reason: Some(
                    match reason {
                        alchemy_llm::types::StopReasonError::Error => "error",
                        alchemy_llm::types::StopReasonError::Aborted => "aborted",
                    }
                    .to_string(),
                ),
                message: Some(from_alchemy_message(&error)),
                error: error.error_message,
            }
        }
    }
}

fn from_alchemy_message(message: &alchemy_llm::types::AssistantMessage) -> AssistantMessage {
    AssistantMessage {
        content: message
            .content
            .iter()
            .filter_map(from_alchemy_content)
            .collect(),
        stop_reason: Some(
            match message.stop_reason {
                alchemy_llm::types::StopReason::Stop => "stop",
                alchemy_llm::types::StopReason::Length => "length",
                alchemy_llm::types::StopReason::ToolUse => "tool_use",
                alchemy_llm::types::StopReason::Error => "error",
                alchemy_llm::types::StopReason::Aborted => "aborted",
            }
            .to_string(),
        ),
    }
}

fn from_alchemy_content(content: &alchemy_llm::types::Content) -> Option<MessageContent> {
    match content {
        alchemy_llm::types::Content::Text { inner } => Some(MessageContent::Text(TextContent {
            text: inner.text.clone(),
        })),
        alchemy_llm::types::Content::Thinking { inner } => {
            Some(MessageContent::Thinking(ThinkingContent {
                text: inner.thinking.clone(),
                signature: inner.thinking_signature.clone(),
            }))
        }
        alchemy_llm::types::Content::ToolCall { inner } => {
            Some(MessageContent::ToolCall(ToolCallContent {
                id: inner.id.to_string(),
                name: inner.name.clone(),
                arguments: inner.arguments.clone(),
            }))
        }
        alchemy_llm::types::Content::Image { inner } => Some(MessageContent::Image(ImageContent {
            url: format!("data:{};base64,{}", inner.mime_type, inner.to_base64()),
            media_type: Some(inner.mime_type.clone()),
        })),
    }
}

fn to_alchemy_stop_reason(reason: Option<&str>) -> alchemy_llm::types::StopReason {
    match reason {
        Some("length") => alchemy_llm::types::StopReason::Length,
        Some("tool_use") => alchemy_llm::types::StopReason::ToolUse,
        Some("error") => alchemy_llm::types::StopReason::Error,
        Some("aborted") => alchemy_llm::types::StopReason::Aborted,
        _ => alchemy_llm::types::StopReason::Stop,
    }
}
