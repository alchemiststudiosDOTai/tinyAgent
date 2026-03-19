use crate::agent_loop::{agent_loop, agent_loop_continue};
use crate::agent_options::{AgentLoopConfig, AgentOptions, MessageProvider};
use crate::agent_streaming::{
    agent_event_channel, text_channel, AgentEventStream, AgentTextStream,
};
use crate::agent_types::{
    current_timestamp, extract_text, AgentContext, AgentEvent, AgentMessage, AgentState,
    AssistantMessage, Model, QueueMode, StopReason, TextContent, UserContent, UserMessage,
};
use crate::error::{AgentError, Result};
use futures::future::BoxFuture;
use futures::StreamExt;
use std::sync::{Arc, Mutex};
use tokio::sync::{broadcast, Notify};
use tokio_util::sync::CancellationToken;

#[derive(Debug, Clone)]
pub enum PromptInput {
    Text(String),
    Message(AgentMessage),
    Messages(Vec<AgentMessage>),
}

impl From<&str> for PromptInput {
    fn from(value: &str) -> Self {
        Self::Text(value.to_string())
    }
}

impl From<String> for PromptInput {
    fn from(value: String) -> Self {
        Self::Text(value)
    }
}

impl From<AgentMessage> for PromptInput {
    fn from(value: AgentMessage) -> Self {
        Self::Message(value)
    }
}

impl From<Vec<AgentMessage>> for PromptInput {
    fn from(value: Vec<AgentMessage>) -> Self {
        Self::Messages(value)
    }
}

#[derive(Debug)]
struct AgentInner {
    state: AgentState,
    steering_queue: Vec<AgentMessage>,
    follow_up_queue: Vec<AgentMessage>,
    steering_mode: QueueMode,
    follow_up_mode: QueueMode,
    options: AgentOptions,
    abort: Option<CancellationToken>,
    run_notify: Option<Arc<Notify>>,
}

#[derive(Clone)]
pub struct Agent {
    inner: Arc<Mutex<AgentInner>>,
    subscribers: broadcast::Sender<AgentEvent>,
}

impl Default for Agent {
    fn default() -> Self {
        Self::new(AgentOptions::default())
    }
}

impl Agent {
    pub fn new(options: AgentOptions) -> Self {
        let state = options.initial_state();
        let (subscribers, _receiver) = broadcast::channel(256);

        Self {
            inner: Arc::new(Mutex::new(AgentInner {
                state,
                steering_queue: Vec::new(),
                follow_up_queue: Vec::new(),
                steering_mode: options.steering_mode.clone(),
                follow_up_mode: options.follow_up_mode.clone(),
                options,
                abort: None,
                run_notify: None,
            })),
            subscribers,
        }
    }

    pub fn state(&self) -> AgentState {
        self.inner
            .lock()
            .expect("agent lock poisoned")
            .state
            .clone()
    }

    pub fn subscribe(&self) -> broadcast::Receiver<AgentEvent> {
        self.subscribers.subscribe()
    }

    pub fn set_system_prompt(&self, value: impl Into<String>) {
        self.inner
            .lock()
            .expect("agent lock poisoned")
            .state
            .system_prompt = value.into();
    }

    pub fn set_model(&self, model: Model) {
        self.inner.lock().expect("agent lock poisoned").state.model = Some(model);
    }

    pub fn set_tools(&self, tools: Vec<crate::agent_types::AgentTool>) {
        self.inner.lock().expect("agent lock poisoned").state.tools = tools;
    }

    pub fn replace_messages(&self, messages: Vec<AgentMessage>) {
        self.inner
            .lock()
            .expect("agent lock poisoned")
            .state
            .messages = messages;
    }

    pub fn append_message(&self, message: AgentMessage) {
        self.inner
            .lock()
            .expect("agent lock poisoned")
            .state
            .messages
            .push(message);
    }

    pub fn steer(&self, message: AgentMessage) {
        self.inner
            .lock()
            .expect("agent lock poisoned")
            .steering_queue
            .push(message);
    }

    pub fn follow_up(&self, message: AgentMessage) {
        self.inner
            .lock()
            .expect("agent lock poisoned")
            .follow_up_queue
            .push(message);
    }

    pub fn clear_steering_queue(&self) {
        self.inner
            .lock()
            .expect("agent lock poisoned")
            .steering_queue
            .clear();
    }

    pub fn clear_follow_up_queue(&self) {
        self.inner
            .lock()
            .expect("agent lock poisoned")
            .follow_up_queue
            .clear();
    }

    pub fn clear_all_queues(&self) {
        let mut inner = self.inner.lock().expect("agent lock poisoned");
        inner.steering_queue.clear();
        inner.follow_up_queue.clear();
    }

