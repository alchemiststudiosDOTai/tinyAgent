use std::sync::Arc;

use anyhow::{Result, anyhow};
use futures::StreamExt;
use serde_json::Value;
use tokio::sync::Mutex;

use crate::{
    providers::{ProviderAdapter, ProviderOptions, ProviderTurnRequest},
    types::{
        AgentContext, AgentEvent, AgentLoopConfig, AgentMessage, AgentRunResult, AssistantMessage,
        AssistantMessageEvent, AssistantMessageEventType, EventEmitter, MessageContent,
        TextContent, ThinkingContent, ToolCallContent, ToolDefinition,
    },
};

pub struct StreamAssistantResult {
    pub message: AssistantMessage,
    pub continuation: Option<Value>,
}

pub async fn stream_assistant_response(
    provider: Arc<Mutex<Box<dyn ProviderAdapter>>>,
    context: AgentContext,
    tools: Vec<ToolDefinition>,
    config: AgentLoopConfig,
    continuation: Option<Value>,
    emitter: &EventEmitter<AgentEvent, AgentRunResult>,
) -> Result<StreamAssistantResult> {
    let request = ProviderTurnRequest {
        model: config.model,
        context,
        tools,
        options: ProviderOptions {
            temperature: config.temperature,
            max_tokens: config.max_tokens,
            continuation,
        },
    };

    let response = {
        let mut provider = provider.lock().await;
        provider.stream_turn(request).await?
    };

    let mut events = response.events;
    let mut partial = AssistantMessage::default();
    let mut message_started = false;
    let mut final_message: Option<AssistantMessage> = None;

    while let Some(raw_event) = events.next().await {
        let event = raw_event?;

        match event.event_type {
            AssistantMessageEventType::Start => {
                if !message_started {
                    emitter.push(AgentEvent::MessageStart {
                        message: AgentMessage::Assistant(partial.clone()),
                    })?;
                    message_started = true;
                }
            }
            AssistantMessageEventType::TextStart
            | AssistantMessageEventType::TextDelta
            | AssistantMessageEventType::TextEnd
            | AssistantMessageEventType::ThinkingStart
            | AssistantMessageEventType::ThinkingDelta
            | AssistantMessageEventType::ThinkingEnd
            | AssistantMessageEventType::ToolCallStart
            | AssistantMessageEventType::ToolCallDelta
            | AssistantMessageEventType::ToolCallEnd => {
                if !message_started {
                    emitter.push(AgentEvent::MessageStart {
                        message: AgentMessage::Assistant(partial.clone()),
                    })?;
                    message_started = true;
                }

                apply_assistant_event(&mut partial, &event);
                emitter.push(AgentEvent::MessageUpdate {
                    message: AgentMessage::Assistant(partial.clone()),
                    assistant_message_event: Some(event),
                })?;
            }
            AssistantMessageEventType::Done | AssistantMessageEventType::Error => {
                if let Some(message) = event.message.clone() {
                    final_message = Some(message);
                } else {
                    apply_assistant_event(&mut partial, &event);
                    final_message = Some(partial.clone());
                }
            }
        }
    }

    let final_message = final_message.unwrap_or_else(|| partial.clone());
    if !message_started {
        emitter.push(AgentEvent::MessageStart {
            message: AgentMessage::Assistant(final_message.clone()),
        })?;
    }
    emitter.push(AgentEvent::MessageEnd {
        message: AgentMessage::Assistant(final_message.clone()),
    })?;

    if final_message.content.is_empty() && final_message.stop_reason.is_none() {
        return Err(anyhow!(
            "provider stream ended without a final assistant message"
        ));
    }

    Ok(StreamAssistantResult {
        message: final_message,
        continuation: response.continuation,
    })
}

fn apply_assistant_event(partial: &mut AssistantMessage, event: &AssistantMessageEvent) {
    match event.event_type {
        AssistantMessageEventType::Start => {}
        AssistantMessageEventType::TextStart => {
            if let Some(MessageContent::Text(text)) = event.content.clone() {
                partial.content.push(MessageContent::Text(text));
            } else {
                partial
                    .content
                    .push(MessageContent::Text(TextContent::new(String::new())));
            }
        }
        AssistantMessageEventType::TextDelta => {
            if let Some(delta) = event.delta.as_deref() {
                partial.push_text_delta(delta);
            }
        }
        AssistantMessageEventType::TextEnd => {}
        AssistantMessageEventType::ThinkingStart => {
            if let Some(MessageContent::Thinking(thinking)) = event.content.clone() {
                partial.content.push(MessageContent::Thinking(thinking));
            } else {
                partial.content.push(MessageContent::Thinking(
                    ThinkingContent::new(String::new()),
                ));
            }
        }
        AssistantMessageEventType::ThinkingDelta => {
            if let Some(delta) = event.delta.as_deref() {
                partial.push_thinking_delta(delta);
            }
        }
        AssistantMessageEventType::ThinkingEnd => {}
        AssistantMessageEventType::ToolCallStart
        | AssistantMessageEventType::ToolCallDelta
        | AssistantMessageEventType::ToolCallEnd => {
            if let Some(tool_call) = event.tool_call.clone() {
                partial.upsert_tool_call(tool_call);
            }
        }
        AssistantMessageEventType::Done => {
            if let Some(message) = event.message.clone() {
                *partial = message;
            }
        }
        AssistantMessageEventType::Error => {
            if let Some(message) = event.message.clone() {
                *partial = message;
            } else {
                partial.stop_reason = Some(
                    event
                        .reason
                        .clone()
                        .or_else(|| event.error.clone())
                        .unwrap_or_else(|| "error".to_string()),
                );
            }
        }
    }
}

#[allow(dead_code)]
fn _tool_call_placeholder(tool_call: ToolCallContent) -> MessageContent {
    MessageContent::ToolCall(tool_call)
}
