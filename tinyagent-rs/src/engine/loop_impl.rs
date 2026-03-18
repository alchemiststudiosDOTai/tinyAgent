use std::sync::Arc;

use anyhow::Result;
use serde_json::Value;
use tokio::sync::Mutex;

use crate::{
    providers::ProviderAdapter,
    tools::{ToolExecutor, ToolRegistry},
    types::{
        AgentContext, AgentEvent, AgentLoopConfig, AgentMessage, AgentRunResult, EventEmitter,
    },
};

use super::stream_assistant::stream_assistant_response;

pub async fn run_loop(
    provider: Arc<Mutex<Box<dyn ProviderAdapter>>>,
    tools: ToolRegistry,
    config: AgentLoopConfig,
    system_prompt: String,
    existing_messages: Vec<AgentMessage>,
    initial_messages: Vec<AgentMessage>,
    provider_state: Option<Value>,
    emitter: EventEmitter<AgentEvent, AgentRunResult>,
) -> Result<AgentRunResult> {
    let tool_definitions = tools.definitions().await;
    let mut current_context = AgentContext {
        system_prompt,
        messages: existing_messages,
        tools: tool_definitions.clone(),
    };
    let mut new_messages = Vec::new();
    let mut continuation = provider_state;
    let tool_executor = ToolExecutor::new(tools);

    emitter.push(AgentEvent::AgentStart)?;
    emitter.push(AgentEvent::TurnStart)?;

    emit_pending_messages(
        &initial_messages,
        &mut current_context,
        &mut new_messages,
        &emitter,
    )?;

    loop {
        let assistant = stream_assistant_response(
            provider.clone(),
            current_context.clone(),
            tool_definitions.clone(),
            config.clone(),
            continuation.clone(),
            &emitter,
        )
        .await?;

        continuation = assistant.continuation;
        current_context
            .messages
            .push(AgentMessage::Assistant(assistant.message.clone()));
        new_messages.push(AgentMessage::Assistant(assistant.message.clone()));

        let tool_results = tool_executor
            .execute_calls(&assistant.message, &emitter)
            .await;

        for tool_result in &tool_results {
            current_context
                .messages
                .push(AgentMessage::ToolResult(tool_result.clone()));
            new_messages.push(AgentMessage::ToolResult(tool_result.clone()));
        }

        emitter.push(AgentEvent::TurnEnd {
            message: Some(assistant.message.clone()),
            tool_results: tool_results.clone(),
        })?;

        if tool_results.is_empty() {
            break;
        }

        emitter.push(AgentEvent::TurnStart)?;
    }

    let final_text = new_messages.iter().rev().find_map(|message| match message {
        AgentMessage::Assistant(assistant) => {
            let text = assistant.text();
            if text.is_empty() { None } else { Some(text) }
        }
        _ => None,
    });

    emitter.push(AgentEvent::AgentEnd {
        messages: new_messages.clone(),
    })?;

    Ok(AgentRunResult {
        messages: new_messages,
        final_text,
        provider_state: continuation,
    })
}

fn emit_pending_messages(
    messages: &[AgentMessage],
    current_context: &mut AgentContext,
    new_messages: &mut Vec<AgentMessage>,
    emitter: &EventEmitter<AgentEvent, AgentRunResult>,
) -> Result<()> {
    for message in messages {
        emitter.push(AgentEvent::MessageStart {
            message: message.clone(),
        })?;
        emitter.push(AgentEvent::MessageEnd {
            message: message.clone(),
        })?;
        current_context.messages.push(message.clone());
        new_messages.push(message.clone());
    }

    Ok(())
}
