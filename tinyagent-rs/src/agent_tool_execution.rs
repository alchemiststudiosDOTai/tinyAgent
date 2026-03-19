use crate::agent_options::MessageProvider;
use crate::agent_streaming::AgentEventTx;
use crate::agent_types::{
    current_timestamp, AgentEvent, AgentMessage, AgentTool, AgentToolResult, AssistantContent,
    AssistantMessage, JsonObject, TextContent, ToolCallContent, ToolResultMessage,
    ToolUpdateCallback, UserContent,
};
use crate::error::Result;
use futures::future::join_all;
use serde_json::{Map, Value};
use tokio_util::sync::CancellationToken;

#[derive(Clone)]
pub struct ToolCallContext {
    pub tool_call_id: String,
    pub args: JsonObject,
    pub abort: CancellationToken,
    on_update: ToolUpdateCallback,
}

impl core::fmt::Debug for ToolCallContext {
    fn fmt(&self, f: &mut core::fmt::Formatter<'_>) -> core::fmt::Result {
        f.debug_struct("ToolCallContext")
            .field("tool_call_id", &self.tool_call_id)
            .field("args", &self.args)
            .field("abort_cancelled", &self.abort.is_cancelled())
            .finish()
    }
}

impl ToolCallContext {
    pub fn emit_update(&self, partial_result: AgentToolResult) {
        (self.on_update)(partial_result);
    }
}

#[derive(Debug, Clone, Default)]
pub struct ToolExecutionResult {
    pub tool_results: Vec<ToolResultMessage>,
    pub steering_messages: Option<Vec<AgentMessage>>,
}

pub fn normalize_tool_arguments(_tool: &AgentTool, tool_call: &ToolCallContent) -> JsonObject {
    match &tool_call.arguments {
        Value::Object(map) => map.clone(),
        Value::String(raw) => serde_json::from_str::<Value>(raw)
            .ok()
            .and_then(|parsed| match parsed {
                Value::Object(map) => Some(map),
                _ => None,
            })
            .unwrap_or_default(),
        _ => JsonObject::new(),
    }
}

pub async fn execute_tool_calls(
    tools: &[AgentTool],
    assistant_message: &AssistantMessage,
    abort: CancellationToken,
    event_tx: &AgentEventTx,
    get_steering_messages: Option<MessageProvider>,
) -> Result<ToolExecutionResult> {
    let tool_calls = extract_tool_calls(assistant_message);
    if tool_calls.is_empty() {
        return Ok(ToolExecutionResult::default());
    }

    for tool_call in &tool_calls {
        let _ = event_tx.send(AgentEvent::ToolExecutionStart {
            tool_call_id: tool_call.id.clone().unwrap_or_default(),
            tool_name: tool_call.name.clone().unwrap_or_default(),
            args: Some(tool_call.arguments.clone()),
        });
    }

    let futures = tool_calls
        .iter()
        .map(|tool_call| {
            let tool = find_tool(tools, tool_call.name.as_deref().unwrap_or_default()).cloned();
            let event_tx = event_tx.clone();
            let tool_call = tool_call.clone();
            let abort = abort.clone();

            async move { execute_single_tool(tool, &tool_call, abort, event_tx).await }
        })
        .collect::<Vec<_>>();

    let raw_results = join_all(futures).await;
    let mut tool_results = Vec::with_capacity(raw_results.len());

    for (tool_call, (result, is_error)) in tool_calls.iter().zip(raw_results.into_iter()) {
        let _ = event_tx.send(AgentEvent::ToolExecutionEnd {
            tool_call_id: tool_call.id.clone().unwrap_or_default(),
            tool_name: tool_call.name.clone().unwrap_or_default(),
            result: Some(result.clone()),
            is_error,
        });

        let message = ToolResultMessage::from_result(
            tool_call.id.clone().unwrap_or_default(),
            tool_call.name.clone().unwrap_or_default(),
            result,
            is_error,
        );

        let _ = event_tx.send(AgentEvent::MessageStart {
            message: Some(AgentMessage::ToolResult(message.clone())),
        });
        let _ = event_tx.send(AgentEvent::MessageEnd {
            message: Some(AgentMessage::ToolResult(message.clone())),
        });

        tool_results.push(message);
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

pub fn skip_tool_call(tool_call: &ToolCallContent, event_tx: &AgentEventTx) -> ToolResultMessage {
    let result = AgentToolResult {
        content: vec![UserContent::Text(TextContent::new(
            "Skipped due to queued user message.",
        ))],
        details: Value::Object(Map::new()),
    };

    let tool_call_id = tool_call.id.clone().unwrap_or_default();
    let tool_name = tool_call.name.clone().unwrap_or_default();

    let _ = event_tx.send(AgentEvent::ToolExecutionStart {
        tool_call_id: tool_call_id.clone(),
        tool_name: tool_name.clone(),
        args: Some(tool_call.arguments.clone()),
    });
    let _ = event_tx.send(AgentEvent::ToolExecutionEnd {
        tool_call_id: tool_call_id.clone(),
        tool_name: tool_name.clone(),
        result: Some(result.clone()),
        is_error: true,
    });

    let message = ToolResultMessage {
        role: "tool_result".to_string(),
        tool_call_id: Some(tool_call_id),
        tool_name: Some(tool_name),
        content: result.content,
        details: result.details,
        is_error: true,
        timestamp: Some(current_timestamp()),
    };

    let _ = event_tx.send(AgentEvent::MessageStart {
        message: Some(AgentMessage::ToolResult(message.clone())),
    });
    let _ = event_tx.send(AgentEvent::MessageEnd {
        message: Some(AgentMessage::ToolResult(message.clone())),
    });

    message
}

fn extract_tool_calls(assistant_message: &AssistantMessage) -> Vec<ToolCallContent> {
    assistant_message
        .content
        .iter()
        .filter_map(|content| match content {
            Some(AssistantContent::ToolCall(tool_call)) => Some(tool_call.clone()),
            _ => None,
        })
        .collect()
}

fn find_tool<'a>(tools: &'a [AgentTool], name: &str) -> Option<&'a AgentTool> {
    tools.iter().find(|tool| tool.name == name)
}

