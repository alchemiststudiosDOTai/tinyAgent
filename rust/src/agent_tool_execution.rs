use std::fmt;
use std::panic::AssertUnwindSafe;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};

use futures::future::join_all;
use futures::FutureExt;
use tokio::sync::Notify;

use crate::agent_loop::AgentEventStream;
use crate::types::{
    AgentMessage, AgentMessageProvider, AgentTool, AgentToolResult, AgentToolUpdateCallback,
    AssistantContent, AssistantMessage, JsonObject, Message, MessageEndEvent, MessageStartEvent,
    TextContent, ToolCallContent, ToolExecutionEndEvent, ToolExecutionStartEvent,
    ToolExecutionUpdateEvent, ToolResultContent, ToolResultMessage,
};

pub type ToolExecutionContractResult<T> = Result<T, ToolExecutionError>;

#[derive(Debug, Clone, Default)]
pub struct ToolExecutionResult {
    pub tool_results: Vec<ToolResultMessage>,
    pub steering_messages: Option<Vec<AgentMessage>>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ToolExecutionError {
    MissingToolCallId,
    MissingToolCallName,
}

impl fmt::Display for ToolExecutionError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingToolCallId => f.write_str("tool call is missing required id"),
            Self::MissingToolCallName => f.write_str("tool call is missing required name"),
        }
    }
}

impl std::error::Error for ToolExecutionError {}

#[derive(Debug, Clone)]
struct ExecutableToolCall {
    id: String,
    name: String,
    arguments: JsonObject,
}

pub fn validate_tool_arguments(tool: &AgentTool, tool_call: &ToolCallContent) -> JsonObject {
    let _ = tool;
    tool_call.arguments.clone()
}

pub async fn execute_tool_calls(
    tools: Option<&[AgentTool]>,
    assistant_message: &AssistantMessage,
    signal: Option<Arc<Notify>>,
    stream: &AgentEventStream,
    get_steering_messages: Option<AgentMessageProvider>,
) -> ToolExecutionContractResult<ToolExecutionResult> {
    let tool_calls = extract_tool_calls(assistant_message)?;
    if tool_calls.is_empty() {
        return Ok(ToolExecutionResult::default());
    }

    for tool_call in &tool_calls {
        stream.push(crate::types::AgentEvent::ToolExecutionStart(
            ToolExecutionStartEvent {
                tool_call_id: tool_call.id.clone(),
                tool_name: tool_call.name.clone(),
                args: Some(tool_call.arguments.clone()),
                ..Default::default()
            },
        ));
    }

    let resolved_tools = tool_calls
        .iter()
        .map(|tool_call| find_tool(tools, &tool_call.name).cloned())
        .collect::<Vec<_>>();

    let raw_results = join_all(
        resolved_tools
            .into_iter()
            .zip(tool_calls.iter().cloned())
            .map(|(tool, tool_call)| {
                execute_single_tool(tool, tool_call, signal.clone(), Arc::clone(stream))
            }),
    )
    .await;

    let mut tool_results = Vec::with_capacity(raw_results.len());

    for (tool_call, (result, is_error)) in tool_calls.iter().zip(raw_results.into_iter()) {
        stream.push(crate::types::AgentEvent::ToolExecutionEnd(
            ToolExecutionEndEvent {
                tool_call_id: tool_call.id.clone(),
                tool_name: tool_call.name.clone(),
                result: Some(result.clone()),
                is_error,
                ..Default::default()
            },
        ));

        let tool_result_message = create_tool_result_message(tool_call, result, is_error);
        let tool_result_agent_message =
            AgentMessage::Message(Message::ToolResult(tool_result_message.clone()));

        tool_results.push(tool_result_message);
        stream.push(crate::types::AgentEvent::MessageStart(MessageStartEvent {
            message: Some(tool_result_agent_message.clone()),
            ..Default::default()
        }));
        stream.push(crate::types::AgentEvent::MessageEnd(MessageEndEvent {
            message: Some(tool_result_agent_message),
            ..Default::default()
        }));
    }

    let steering_messages = match get_steering_messages {
        Some(provider) => {
            let messages = provider().await;
            if messages.is_empty() {
                None
            } else {
                Some(messages)
            }
        }
        None => None,
    };

    Ok(ToolExecutionResult {
        tool_results,
        steering_messages,
    })
}

