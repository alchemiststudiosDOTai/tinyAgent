use std::error::Error;
use std::fmt;
use std::sync::Arc;

use tokio::sync::Notify;

use crate::agent_tool_execution::{ToolExecutionError, execute_tool_calls};
use crate::types::{
    AgentContext, AgentEndEvent, AgentEvent, AgentLoopConfig, AgentMessage, AgentMessageProvider,
    AgentStartEvent, AssistantMessage, AssistantMessageEventType, Context,
    EventStream, Message, MessageEndEvent, MessageStartEvent, MessageUpdateEvent,
    SimpleStreamOptions, StopReason, StreamFn, TurnEndEvent, TurnStartEvent,
    event_stream_error, is_agent_end_event,
};

pub type AgentEventStream = Arc<EventStream>;
pub type AgentLoopResult<T> = Result<T, AgentLoopError>;

#[derive(Debug)]
pub enum AgentLoopError {
    MissingStreamFn,
    CannotContinueWithoutMessages,
    CannotContinueFromAssistant,
    MissingAssistantEventPartial(AssistantMessageEventType),
    AssistantUpdateBeforeStart(AssistantMessageEventType),
    ToolExecution(ToolExecutionError),
}

impl fmt::Display for AgentLoopError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingStreamFn => f.write_str("agent loop requires a stream function"),
            Self::CannotContinueWithoutMessages => {
                f.write_str("cannot continue agent loop without context messages")
            }
            Self::CannotContinueFromAssistant => {
                f.write_str("cannot continue agent loop from an assistant message")
            }
            Self::MissingAssistantEventPartial(event_type) => {
                write!(
                    f,
                    "assistant stream event '{event_type:?}' arrived without a partial message"
                )
            }
            Self::AssistantUpdateBeforeStart(event_type) => {
                write!(
                    f,
                    "assistant stream event '{event_type:?}' arrived before a start event"
                )
            }
            Self::ToolExecution(error) => write!(f, "{error}"),
        }
    }
}

impl Error for AgentLoopError {}

impl From<ToolExecutionError> for AgentLoopError {
    fn from(value: ToolExecutionError) -> Self {
        Self::ToolExecution(value)
    }
}

#[derive(Debug, Clone, Default)]
struct ResponseStreamState {
    added_partial: bool,
}

#[derive(Debug, Clone)]
struct TurnProcessingResult {
    pending_messages: Vec<AgentMessage>,
    has_more_tool_calls: bool,
    first_turn: bool,
    should_continue: bool,
}

pub fn create_agent_stream() -> AgentEventStream {
    Arc::new(EventStream::new(is_agent_end_event, |event| match event {
        AgentEvent::AgentEnd(agent_end) => agent_end.messages.clone(),
        _ => Vec::new(),
    }))
}

pub async fn build_llm_context(
    context: AgentContext,
    config: &AgentLoopConfig,
    signal: Option<Arc<Notify>>,
) -> Context {
    let messages = match &config.transform_context {
        Some(transform_context) => transform_context(context.messages, signal).await,
        None => context.messages,
    };

    let llm_messages = (config.convert_to_llm)(messages).resolve().await;

    Context {
        system_prompt: context.system_prompt,
        messages: llm_messages,
        tools: context.tools,
    }
}

pub async fn resolve_api_key(config: &AgentLoopConfig) -> Option<String> {
    if let Some(get_api_key) = &config.get_api_key {
        let resolved = get_api_key(config.model.provider.clone()).resolve().await;
        if resolved.is_some() {
            return resolved;
        }
    }

    config.api_key.clone()
}