async fn execute_single_tool(
    tool: Option<AgentTool>,
    tool_call: &ToolCallContent,
    abort: CancellationToken,
    event_tx: AgentEventTx,
) -> (AgentToolResult, bool) {
    let tool_name = tool_call.name.clone().unwrap_or_default();

    let Some(tool) = tool else {
        return (
            AgentToolResult {
                content: vec![UserContent::Text(TextContent::new(format!(
                    "Tool {tool_name} not found"
                )))],
                details: Value::Object(Map::new()),
            },
            true,
        );
    };

    let args = normalize_tool_arguments(&tool, tool_call);
    let tool_call_id = tool_call.id.clone().unwrap_or_default();
    let tool_name_for_updates = tool_name.clone();
    let tool_args_for_updates = tool_call.arguments.clone();
    let update_tx = event_tx.clone();
    let on_update: ToolUpdateCallback = std::sync::Arc::new(move |partial_result| {
        let _ = update_tx.send(AgentEvent::ToolExecutionUpdate {
            tool_call_id: tool_call_id.clone(),
            tool_name: tool_name_for_updates.clone(),
            args: Some(tool_args_for_updates.clone()),
            partial_result: Some(partial_result),
        });
    });

    match tool
        .call(
            tool_call.id.clone().unwrap_or_default(),
            args,
            abort,
            on_update,
        )
        .await
    {
        Ok(result) => (result, false),
        Err(error) => (
            AgentToolResult {
                content: vec![UserContent::Text(TextContent::new(error.to_string()))],
                details: Value::Object(Map::new()),
            },
            true,
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::{execute_tool_calls, normalize_tool_arguments};
    use crate::agent_streaming::agent_event_channel;
    use crate::agent_types::{
        AgentTool, AgentToolResult, AssistantContent, AssistantMessage, TextContent,
        ToolCallContent, UserContent,
    };
    use futures::StreamExt;
    use serde_json::{json, Value};
    use tokio_util::sync::CancellationToken;

    #[tokio::test]
    async fn parses_object_and_string_tool_arguments_and_builds_canonical_result_message() {
        let tool = AgentTool::new(
            "echo",
            "Echo input",
            json!({"type": "object"}),
            |_id, args, _abort, on_update| async move {
                on_update(AgentToolResult {
                    content: vec![UserContent::Text(TextContent::new("running"))],
                    details: json!({"phase": "update"}),
                });

                Ok(AgentToolResult {
                    content: vec![UserContent::Text(TextContent::new(
                        args.get("value")
                            .and_then(|value| value.as_str())
                            .unwrap_or_default(),
                    ))],
                    details: json!({"ok": true}),
                })
            },
        );

        let object_call = ToolCallContent {
            kind: "tool_call".to_string(),
            id: Some("call-1".to_string()),
            name: Some("echo".to_string()),
            arguments: json!({"value": "object"}),
            partial_json: None,
        };
        let string_call = ToolCallContent {
            arguments: Value::String("{\"value\":\"string\"}".to_string()),
            ..object_call.clone()
        };

        assert_eq!(
            normalize_tool_arguments(&tool, &object_call)
                .get("value")
                .and_then(|value| value.as_str()),
            Some("object")
        );
        assert_eq!(
            normalize_tool_arguments(&tool, &string_call)
                .get("value")
                .and_then(|value| value.as_str()),
            Some("string")
        );

        let assistant_message = AssistantMessage {
            content: vec![
                Some(AssistantContent::ToolCall(object_call)),
                Some(AssistantContent::ToolCall(string_call)),
            ],
            ..AssistantMessage::default()
        };

        let (stream, event_tx, result_tx) = agent_event_channel();
        let execution = execute_tool_calls(
            &[tool],
            &assistant_message,
            CancellationToken::new(),
            &event_tx,
            None,
        )
        .await
        .expect("tool execution should succeed");
        drop(event_tx);
        let _ = result_tx.send(Ok(Vec::new()));

        assert_eq!(execution.tool_results.len(), 2);
        assert_eq!(
            execution.tool_results[0]
                .content
                .iter()
                .filter_map(|content| match content {
                    UserContent::Text(text) => Some(text.text.as_str()),
                    UserContent::Image(_) => None,
                })
                .collect::<String>(),
            "object"
        );
        assert_eq!(
            execution.tool_results[1]
                .content
                .iter()
                .filter_map(|content| match content {
                    UserContent::Text(text) => Some(text.text.as_str()),
                    UserContent::Image(_) => None,
                })
                .collect::<String>(),
            "string"
        );

        let events = stream.collect::<Vec<_>>().await;
        assert!(events.iter().any(|event| matches!(
            event,
            crate::agent_types::AgentEvent::ToolExecutionUpdate { .. }
        )));
    }
}