    pub fn clear_messages(&self) {
        self.inner
            .lock()
            .expect("agent lock poisoned")
            .state
            .messages
            .clear();
    }

    pub fn reset(&self) {
        let mut inner = self.inner.lock().expect("agent lock poisoned");
        inner.state.messages.clear();
        inner.state.is_streaming = false;
        inner.state.stream_message = None;
        inner.state.pending_tool_calls.clear();
        inner.state.error = None;
        inner.steering_queue.clear();
        inner.follow_up_queue.clear();
    }

    pub fn abort(&self) {
        if let Some(token) = self
            .inner
            .lock()
            .expect("agent lock poisoned")
            .abort
            .clone()
        {
            token.cancel();
        }
    }

    pub async fn wait_for_idle(&self) {
        let notify = self
            .inner
            .lock()
            .expect("agent lock poisoned")
            .run_notify
            .clone();

        if let Some(notify) = notify {
            notify.notified().await;
        }
    }

    pub async fn prompt(&self, input: impl Into<PromptInput>) -> Result<AssistantMessage> {
        let stream = self.stream(input)?;
        let messages = stream.result().await?;
        find_last_assistant(&messages).ok_or_else(|| {
            AgentError::Internal("no assistant message produced by prompt".to_string())
        })
    }

    pub async fn prompt_text(&self, input: impl Into<PromptInput>) -> Result<String> {
        let message = self.prompt(input).await?;
        Ok(extract_text(&AgentMessage::Assistant(message)))
    }

    pub fn stream(&self, input: impl Into<PromptInput>) -> Result<AgentEventStream> {
        let prompts = normalize_input(input.into());
        self.start_prompt_stream(prompts)
    }

    pub fn stream_text(&self, input: impl Into<PromptInput>) -> Result<AgentTextStream> {
        let mut event_stream = self.stream(input)?;
        let (text_stream, text_tx) = text_channel();

        tokio::spawn(async move {
            while let Some(event) = event_stream.next().await {
                if let AgentEvent::MessageUpdate {
                    assistant_message_event:
                        Some(crate::agent_types::AssistantMessageEvent::TextDelta { delta, .. }),
                    ..
                } = event
                {
                    let _ = text_tx.send(delta);
                }
            }

            let _ = event_stream.result().await;
            drop(text_tx);
        });

        Ok(text_stream)
    }

    pub async fn continue_(&self) -> Result<AssistantMessage> {
        let stream = self.start_continue_stream()?;
        let messages = stream.result().await?;
        find_last_assistant(&messages).ok_or_else(|| {
            AgentError::Internal("no assistant message produced by continue_".to_string())
        })
    }

    fn start_prompt_stream(&self, prompts: Vec<AgentMessage>) -> Result<AgentEventStream> {
        let (context, config, abort, notify, model) = self.prepare_run()?;
        let low_level = agent_loop(prompts, context, config, Some(abort.clone()));
        self.wrap_low_level_stream(low_level, model, abort, notify)
    }

    fn start_continue_stream(&self) -> Result<AgentEventStream> {
        let (context, config, abort, notify, model) = self.prepare_run()?;
        let low_level = agent_loop_continue(context, config, Some(abort.clone()))?;
        self.wrap_low_level_stream(low_level, model, abort, notify)
    }

    fn prepare_run(
        &self,
    ) -> Result<(
        AgentContext,
        AgentLoopConfig,
        CancellationToken,
        Arc<Notify>,
        Model,
    )> {
        let mut inner = self.inner.lock().expect("agent lock poisoned");
        if inner.state.is_streaming {
            return Err(AgentError::AlreadyStreaming);
        }

        let model = inner
            .state
            .model
            .clone()
            .ok_or(AgentError::NoModelConfigured)?;
        let abort = CancellationToken::new();
        let notify = Arc::new(Notify::new());
        inner.abort = Some(abort.clone());
        inner.run_notify = Some(notify.clone());
        inner.state.is_streaming = true;
        inner.state.stream_message = None;
        inner.state.error = None;
        inner.state.pending_tool_calls.clear();

        let context = AgentContext {
            system_prompt: inner.state.system_prompt.clone(),
            messages: inner.state.messages.clone(),
            tools: inner.state.tools.clone(),
        };
        let config = AgentLoopConfig::from_options(
            model.clone(),
            &inner.options,
            Some(self.queue_reader(true)),
            Some(self.queue_reader(false)),
        );

        Ok((context, config, abort, notify, model))
    }