pub async fn stream_assistant_response(
    context: &mut AgentContext,
    config: &AgentLoopConfig,
    signal: Option<Arc<Notify>>,
    stream: &AgentEventStream,
    stream_fn: Option<StreamFn>,
) -> AgentLoopResult<AssistantMessage> {
    let llm_context = build_llm_context(context.clone(), config, signal.clone()).await;
    let resolved_api_key = resolve_api_key(config).await;
    let options = SimpleStreamOptions {
        api_key: resolved_api_key,
        temperature: config.temperature,
        max_tokens: config.max_tokens,
        signal,
    };

    let stream_function = stream_fn.ok_or(AgentLoopError::MissingStreamFn)?;
    let mut response = stream_function(config.model.clone(), llm_context, options).await;
    let mut state = ResponseStreamState::default();

    while let Some(event) = response.next_event().await {
        let Some(event_type) = event.event_type else {
            continue;
        };

        match event_type {
            AssistantMessageEventType::Start => {
                let partial_message = event
                    .partial
                    .clone()
                    .ok_or(AgentLoopError::MissingAssistantEventPartial(event_type))?;
                let partial_agent_message =
                    AgentMessage::Message(Message::Assistant(partial_message.clone()));

                context.messages.push(partial_agent_message.clone());
                state.added_partial = true;

                stream.push(AgentEvent::MessageStart(MessageStartEvent {
                    message: Some(partial_agent_message),
                    ..Default::default()
                }));
            }
            AssistantMessageEventType::Done | AssistantMessageEventType::Error => {
                let final_message = response.result().await;
                let final_agent_message =
                    AgentMessage::Message(Message::Assistant(final_message.clone()));

                if state.added_partial {
                    if let Some(last_message) = context.messages.last_mut() {
                        *last_message = final_agent_message.clone();
                    }
                } else {
                    context.messages.push(final_agent_message.clone());
                    stream.push(AgentEvent::MessageStart(MessageStartEvent {
                        message: Some(final_agent_message.clone()),
                        ..Default::default()
                    }));
                }

                stream.push(AgentEvent::MessageEnd(MessageEndEvent {
                    message: Some(final_agent_message),
                    ..Default::default()
                }));

                return Ok(final_message);
            }
            _ => {
                if !state.added_partial {
                    return Err(AgentLoopError::AssistantUpdateBeforeStart(event_type));
                }

                let partial_message = event
                    .partial
                    .clone()
                    .ok_or(AgentLoopError::MissingAssistantEventPartial(event_type))?;
                let partial_agent_message =
                    AgentMessage::Message(Message::Assistant(partial_message.clone()));

                if let Some(last_message) = context.messages.last_mut() {
                    *last_message = partial_agent_message.clone();
                }

                stream.push(AgentEvent::MessageUpdate(MessageUpdateEvent {
                    message: Some(partial_agent_message),
                    assistant_message_event: Some(event),
                    ..Default::default()
                }));
            }
        }
    }

    Ok(response.result().await)
}

pub async fn run_loop(
    current_context: &mut AgentContext,
    new_messages: &mut Vec<AgentMessage>,
    config: &AgentLoopConfig,
    signal: Option<Arc<Notify>>,
    stream: &AgentEventStream,
    stream_fn: Option<StreamFn>,
) -> AgentLoopResult<()> {
    let mut first_turn = true;
    let get_steering_fn = config.get_steering_messages.clone();
    let mut pending_messages = take_messages(get_steering_fn.as_ref()).await;

    loop {
        let mut has_more_tool_calls = true;

        while has_more_tool_calls || !pending_messages.is_empty() {
            let turn_result = process_turn(
                current_context,
                new_messages,
                pending_messages,
                config,
                signal.clone(),
                stream,
                first_turn,
                stream_fn.clone(),
                get_steering_fn.clone(),
            )
            .await?;

            if !turn_result.should_continue {
                return Ok(());
            }

            pending_messages = turn_result.pending_messages;
            has_more_tool_calls = turn_result.has_more_tool_calls;
            first_turn = turn_result.first_turn;
        }

        let follow_up_messages = take_messages(config.get_follow_up_messages.as_ref()).await;
        if follow_up_messages.is_empty() {
            break;
        }

        pending_messages = follow_up_messages;
    }

    stream.push(AgentEvent::AgentEnd(AgentEndEvent {
        messages: new_messages.clone(),
        ..Default::default()
    }));
    stream.end(new_messages.clone());

    Ok(())
}

pub fn agent_loop(
    prompts: Vec<AgentMessage>,
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Option<Arc<Notify>>,
    stream_fn: Option<StreamFn>,
) -> AgentEventStream {
    let stream = create_agent_stream();
    let run_stream = Arc::clone(&stream);

    let task = tokio::spawn(async move {
        let mut new_messages = prompts.clone();
        let mut messages = context.messages;
        messages.extend(prompts.iter().cloned());

        let mut current_context = AgentContext {
            system_prompt: context.system_prompt,
            messages,
            tools: context.tools,
        };

        run_stream.push(AgentEvent::AgentStart(AgentStartEvent::default()));
        run_stream.push(AgentEvent::TurnStart(TurnStartEvent::default()));

        for prompt in prompts {
            run_stream.push(AgentEvent::MessageStart(MessageStartEvent {
                message: Some(prompt.clone()),
                ..Default::default()
            }));
            run_stream.push(AgentEvent::MessageEnd(MessageEndEvent {
                message: Some(prompt),
                ..Default::default()
            }));
        }

        run_loop(
            &mut current_context,
            &mut new_messages,
            &config,
            signal,
            &run_stream,
            stream_fn,
        )
        .await
    });

    spawn_join_reporter(task, Arc::clone(&stream));
    stream
}

