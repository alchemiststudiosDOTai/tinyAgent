#![cfg_attr(not(test), allow(dead_code))]

use crate::agent_types::{AgentTool, AgentToolResult, JsonObject, ToolUpdateCallback, UserContent};
use async_trait::async_trait;
use looper::tools::LooperTool;
use looper::types::{HandlerToLooperMessage, LooperToolDefinition};
use serde_json::{json, Value};
use tokio_util::sync::CancellationToken;

#[derive(Debug, Clone, PartialEq)]
pub(crate) enum SupportEvent {
    Assistant(String),
    Thinking(String),
    ThinkingComplete,
    ToolCallPending(String),
    ToolCallRequest {
        id: String,
        name: String,
        args: Value,
    },
    ToolCallComplete(String),
    TurnComplete,
}

pub(crate) fn bridge_handler_message(message: HandlerToLooperMessage) -> SupportEvent {
    match message {
        HandlerToLooperMessage::Assistant(text) => SupportEvent::Assistant(text),
        HandlerToLooperMessage::Thinking(text) => SupportEvent::Thinking(text),
        HandlerToLooperMessage::ThinkingComplete => SupportEvent::ThinkingComplete,
        HandlerToLooperMessage::ToolCallPending(id) => SupportEvent::ToolCallPending(id),
        HandlerToLooperMessage::ToolCallRequest(request) => SupportEvent::ToolCallRequest {
            id: request.id,
            name: request.name,
            args: request.args,
        },
        HandlerToLooperMessage::ToolCallComplete(id) => SupportEvent::ToolCallComplete(id),
        HandlerToLooperMessage::TurnComplete => SupportEvent::TurnComplete,
    }
}

pub(crate) fn looper_definition(tool: &AgentTool) -> LooperToolDefinition {
    LooperToolDefinition {
        name: tool.name.clone(),
        description: tool.description.clone(),
        parameters: tool.parameters.clone(),
    }
}

pub(crate) struct LooperToolAdapter {
    tool: AgentTool,
}

impl LooperToolAdapter {
    pub(crate) fn new(tool: AgentTool) -> Self {
        Self { tool }
    }
}

#[async_trait]
impl LooperTool for LooperToolAdapter {
    async fn execute(&mut self, args: &Value) -> Value {
        let normalized_args = match args {
            Value::Object(map) => map.clone(),
            _ => JsonObject::new(),
        };

        let on_update: ToolUpdateCallback = std::sync::Arc::new(|_partial: AgentToolResult| {});
        let result = self
            .tool
            .call(
                String::new(),
                normalized_args,
                CancellationToken::new(),
                on_update,
            )
            .await;

        match result {
            Ok(result) => tool_result_to_value(result),
            Err(error) => json!({
                "error": error.to_string(),
            }),
        }
    }

    fn tool(&self) -> LooperToolDefinition {
        looper_definition(&self.tool)
    }

    fn get_tool_name(&self) -> String {
        self.tool.name.clone()
    }
}

fn tool_result_to_value(result: AgentToolResult) -> Value {
    let content = result
        .content
        .into_iter()
        .filter_map(|item| match item {
            UserContent::Text(text) => Some(text.text),
            UserContent::Image(_) => None,
        })
        .collect::<Vec<_>>();

    json!({
        "content": content,
        "details": result.details,
    })
}

#[cfg(test)]
mod tests {
    use super::{bridge_handler_message, looper_definition, LooperToolAdapter, SupportEvent};
    use crate::agent_types::{AgentTool, AgentToolResult, TextContent, UserContent};
    use looper::tools::LooperTool;
    use looper::types::HandlerToLooperMessage;
    use serde_json::json;

    #[tokio::test]
    async fn looper_tool_adapter_registers_definition_and_executes() {
        let tool = AgentTool::new(
            "echo",
            "Echo input",
            json!({"type": "object"}),
            |_id, args, _abort, _on_update| async move {
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

        let definition = looper_definition(&tool);
        assert_eq!(definition.name, "echo");

        let mut adapter = LooperToolAdapter::new(tool);
        let value = adapter.execute(&json!({"value": "hello"})).await;
        assert_eq!(value["content"], json!(["hello"]));
        assert_eq!(adapter.tool().name, "echo");
    }

    #[test]
    fn bridge_moves_synthetic_handler_event_without_public_looper_types() {
        let bridged = bridge_handler_message(HandlerToLooperMessage::Thinking("step".to_string()));
        assert_eq!(bridged, SupportEvent::Thinking("step".to_string()));
    }
}
