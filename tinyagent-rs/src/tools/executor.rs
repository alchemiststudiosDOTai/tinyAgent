use std::sync::Arc;

use futures::future::join_all;

use crate::{
    tools::registry::ToolRegistry,
    types::{
        AgentEvent, AgentRunResult, AssistantMessage, EventEmitter, ToolCallContent,
        ToolExecutionContext, ToolOutput, ToolResultMessage,
    },
};

pub struct ToolExecutor {
    registry: ToolRegistry,
}

impl ToolExecutor {
    pub fn new(registry: ToolRegistry) -> Self {
        Self { registry }
    }

    pub async fn execute_calls(
        &self,
        assistant_message: &AssistantMessage,
        emitter: &EventEmitter<AgentEvent, AgentRunResult>,
    ) -> Vec<ToolResultMessage> {
        let tool_calls = assistant_message.tool_calls();
        if tool_calls.is_empty() {
            return Vec::new();
        }

        for tool_call in &tool_calls {
            let _ = emitter.push(AgentEvent::ToolExecutionStart {
                tool_call_id: tool_call.id.clone(),
                tool_name: tool_call.name.clone(),
                args: tool_call.arguments.clone(),
            });
        }

        let tasks = tool_calls.iter().cloned().map(|tool_call| {
            let registry = self.registry.clone();
            let emitter = emitter.clone();
            async move { execute_single_tool_call(registry, tool_call, emitter).await }
        });

        let outcomes = join_all(tasks).await;
        let mut results = Vec::with_capacity(outcomes.len());

        for (tool_call, (output, is_error)) in tool_calls.into_iter().zip(outcomes.into_iter()) {
            let _ = emitter.push(AgentEvent::ToolExecutionEnd {
                tool_call_id: tool_call.id.clone(),
                tool_name: tool_call.name.clone(),
                result: output.clone(),
                is_error,
            });

            let result_message = ToolResultMessage::from_output(&tool_call, output, is_error);
            let _ = emitter.push(AgentEvent::MessageStart {
                message: crate::types::AgentMessage::ToolResult(result_message.clone()),
            });
            let _ = emitter.push(AgentEvent::MessageEnd {
                message: crate::types::AgentMessage::ToolResult(result_message.clone()),
            });
            results.push(result_message);
        }

        results
    }
}

async fn execute_single_tool_call(
    registry: ToolRegistry,
    tool_call: ToolCallContent,
    emitter: EventEmitter<AgentEvent, AgentRunResult>,
) -> (ToolOutput, bool) {
    let Some(tool) = registry.get(&tool_call.name).await else {
        return (
            ToolOutput::from_text(format!("Tool {} not found", tool_call.name)),
            true,
        );
    };

    let tool_name = tool_call.name.clone();
    let tool_call_id = tool_call.id.clone();
    let args = tool_call.arguments.clone();
    let update_emitter = emitter.clone();

    let on_update = Arc::new(move |partial_result: ToolOutput| {
        let _ = update_emitter.push(AgentEvent::ToolExecutionUpdate {
            tool_call_id: tool_call_id.clone(),
            tool_name: tool_name.clone(),
            args: args.clone(),
            partial_result,
        });
    });

    match tool
        .execute(
            ToolExecutionContext {
                tool_call_id: tool_call.id,
            },
            tool_call.arguments,
            on_update,
        )
        .await
    {
        Ok(output) => (output, false),
        Err(error) => (ToolOutput::from_text(error.to_string()), true),
    }
}