pub fn skip_tool_call(
    tool_call: &ToolCallContent,
    stream: &AgentEventStream,
) -> ToolExecutionContractResult<ToolResultMessage> {
    let executable_tool_call = executable_tool_call(tool_call)?;
    let result = AgentToolResult {
        content: vec![ToolResultContent::Text(TextContent {
            text: Some("Skipped due to queued user message.".to_string()),
            ..Default::default()
        })],
        details: JsonObject::new(),
    };

    stream.push(crate::types::AgentEvent::ToolExecutionStart(
        ToolExecutionStartEvent {
            tool_call_id: executable_tool_call.id.clone(),
            tool_name: executable_tool_call.name.clone(),
            args: Some(executable_tool_call.arguments.clone()),
            ..Default::default()
        },
    ));
    stream.push(crate::types::AgentEvent::ToolExecutionEnd(
        ToolExecutionEndEvent {
            tool_call_id: executable_tool_call.id.clone(),
            tool_name: executable_tool_call.name.clone(),
            result: Some(result.clone()),
            is_error: true,
            ..Default::default()
        },
    ));

    let tool_result_message = create_tool_result_message(&executable_tool_call, result, true);
    let tool_result_agent_message =
        AgentMessage::Message(Message::ToolResult(tool_result_message.clone()));

    stream.push(crate::types::AgentEvent::MessageStart(MessageStartEvent {
        message: Some(tool_result_agent_message.clone()),
        ..Default::default()
    }));
    stream.push(crate::types::AgentEvent::MessageEnd(MessageEndEvent {
        message: Some(tool_result_agent_message),
        ..Default::default()
    }));

    Ok(tool_result_message)
}

async fn execute_single_tool(
    tool: Option<AgentTool>,
    tool_call: ExecutableToolCall,
    signal: Option<Arc<Notify>>,
    stream: AgentEventStream,
) -> (AgentToolResult, bool) {
    match tool {
        None => (
            AgentToolResult {
                content: vec![ToolResultContent::Text(TextContent {
                    text: Some(format!("Tool {} not found", tool_call.name)),
                    ..Default::default()
                })],
                details: JsonObject::new(),
            },
            true,
        ),
        Some(tool) => match tool.execute {
            None => (
                AgentToolResult {
                    content: vec![ToolResultContent::Text(TextContent {
                        text: Some(format!("Tool {} has no execute function", tool_call.name)),
                        ..Default::default()
                    })],
                    details: JsonObject::new(),
                },
                true,
            ),
            Some(ref execute) => {
                let tool_call_id = tool_call.id.clone();
                let tool_call_name = tool_call.name.clone();
                let tool_call_args = tool_call.arguments.clone();
                let update_stream = Arc::clone(&stream);
                let tool_call_content = ToolCallContent {
                    id: Some(tool_call.id.clone()),
                    name: Some(tool_call.name.clone()),
                    arguments: tool_call.arguments.clone(),
                    ..Default::default()
                };
                let validated_args = validate_tool_arguments(&tool, &tool_call_content);
                let on_update: AgentToolUpdateCallback = Arc::new(move |partial_result| {
                    update_stream.push(crate::types::AgentEvent::ToolExecutionUpdate(
                        ToolExecutionUpdateEvent {
                            tool_call_id: tool_call_id.clone(),
                            tool_name: tool_call_name.clone(),
                            args: Some(tool_call_args.clone()),
                            partial_result: Some(partial_result),
                            ..Default::default()
                        },
                    ));
                });

                let future = execute(tool_call.id.clone(), validated_args, signal, on_update);

                match AssertUnwindSafe(future).catch_unwind().await {
                    Ok(result) => (result, false),
                    Err(_) => (
                        AgentToolResult {
                            content: vec![ToolResultContent::Text(TextContent {
                                text: Some(format!("Tool {} panicked during execution", tool_call.name)),
                                ..Default::default()
                            })],
                            details: JsonObject::new(),
                        },
                        true,
                    ),
                }
            }
        },
    }
}

fn extract_tool_calls(
    assistant_message: &AssistantMessage,
) -> ToolExecutionContractResult<Vec<ExecutableToolCall>> {
    assistant_message
        .content
        .iter()
        .filter_map(|content| match content {
            Some(AssistantContent::ToolCall(tool_call)) => Some(executable_tool_call(tool_call)),
            _ => None,
        })
        .collect()
}

fn executable_tool_call(
    tool_call: &ToolCallContent,
) -> ToolExecutionContractResult<ExecutableToolCall> {
    let id = tool_call
        .id
        .clone()
        .ok_or(ToolExecutionError::MissingToolCallId)?;
    let name = tool_call
        .name
        .clone()
        .ok_or(ToolExecutionError::MissingToolCallName)?;

    Ok(ExecutableToolCall {
        id,
        name,
        arguments: tool_call.arguments.clone(),
    })
}

fn find_tool<'a>(tools: Option<&'a [AgentTool]>, name: &str) -> Option<&'a AgentTool> {
    tools.and_then(|tools| tools.iter().find(|tool| tool.name == name))
}

fn create_tool_result_message(
    tool_call: &ExecutableToolCall,
    result: AgentToolResult,
    is_error: bool,
) -> ToolResultMessage {
    ToolResultMessage {
        tool_call_id: Some(tool_call.id.clone()),
        tool_name: Some(tool_call.name.clone()),
        content: result.content,
        details: result.details,
        is_error,
        timestamp: Some(current_timestamp_ms()),
        ..Default::default()
    }
}

fn current_timestamp_ms() -> i64 {
    match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(duration) => duration.as_millis() as i64,
        Err(error) => -(error.duration().as_millis() as i64),
    }
}