pub fn agent_loop_continue(
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Option<Arc<Notify>>,
    stream_fn: Option<StreamFn>,
) -> AgentLoopResult<AgentEventStream> {
    let Some(last_message) = context.messages.last() else {
        return Err(AgentLoopError::CannotContinueWithoutMessages);
    };

    if matches!(last_message, AgentMessage::Message(Message::Assistant(_))) {
        return Err(AgentLoopError::CannotContinueFromAssistant);
    }

    let stream = create_agent_stream();
    let run_stream = Arc::clone(&stream);

    let task = tokio::spawn(async move {
        let mut new_messages = Vec::new();
        let mut current_context = context;

        run_stream.push(AgentEvent::AgentStart(AgentStartEvent::default()));
        run_stream.push(AgentEvent::TurnStart(TurnStartEvent::default()));

        run_loop(
            &mut current_context,
            &mut new_messages,
            &config,
            signal,
            &run_stream,
            stream_fn,
        )
        .await
    });

    spawn_join_reporter(task, Arc::clone(&stream));
    Ok(stream)
}

async fn process_turn(
    current_context: &mut AgentContext,
    new_messages: &mut Vec<AgentMessage>,
    pending_messages: Vec<AgentMessage>,
    config: &AgentLoopConfig,
    signal: Option<Arc<Notify>>,
    stream: &AgentEventStream,
    first_turn: bool,
    stream_fn: Option<StreamFn>,
    get_steering_fn: Option<AgentMessageProvider>,
) -> AgentLoopResult<TurnProcessingResult> {
    let mut first_turn = first_turn;
    if first_turn {
        first_turn = false;
    } else {
        stream.push(AgentEvent::TurnStart(TurnStartEvent::default()));
    }

    emit_pending_messages(pending_messages, current_context, new_messages, stream);

    let message = stream_assistant_response(
        current_context,
        config,
        signal.clone(),
        stream,
        stream_fn,
    )
    .await?;
    let agent_message = AgentMessage::Message(Message::Assistant(message.clone()));
    new_messages.push(agent_message.clone());

    if matches!(message.stop_reason, Some(StopReason::Error | StopReason::Aborted)) {
        stream.push(AgentEvent::TurnEnd(TurnEndEvent {
            message: Some(agent_message),
            tool_results: Vec::new(),
            ..Default::default()
        }));
        stream.push(AgentEvent::AgentEnd(AgentEndEvent {
            messages: new_messages.clone(),
            ..Default::default()
        }));
        stream.end(new_messages.clone());

        return Ok(TurnProcessingResult {
            pending_messages: Vec::new(),
            has_more_tool_calls: false,
            first_turn,
            should_continue: false,
        });
    }

    let tool_execution = execute_tool_calls(
        current_context.tools.as_deref(),
        &message,
        signal,
        stream,
        get_steering_fn.clone(),
    )
    .await?;

    let tool_results = tool_execution.tool_results;
    let has_more_tool_calls = !tool_results.is_empty();
    let steering_after_tools = tool_execution.steering_messages.unwrap_or_default();

    for result in tool_results.iter().cloned() {
        let tool_result_message = AgentMessage::Message(Message::ToolResult(result.clone()));
        current_context.messages.push(tool_result_message.clone());
        new_messages.push(tool_result_message);
    }

    stream.push(AgentEvent::TurnEnd(TurnEndEvent {
        message: Some(agent_message),
        tool_results: tool_results.clone(),
        ..Default::default()
    }));

    Ok(TurnProcessingResult {
        pending_messages: if has_more_tool_calls {
            steering_after_tools
        } else {
            take_messages(get_steering_fn.as_ref()).await
        },
        has_more_tool_calls,
        first_turn,
        should_continue: true,
    })
}

fn emit_pending_messages(
    pending_messages: Vec<AgentMessage>,
    current_context: &mut AgentContext,
    new_messages: &mut Vec<AgentMessage>,
    stream: &AgentEventStream,
) {
    for message in pending_messages {
        stream.push(AgentEvent::MessageStart(MessageStartEvent {
            message: Some(message.clone()),
            ..Default::default()
        }));
        stream.push(AgentEvent::MessageEnd(MessageEndEvent {
            message: Some(message.clone()),
            ..Default::default()
        }));
        current_context.messages.push(message.clone());
        new_messages.push(message);
    }
}

async fn take_messages(provider: Option<&AgentMessageProvider>) -> Vec<AgentMessage> {
    match provider {
        Some(provider) => provider().await,
        None => Vec::new(),
    }
}

fn spawn_join_reporter(
    task: tokio::task::JoinHandle<AgentLoopResult<()>>,
    stream: AgentEventStream,
) {
    tokio::spawn(async move {
        match task.await {
            Ok(Ok(())) => {}
            Ok(Err(error)) => stream.set_exception(event_stream_error(error.to_string())),
            Err(join_error) => stream.set_exception(event_stream_error(join_error.to_string())),
        }
    });
}
