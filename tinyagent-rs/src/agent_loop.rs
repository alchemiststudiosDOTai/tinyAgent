use crate::agent_options::{AgentLoopConfig, MessageProvider};
use crate::agent_streaming::{
    agent_event_channel, stream_assistant_response, AgentEventStream, AgentEventTx,
};
use crate::agent_tool_execution::execute_tool_calls;
use crate::agent_types::{AgentContext, AgentEvent, AgentMessage, StopReason};
use crate::error::{AgentError, Result};
use tokio_util::sync::CancellationToken;

pub fn agent_loop(
    prompts: Vec<AgentMessage>,
    context: AgentContext,
    config: AgentLoopConfig,
    abort: Option<CancellationToken>,
) -> AgentEventStream {
    let (stream, event_tx, result_tx) = agent_event_channel();
    let abort = abort.unwrap_or_default();

    tokio::spawn(async move {
        let _ = event_tx.send(AgentEvent::AgentStart);
        let _ = event_tx.send(AgentEvent::TurnStart);

        let mut current_context = AgentContext {
            system_prompt: context.system_prompt,
            messages: context.messages,
            tools: context.tools,
        };

        let mut new_messages = Vec::with_capacity(prompts.len());
        for prompt in prompts {
            let _ = event_tx.send(AgentEvent::MessageStart {
                message: Some(prompt.clone()),
            });
            let _ = event_tx.send(AgentEvent::MessageEnd {
                message: Some(prompt.clone()),
            });
            current_context.messages.push(prompt.clone());
            new_messages.push(prompt);
        }

        let result = run_loop(current_context, new_messages, config, abort, &event_tx).await;
        if let Ok(messages) = &result {
            let _ = event_tx.send(AgentEvent::AgentEnd {
                messages: messages.clone(),
            });
        }

        let _ = result_tx.send(result);
        drop(event_tx);
    });

    stream
}

pub fn agent_loop_continue(
    context: AgentContext,
    config: AgentLoopConfig,
    abort: Option<CancellationToken>,
) -> Result<AgentEventStream> {
    if context.messages.is_empty() {
        return Err(AgentError::CannotContinueWithoutMessages);
    }
    if matches!(context.messages.last(), Some(message) if message.role() == "assistant") {
        return Err(AgentError::CannotContinueFromAssistant);
    }

    let (stream, event_tx, result_tx) = agent_event_channel();
    let abort = abort.unwrap_or_default();

    tokio::spawn(async move {
        let _ = event_tx.send(AgentEvent::AgentStart);
        let _ = event_tx.send(AgentEvent::TurnStart);

        let result = run_loop(context, Vec::new(), config, abort, &event_tx).await;
        if let Ok(messages) = &result {
            let _ = event_tx.send(AgentEvent::AgentEnd {
                messages: messages.clone(),
            });
        }

        let _ = result_tx.send(result);
        drop(event_tx);
    });

    Ok(stream)
}

async fn run_loop(
    mut current_context: AgentContext,
    mut new_messages: Vec<AgentMessage>,
    config: AgentLoopConfig,
    abort: CancellationToken,
    event_tx: &AgentEventTx,
) -> Result<Vec<AgentMessage>> {
    let mut first_turn = true;
    let mut turns = 0usize;
    let mut pending_messages = poll_messages(config.get_steering_messages.as_ref()).await;

    loop {
        let mut has_more_tool_calls = true;

        while has_more_tool_calls || !pending_messages.is_empty() {
            if abort.is_cancelled() {
                return Err(AgentError::Aborted);
            }
            if turns >= config.max_turns {
                return Err(AgentError::MaxTurnsExceeded {
                    max_turns: config.max_turns,
                });
            }

            if first_turn {
                first_turn = false;
            } else {
                let _ = event_tx.send(AgentEvent::TurnStart);
            }

            emit_pending_messages(
                &mut current_context,
                &mut new_messages,
                &mut pending_messages,
                event_tx,
            );

            turns += 1;
            let assistant =
                stream_assistant_response(&mut current_context, &config, abort.clone(), event_tx)
                    .await?;
            let assistant_message = AgentMessage::Assistant(assistant.clone());
            new_messages.push(assistant_message.clone());

            if matches!(
                assistant.stop_reason,
                Some(StopReason::Error) | Some(StopReason::Aborted)
            ) {
                let _ = event_tx.send(AgentEvent::TurnEnd {
                    message: Some(assistant_message),
                    tool_results: Vec::new(),
                });
                return Ok(new_messages);
            }

            let tool_execution = execute_tool_calls(
                &current_context.tools,
                &assistant,
                abort.clone(),
                event_tx,
                config.get_steering_messages.clone(),
            )
            .await?;

            has_more_tool_calls = !tool_execution.tool_results.is_empty();
            for tool_result in &tool_execution.tool_results {
                current_context
                    .messages
                    .push(AgentMessage::ToolResult(tool_result.clone()));
                new_messages.push(AgentMessage::ToolResult(tool_result.clone()));
            }

            let _ = event_tx.send(AgentEvent::TurnEnd {
                message: Some(assistant_message),
                tool_results: tool_execution.tool_results.clone(),
            });

            pending_messages = if has_more_tool_calls {
                tool_execution.steering_messages.unwrap_or_default()
            } else {
                poll_messages(config.get_steering_messages.as_ref()).await
            };
        }

        let follow_up_messages = poll_messages(config.get_follow_up_messages.as_ref()).await;
        if follow_up_messages.is_empty() {
            break;
        }

        pending_messages = follow_up_messages;
    }

    Ok(new_messages)
}

fn emit_pending_messages(
    current_context: &mut AgentContext,
    new_messages: &mut Vec<AgentMessage>,
    pending_messages: &mut Vec<AgentMessage>,
    event_tx: &AgentEventTx,
) {
    let messages = std::mem::take(pending_messages);
    for message in messages {
        let _ = event_tx.send(AgentEvent::MessageStart {
            message: Some(message.clone()),
        });
        let _ = event_tx.send(AgentEvent::MessageEnd {
            message: Some(message.clone()),
        });
        current_context.messages.push(message.clone());
        new_messages.push(message);
    }
}

async fn poll_messages(provider: Option<&MessageProvider>) -> Vec<AgentMessage> {
    match provider {
        Some(provider) => provider().await,
        None => Vec::new(),
    }
}