    fn queue_reader(&self, steering: bool) -> MessageProvider {
        let inner = Arc::clone(&self.inner);

        Arc::new(move || {
            let inner = Arc::clone(&inner);
            Box::pin(async move {
                let mut inner = inner.lock().expect("agent lock poisoned");
                let mode = if steering {
                    inner.steering_mode.clone()
                } else {
                    inner.follow_up_mode.clone()
                };
                let queue = if steering {
                    &mut inner.steering_queue
                } else {
                    &mut inner.follow_up_queue
                };

                match mode {
                    QueueMode::OneAtATime => {
                        if queue.is_empty() {
                            Vec::new()
                        } else {
                            vec![queue.remove(0)]
                        }
                    }
                    QueueMode::All => queue.drain(..).collect(),
                }
            }) as BoxFuture<'static, Vec<AgentMessage>>
        })
    }

    fn wrap_low_level_stream(
        &self,
        mut low_level: AgentEventStream,
        model: Model,
        abort: CancellationToken,
        notify: Arc<Notify>,
    ) -> Result<AgentEventStream> {
        let (stream, event_tx, result_tx) = agent_event_channel();
        let inner = Arc::clone(&self.inner);
        let subscribers = self.subscribers.clone();

        tokio::spawn(async move {
            while let Some(event) = low_level.next().await {
                {
                    let mut inner = inner.lock().expect("agent lock poisoned");
                    handle_agent_event(&mut inner.state, &event);
                }
                let _ = subscribers.send(event.clone());
                let _ = event_tx.send(event);
            }

            let result = low_level.result().await;
            let final_result = match result {
                Ok(messages) => Ok(messages),
                Err(error) => {
                    let error_message = create_error_message(&model, &error, abort.is_cancelled());
                    {
                        let mut inner = inner.lock().expect("agent lock poisoned");
                        inner
                            .state
                            .messages
                            .push(AgentMessage::Assistant(error_message.clone()));
                        inner.state.error = Some(error.to_string());
                    }

                    let end_event = AgentEvent::AgentEnd {
                        messages: vec![AgentMessage::Assistant(error_message.clone())],
                    };
                    let _ = subscribers.send(end_event.clone());
                    let _ = event_tx.send(end_event);
                    Ok(vec![AgentMessage::Assistant(error_message)])
                }
            };

            {
                let mut inner = inner.lock().expect("agent lock poisoned");
                inner.state.is_streaming = false;
                inner.state.stream_message = None;
                inner.abort = None;
                inner.run_notify = None;
            }
            notify.notify_waiters();

            let _ = result_tx.send(final_result);
            drop(event_tx);
        });

        Ok(stream)
    }
}

fn normalize_input(input: PromptInput) -> Vec<AgentMessage> {
    match input {
        PromptInput::Text(text) => vec![AgentMessage::User(UserMessage {
            content: vec![UserContent::Text(TextContent::new(text))],
            timestamp: Some(current_timestamp()),
            ..UserMessage::default()
        })],
        PromptInput::Message(message) => vec![message],
        PromptInput::Messages(messages) => messages,
    }
}

fn create_error_message(model: &Model, error: &AgentError, aborted: bool) -> AssistantMessage {
    AssistantMessage {
        content: vec![Some(crate::agent_types::AssistantContent::Text(
            TextContent::new(String::new()),
        ))],
        stop_reason: Some(if aborted {
            StopReason::Aborted
        } else {
            StopReason::Error
        }),
        api: Some(model.api.clone()),
        provider: Some(model.provider.clone()),
        model: Some(model.id.clone()),
        error_message: Some(error.to_string()),
        timestamp: Some(current_timestamp()),
        ..AssistantMessage::default()
    }
}

fn find_last_assistant(messages: &[AgentMessage]) -> Option<AssistantMessage> {
    messages.iter().rev().find_map(|message| match message {
        AgentMessage::Assistant(message) => Some(message.clone()),
        _ => None,
    })
}

fn handle_agent_event(state: &mut AgentState, event: &AgentEvent) {
    match event {
        AgentEvent::MessageStart { message } | AgentEvent::MessageUpdate { message, .. } => {
            state.stream_message = message.clone();
        }
        AgentEvent::MessageEnd { message } => {
            state.stream_message = None;
            if let Some(message) = message {
                state.messages.push(message.clone());
            }
        }
        AgentEvent::ToolExecutionStart { tool_call_id, .. } => {
            state.pending_tool_calls.insert(tool_call_id.clone());
        }
        AgentEvent::ToolExecutionEnd { tool_call_id, .. } => {
            state.pending_tool_calls.remove(tool_call_id);
        }
        AgentEvent::TurnEnd { message, .. } => {
            if let Some(AgentMessage::Assistant(message)) = message {
                if let Some(error) = &message.error_message {
                    state.error = Some(error.clone());
                }
            }
        }
        AgentEvent::AgentEnd { .. } => {
            state.is_streaming = false;
            state.stream_message = None;
        }
        AgentEvent::AgentStart | AgentEvent::TurnStart | AgentEvent::ToolExecutionUpdate { .. } => {
        }
    }
}
