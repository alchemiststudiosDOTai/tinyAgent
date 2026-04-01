use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use tokio::sync::Notify;

use crate::agent_loop::{AgentEventStream, agent_loop, agent_loop_continue};
use crate::types::{
    AgentContext, AgentEvent, AgentLoopConfig, AgentMessage, AgentMessageProvider, AgentState,
    AgentTool, ApiKeyResolver, AssistantContent, AssistantMessage, Context, ConvertToLlmFn,
    ImageContent, MaybeAwaitable, Message, MessageEndEvent, MessageStartEvent, Model,
    SimpleStreamOptions, StopReason, StreamFn, TextContent, ThinkingBudgets, ThinkingContent,
    ThinkingLevel, ToolExecutionEndEvent, ToolExecutionStartEvent, TransformContextFn, UserContent,
    UserMessage, zero_usage,
};

pub type AgentListener = Arc<dyn Fn(&AgentEvent) + Send + Sync>;
pub type AgentRunResult<T> = Result<T, AgentRunError>;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AgentRunError {
    MissingModel,
    MissingStreamFn,
    Loop(String),
    Stream(String),
    MissingAssistantResponse,
}

impl std::fmt::Display for AgentRunError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::MissingModel => f.write_str("agent is missing a model"),
            Self::MissingStreamFn => f.write_str("agent is missing a stream backend"),
            Self::Loop(message) => f.write_str(message),
            Self::Stream(message) => f.write_str(message),
            Self::MissingAssistantResponse => {
                f.write_str("agent run completed without an assistant response")
            }
        }
    }
}

impl std::error::Error for AgentRunError {}

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum QueueMode {
    All,
    #[default]
    OneAtATime,
}

impl QueueMode {
    fn drain<T>(&self, queue: &mut Vec<T>) -> Vec<T> {
        match self {
            Self::All => std::mem::take(queue),
            Self::OneAtATime => {
                if queue.is_empty() {
                    Vec::new()
                } else {
                    vec![queue.remove(0)]
                }
            }
        }
    }
}

#[derive(Debug, Clone)]
pub enum AgentInput {
    Text(String),
    Message(AgentMessage),
    Messages(Vec<AgentMessage>),
}

impl From<String> for AgentInput {
    fn from(value: String) -> Self {
        Self::Text(value)
    }
}

impl From<&str> for AgentInput {
    fn from(value: &str) -> Self {
        Self::Text(value.to_string())
    }
}

impl From<AgentMessage> for AgentInput {
    fn from(value: AgentMessage) -> Self {
        Self::Message(value)
    }
}

impl From<Message> for AgentInput {
    fn from(value: Message) -> Self {
        Self::Message(AgentMessage::Message(value))
    }
}

impl From<Vec<AgentMessage>> for AgentInput {
    fn from(value: Vec<AgentMessage>) -> Self {
        Self::Messages(value)
    }
}

#[derive(Clone, Default)]
pub struct AgentOptions {
    pub initial_state: Option<AgentState>,
    pub convert_to_llm: Option<ConvertToLlmFn>,
    pub transform_context: Option<TransformContextFn>,
    pub steering_mode: QueueMode,
    pub follow_up_mode: QueueMode,
    pub stream_fn: Option<StreamFn>,
    pub session_id: Option<String>,
    pub get_api_key: Option<ApiKeyResolver>,
    pub thinking_budgets: Option<ThinkingBudgets>,
    pub enable_prompt_caching: bool,
}

impl std::fmt::Debug for AgentOptions {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("AgentOptions")
            .field("initial_state", &self.initial_state)
            .field(
                "convert_to_llm",
                &self.convert_to_llm.as_ref().map(|_| "<callback>"),
            )
            .field(
                "transform_context",
                &self.transform_context.as_ref().map(|_| "<callback>"),
            )
            .field("steering_mode", &self.steering_mode)
            .field("follow_up_mode", &self.follow_up_mode)
            .field("stream_fn", &self.stream_fn.as_ref().map(|_| "<callback>"))
            .field("session_id", &self.session_id)
            .field(
                "get_api_key",
                &self.get_api_key.as_ref().map(|_| "<callback>"),
            )
            .field("thinking_budgets", &self.thinking_budgets)
            .field("enable_prompt_caching", &self.enable_prompt_caching)
            .finish()
    }
}

#[derive(Debug, Clone)]
pub struct AbortHandle {
    signal: Arc<Notify>,
    aborted: Arc<AtomicBool>,
}

impl Default for AbortHandle {
    fn default() -> Self {
        Self::new()
    }
}

impl AbortHandle {
    pub fn new() -> Self {
        Self {
            signal: Arc::new(Notify::new()),
            aborted: Arc::new(AtomicBool::new(false)),
        }
    }

    pub fn abort(&self) {
        self.aborted.store(true, Ordering::SeqCst);
        self.signal.notify_waiters();
    }

    pub fn is_aborted(&self) -> bool {
        self.aborted.load(Ordering::SeqCst)
    }

    pub fn signal(&self) -> Arc<Notify> {
        Arc::clone(&self.signal)
    }
}

pub struct Agent {
    state: AgentState,
    listeners: HashMap<u64, AgentListener>,
    next_listener_id: u64,
    abort_handle: Option<AbortHandle>,
    convert_to_llm: ConvertToLlmFn,
    transform_context: Option<TransformContextFn>,
    steering_queue: Vec<AgentMessage>,
    follow_up_queue: Vec<AgentMessage>,
    steering_mode: QueueMode,
    follow_up_mode: QueueMode,
    stream_fn: Option<StreamFn>,
    session_id: Option<String>,
    get_api_key: Option<ApiKeyResolver>,
    thinking_budgets: Option<ThinkingBudgets>,
    enable_prompt_caching: bool,
}

impl std::fmt::Debug for Agent {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Agent")
            .field("state", &self.state)
            .field("listener_count", &self.listeners.len())
            .field("abort_handle", &self.abort_handle)
            .field("convert_to_llm", &"<callback>")
            .field(
                "transform_context",
                &self.transform_context.as_ref().map(|_| "<callback>"),
            )
            .field("steering_queue_len", &self.steering_queue.len())
            .field("follow_up_queue_len", &self.follow_up_queue.len())
            .field("steering_mode", &self.steering_mode)
            .field("follow_up_mode", &self.follow_up_mode)
            .field("stream_fn", &self.stream_fn.as_ref().map(|_| "<callback>"))
            .field("session_id", &self.session_id)
            .field(
                "get_api_key",
                &self.get_api_key.as_ref().map(|_| "<callback>"),
            )
            .field("thinking_budgets", &self.thinking_budgets)
            .field("enable_prompt_caching", &self.enable_prompt_caching)
            .finish()
    }
}

impl Default for Agent {
    fn default() -> Self {
        Self::new(AgentOptions::default())
    }
}

impl Agent {
    pub fn new(options: AgentOptions) -> Self {
        Self {
            state: options.initial_state.unwrap_or_default(),
            listeners: HashMap::new(),
            next_listener_id: 1,
            abort_handle: None,
            convert_to_llm: options
                .convert_to_llm
                .unwrap_or_else(|| Arc::new(default_convert_to_llm)),
            transform_context: options.transform_context,
            steering_queue: Vec::new(),
            follow_up_queue: Vec::new(),
            steering_mode: options.steering_mode,
            follow_up_mode: options.follow_up_mode,
            stream_fn: options.stream_fn,
            session_id: options.session_id,
            get_api_key: options.get_api_key,
            thinking_budgets: options.thinking_budgets,
            enable_prompt_caching: options.enable_prompt_caching,
        }
    }

    pub fn state(&self) -> &AgentState {
        &self.state
    }

    pub fn state_mut(&mut self) -> &mut AgentState {
        &mut self.state
    }

    pub fn convert_to_llm(&self) -> &ConvertToLlmFn {
        &self.convert_to_llm
    }

    pub fn transform_context(&self) -> Option<&TransformContextFn> {
        self.transform_context.as_ref()
    }

    pub fn stream_fn(&self) -> Option<&StreamFn> {
        self.stream_fn.as_ref()
    }

    pub fn set_stream_fn(&mut self, value: Option<StreamFn>) {
        self.stream_fn = value;
    }

    pub fn get_api_key(&self) -> Option<&ApiKeyResolver> {
        self.get_api_key.as_ref()
    }

    pub fn session_id(&self) -> Option<&str> {
        self.session_id.as_deref()
    }

    pub fn set_session_id(&mut self, value: Option<String>) {
        self.session_id = value;
    }

    pub fn thinking_budgets(&self) -> Option<&ThinkingBudgets> {
        self.thinking_budgets.as_ref()
    }

    pub fn set_thinking_budgets(&mut self, value: Option<ThinkingBudgets>) {
        self.thinking_budgets = value;
    }

    pub fn enable_prompt_caching(&self) -> bool {
        self.enable_prompt_caching
    }

    pub fn subscribe(&mut self, listener: AgentListener) -> u64 {
        let listener_id = self.next_listener_id;
        self.next_listener_id += 1;
        self.listeners.insert(listener_id, listener);
        listener_id
    }

    pub fn unsubscribe(&mut self, listener_id: u64) -> bool {
        self.listeners.remove(&listener_id).is_some()
    }

    pub fn set_system_prompt(&mut self, value: impl Into<String>) {
        self.state.system_prompt = value.into();
    }

    pub fn set_model(&mut self, model: Model) {
        self.state.model = Some(model);
    }

    pub fn set_thinking_level(&mut self, level: ThinkingLevel) {
        self.state.thinking_level = level;
    }

    pub fn set_steering_mode(&mut self, mode: QueueMode) {
        self.steering_mode = mode;
    }

    pub fn steering_mode(&self) -> QueueMode {
        self.steering_mode
    }

    pub fn set_follow_up_mode(&mut self, mode: QueueMode) {
        self.follow_up_mode = mode;
    }

    pub fn follow_up_mode(&self) -> QueueMode {
        self.follow_up_mode
    }

    pub fn set_tools(&mut self, tools: Vec<AgentTool>) {
        self.state.tools = tools;
    }

    pub fn replace_messages(&mut self, messages: Vec<AgentMessage>) {
        self.state.messages = messages;
    }

    pub fn append_message(&mut self, message: AgentMessage) {
        self.state.messages.push(message);
    }

    pub fn steer(&mut self, message: AgentMessage) {
        self.steering_queue.push(message);
    }

    pub fn follow_up(&mut self, message: AgentMessage) {
        self.follow_up_queue.push(message);
    }

    pub fn clear_steering_queue(&mut self) {
        self.steering_queue.clear();
    }

    pub fn clear_follow_up_queue(&mut self) {
        self.follow_up_queue.clear();
    }

    pub fn clear_all_queues(&mut self) {
        self.clear_steering_queue();
        self.clear_follow_up_queue();
    }

    pub fn clear_messages(&mut self) {
        self.state.messages.clear();
    }

    pub fn reset(&mut self) {
        self.state.messages.clear();
        self.state.is_streaming = false;
        self.state.stream_message = None;
        self.state.pending_tool_calls.clear();
        self.state.error = None;
        self.abort_handle = None;
        self.clear_all_queues();
    }

    pub fn begin_run(&mut self) -> Arc<Notify> {
        let abort_handle = AbortHandle::new();
        let signal = abort_handle.signal();
        self.abort_handle = Some(abort_handle);
        self.state.is_streaming = true;
        self.state.stream_message = None;
        self.state.error = None;
        self.state.pending_tool_calls.clear();
        signal
    }

    pub fn finish_run(&mut self) {
        self.state.is_streaming = false;
        self.state.stream_message = None;
        self.state.pending_tool_calls.clear();
        self.abort_handle = None;
    }

    pub fn abort(&self) {
        if let Some(handle) = &self.abort_handle {
            handle.abort();
        }
    }

    pub fn is_aborted(&self) -> bool {
        self.abort_handle
            .as_ref()
            .is_some_and(AbortHandle::is_aborted)
    }

    pub fn abort_signal(&self) -> Option<Arc<Notify>> {
        self.abort_handle.as_ref().map(AbortHandle::signal)
    }

    pub fn build_input_messages(
        &self,
        input: impl Into<AgentInput>,
        images: Vec<ImageContent>,
    ) -> Vec<AgentMessage> {
        match input.into() {
            AgentInput::Messages(messages) => messages,
            AgentInput::Message(message) => vec![message],
            AgentInput::Text(text) => {
                let mut content = vec![UserContent::Text(TextContent {
                    text: Some(text),
                    ..Default::default()
                })];

                content.extend(images.into_iter().map(UserContent::Image));

                vec![AgentMessage::Message(Message::User(UserMessage {
                    role: Default::default(),
                    content,
                    timestamp: Some(current_timestamp_ms()),
                }))]
            }
        }
    }

    pub fn last_assistant_message(&self) -> Option<&AssistantMessage> {
        self.state
            .messages
            .iter()
            .rev()
            .find_map(|message| match message {
                AgentMessage::Message(Message::Assistant(message)) => Some(message),
                _ => None,
            })
    }

    pub fn take_steering_messages(&mut self) -> Vec<AgentMessage> {
        self.steering_mode.drain(&mut self.steering_queue)
    }

    pub fn take_follow_up_messages(&mut self) -> Vec<AgentMessage> {
        self.follow_up_mode.drain(&mut self.follow_up_queue)
    }

    pub fn build_agent_context(&self) -> AgentContext {
        AgentContext {
            system_prompt: self.state.system_prompt.clone(),
            messages: self.state.messages.clone(),
            tools: Some(self.state.tools.clone()),
        }
    }

    pub fn build_loop_config(&self) -> Option<AgentLoopConfig> {
        let mut model = self.state.model.clone()?;
        model.thinking_level = self.state.thinking_level;
        Some(AgentLoopConfig {
            model,
            convert_to_llm: Arc::clone(&self.convert_to_llm),
            transform_context: self.transform_context.clone(),
            get_api_key: self.get_api_key.clone(),
            get_steering_messages: None,
            get_follow_up_messages: None,
            api_key: None,
            temperature: None,
            max_tokens: self
                .thinking_budgets
                .as_ref()
                .and_then(|budgets| budgets.max_tokens),
        })
    }

    pub fn build_stream_options(&self, api_key: Option<String>) -> SimpleStreamOptions {
        SimpleStreamOptions {
            api_key,
            temperature: None,
            max_tokens: self
                .thinking_budgets
                .as_ref()
                .and_then(|budgets| budgets.max_tokens),
            signal: self.abort_signal(),
        }
    }

    pub async fn prompt(
        &mut self,
        input: impl Into<AgentInput>,
    ) -> AgentRunResult<AssistantMessage> {
        self.prompt_with_images(input, Vec::new()).await
    }

    pub async fn prompt_with_images(
        &mut self,
        input: impl Into<AgentInput>,
        images: Vec<ImageContent>,
    ) -> AgentRunResult<AssistantMessage> {
        let prompts = self.build_input_messages(input, images);
        self.run_prompts(prompts).await
    }

    pub async fn prompt_text(&mut self, input: impl Into<AgentInput>) -> AgentRunResult<String> {
        let response = self.prompt(input).await?;
        Ok(extract_text(&AgentMessage::Message(Message::Assistant(
            response,
        ))))
    }

    pub async fn continue_(&mut self) -> AgentRunResult<AssistantMessage> {
        let model = self
            .state
            .model
            .clone()
            .ok_or(AgentRunError::MissingModel)?;
        let stream_fn = self
            .stream_fn
            .clone()
            .ok_or(AgentRunError::MissingStreamFn)?;
        let signal = self.begin_run();
        let context = self.build_agent_context();
        let config = self
            .build_run_loop_config()
            .ok_or(AgentRunError::MissingModel)?;
        let stream = agent_loop_continue(context, config, Some(signal), Some(stream_fn))
            .map_err(|error| AgentRunError::Loop(error.to_string()))?;

        self.consume_stream(stream, &model).await
    }

    async fn run_prompts(
        &mut self,
        prompts: Vec<AgentMessage>,
    ) -> AgentRunResult<AssistantMessage> {
        let model = self
            .state
            .model
            .clone()
            .ok_or(AgentRunError::MissingModel)?;
        let stream_fn = self
            .stream_fn
            .clone()
            .ok_or(AgentRunError::MissingStreamFn)?;
        let signal = self.begin_run();
        let context = self.build_agent_context();
        let config = self
            .build_run_loop_config()
            .ok_or(AgentRunError::MissingModel)?;
        let stream = agent_loop(prompts, context, config, Some(signal), Some(stream_fn));

        self.consume_stream(stream, &model).await
    }

    fn build_run_loop_config(&mut self) -> Option<AgentLoopConfig> {
        let mut config = self.build_loop_config()?;
        config.get_steering_messages = take_once_provider(self.take_steering_messages());
        config.get_follow_up_messages = take_once_provider(self.take_follow_up_messages());
        Some(config)
    }

    async fn consume_stream(
        &mut self,
        stream: AgentEventStream,
        model: &Model,
    ) -> AgentRunResult<AssistantMessage> {
        let result = self.consume_stream_inner(&stream).await;
        let was_aborted = self.is_aborted();
        self.finish_run();

        match result {
            Ok(()) => self
                .last_assistant_message()
                .cloned()
                .ok_or(AgentRunError::MissingAssistantResponse),
            Err(error) => {
                let error_text = error.to_string();
                self.state.error = Some(error_text.clone());
                self.append_message(create_error_message(model, &error_text, was_aborted));
                Err(error)
            }
        }
    }

    async fn consume_stream_inner(&mut self, stream: &AgentEventStream) -> AgentRunResult<()> {
        loop {
            match stream.next().await {
                Ok(Some(event)) => self.handle_event(event),
                Ok(None) => break,
                Err(error) => return Err(AgentRunError::Stream(error.to_string())),
            }
        }

        stream
            .result()
            .await
            .map(|_| ())
            .map_err(|error| AgentRunError::Stream(error.to_string()))
    }

    pub fn llm_context_from_messages(
        &self,
        messages: Vec<Message>,
        tools: Option<Vec<AgentTool>>,
    ) -> Context {
        Context {
            system_prompt: self.state.system_prompt.clone(),
            messages,
            tools,
        }
    }

    pub fn handle_event(&mut self, event: AgentEvent) {
        self.apply_event(&event);
        self.emit(&event);
    }

    pub fn handle_remaining_partial(
        &mut self,
        partial: Option<AgentMessage>,
    ) -> Result<(), String> {
        match partial {
            Some(message) if has_meaningful_content(&message) => {
                self.append_message(message);
                Ok(())
            }
            Some(_) if self.is_aborted() => Err("Request was aborted".to_string()),
            _ => Ok(()),
        }
    }

    fn emit(&self, event: &AgentEvent) {
        for listener in self.listeners.values() {
            listener(event);
        }
    }

    fn apply_event(&mut self, event: &AgentEvent) {
        match event {
            AgentEvent::MessageStart(MessageStartEvent { message, .. }) => {
                self.state.stream_message = message.clone();
            }
            AgentEvent::MessageUpdate(message_update) => {
                self.state.stream_message = message_update.message.clone();
            }
            AgentEvent::MessageEnd(MessageEndEvent { message, .. }) => {
                self.state.stream_message = message.clone();
                self.state.stream_message = None;
                if let Some(message) = message.clone() {
                    self.append_message(message);
                }
            }
            AgentEvent::ToolExecutionStart(ToolExecutionStartEvent { tool_call_id, .. }) => {
                if !tool_call_id.is_empty() {
                    self.state.pending_tool_calls.insert(tool_call_id.clone());
                }
            }
            AgentEvent::ToolExecutionEnd(ToolExecutionEndEvent { tool_call_id, .. }) => {
                if !tool_call_id.is_empty() {
                    self.state.pending_tool_calls.remove(tool_call_id);
                }
            }
            AgentEvent::TurnEnd(turn_end) => {
                if let Some(AgentMessage::Message(Message::Assistant(message))) = &turn_end.message
                    && let Some(error_message) = &message.error_message
                    && !error_message.trim().is_empty()
                {
                    self.state.error = Some(error_message.clone());
                }
            }
            AgentEvent::AgentEnd(_) => {
                self.state.is_streaming = false;
                self.state.stream_message = None;
            }
            _ => {}
        }
    }
}

pub fn default_convert_to_llm(messages: Vec<AgentMessage>) -> MaybeAwaitable<Vec<Message>> {
    MaybeAwaitable::ready(
        messages
            .into_iter()
            .filter_map(|message| match message {
                AgentMessage::Message(message) => Some(message),
                AgentMessage::Custom(_) => None,
            })
            .collect(),
    )
}

pub fn extract_text(message: &AgentMessage) -> String {
    match message {
        AgentMessage::Message(Message::User(message)) => message
            .content
            .iter()
            .filter_map(|item| match item {
                UserContent::Text(content) => content.text.clone(),
                UserContent::Image(_) => None,
            })
            .collect(),
        AgentMessage::Message(Message::Assistant(message)) => message
            .content
            .iter()
            .filter_map(|item| match item {
                Some(AssistantContent::Text(content)) => content.text.clone(),
                _ => None,
            })
            .collect(),
        AgentMessage::Message(Message::ToolResult(message)) => message
            .content
            .iter()
            .filter_map(|item| match item {
                crate::types::ToolResultContent::Text(content) => content.text.clone(),
                crate::types::ToolResultContent::Image(_) => None,
            })
            .collect(),
        AgentMessage::Custom(_) => String::new(),
    }
}

pub fn create_error_message(
    model: &Model,
    error: impl ToString,
    was_aborted: bool,
) -> AgentMessage {
    AgentMessage::Message(Message::Assistant(AssistantMessage {
        content: vec![Some(AssistantContent::Text(TextContent {
            text: Some(String::new()),
            ..Default::default()
        }))],
        stop_reason: Some(if was_aborted {
            StopReason::Aborted
        } else {
            StopReason::Error
        }),
        timestamp: Some(current_timestamp_ms()),
        api: Some(model.api.clone()),
        provider: Some(model.provider.clone()),
        model: Some(model.id.clone()),
        usage: Some(zero_usage()),
        error_message: Some(error.to_string()),
        ..Default::default()
    }))
}

pub fn has_meaningful_content(message: &AgentMessage) -> bool {
    let AgentMessage::Message(Message::Assistant(message)) = message else {
        return false;
    };

    if message.content.is_empty() {
        return false;
    }

    message.content.iter().any(|item| match item {
        Some(AssistantContent::Text(TextContent {
            text: Some(text), ..
        })) => !text.trim().is_empty(),
        Some(AssistantContent::Thinking(ThinkingContent {
            thinking: Some(thinking),
            ..
        })) => !thinking.trim().is_empty(),
        Some(AssistantContent::ToolCall(tool_call)) => tool_call
            .name
            .as_deref()
            .is_some_and(|name| !name.trim().is_empty()),
        _ => false,
    })
}

fn take_once_provider(messages: Vec<AgentMessage>) -> Option<AgentMessageProvider> {
    if messages.is_empty() {
        return None;
    }

    let shared = Arc::new(Mutex::new(Some(messages)));
    Some(Arc::new(move || {
        let shared = Arc::clone(&shared);
        Box::pin(async move {
            match shared.lock() {
                Ok(mut guard) => guard.take().unwrap_or_default(),
                Err(poisoned) => poisoned.into_inner().take().unwrap_or_default(),
            }
        })
    }))
}

fn current_timestamp_ms() -> i64 {
    match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(duration) => duration.as_millis() as i64,
        Err(error) => -(error.duration().as_millis() as i64),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{
        AgentEndEvent, MessageStartEventType, ToolExecutionEndEventType,
        ToolExecutionStartEventType, ToolResultMessage,
    };
    use serde_json::json;

    fn assistant_message_with_text(text: &str) -> AgentMessage {
        AgentMessage::Message(Message::Assistant(AssistantMessage {
            content: vec![Some(AssistantContent::Text(TextContent {
                text: Some(text.to_string()),
                ..Default::default()
            }))],
            ..Default::default()
        }))
    }

    #[test]
    fn builds_text_input_with_images() {
        let agent = Agent::default();
        let messages = agent.build_input_messages(
            "hello",
            vec![ImageContent {
                url: Some("https://example.com/cat.png".to_string()),
                mime_type: Some("image/png".to_string()),
                ..Default::default()
            }],
        );

        assert_eq!(messages.len(), 1);
        let AgentMessage::Message(Message::User(message)) = &messages[0] else {
            panic!("expected user message");
        };
        assert_eq!(message.content.len(), 2);
    }

    #[test]
    fn extracts_text_from_supported_messages() {
        let assistant = assistant_message_with_text("hi");
        assert_eq!(extract_text(&assistant), "hi");

        let tool_result = AgentMessage::Message(Message::ToolResult(ToolResultMessage {
            content: vec![crate::types::ToolResultContent::Text(TextContent {
                text: Some("done".to_string()),
                ..Default::default()
            })],
            ..Default::default()
        }));
        assert_eq!(extract_text(&tool_result), "done");
    }

    #[test]
    fn queue_mode_one_at_a_time_drains_single_item() {
        let mut agent = Agent::new(AgentOptions {
            steering_mode: QueueMode::OneAtATime,
            ..Default::default()
        });
        agent.steer(assistant_message_with_text("one"));
        agent.steer(assistant_message_with_text("two"));

        assert_eq!(agent.take_steering_messages().len(), 1);
        assert_eq!(agent.take_steering_messages().len(), 1);
        assert!(agent.take_steering_messages().is_empty());
    }

    #[test]
    fn queue_mode_all_drains_entire_queue() {
        let mut agent = Agent::new(AgentOptions {
            steering_mode: QueueMode::All,
            ..Default::default()
        });
        agent.steer(assistant_message_with_text("one"));
        agent.steer(assistant_message_with_text("two"));

        assert_eq!(agent.take_steering_messages().len(), 2);
        assert!(agent.take_steering_messages().is_empty());
    }

    #[test]
    fn handle_events_updates_state() {
        let mut agent = Agent::default();
        agent.begin_run();

        let partial = assistant_message_with_text("hello");
        agent.handle_event(AgentEvent::MessageStart(MessageStartEvent {
            type_name: MessageStartEventType::Value,
            message: Some(partial.clone()),
        }));
        assert_eq!(agent.state().stream_message, Some(partial.clone()));

        agent.handle_event(AgentEvent::ToolExecutionStart(ToolExecutionStartEvent {
            type_name: ToolExecutionStartEventType::Value,
            tool_call_id: "call_1".to_string(),
            tool_name: "lookup".to_string(),
            args: Some(
                json!({
                    "city": "Austin"
                })
                .as_object()
                .cloned()
                .expect("json object"),
            ),
        }));
        assert!(agent.state().pending_tool_calls.contains("call_1"));

        agent.handle_event(AgentEvent::ToolExecutionEnd(ToolExecutionEndEvent {
            type_name: ToolExecutionEndEventType::Value,
            tool_call_id: "call_1".to_string(),
            tool_name: "lookup".to_string(),
            result: None,
            is_error: false,
        }));
        assert!(!agent.state().pending_tool_calls.contains("call_1"));

        agent.handle_event(AgentEvent::MessageEnd(MessageEndEvent {
            message: Some(partial.clone()),
            ..Default::default()
        }));
        assert!(agent.state().stream_message.is_none());
        assert_eq!(agent.state().messages, vec![partial.clone()]);

        agent.handle_event(AgentEvent::AgentEnd(AgentEndEvent {
            messages: vec![partial],
            ..Default::default()
        }));
        assert!(!agent.state().is_streaming);
    }

    #[test]
    fn records_turn_end_error_message() {
        let mut agent = Agent::default();
        let message = AgentMessage::Message(Message::Assistant(AssistantMessage {
            error_message: Some("provider failed".to_string()),
            ..Default::default()
        }));
        agent.handle_event(AgentEvent::TurnEnd(crate::types::TurnEndEvent {
            message: Some(message),
            ..Default::default()
        }));
        assert_eq!(agent.state().error.as_deref(), Some("provider failed"));
    }

    #[test]
    fn meaningful_content_detects_text_thinking_and_tool_calls() {
        assert!(has_meaningful_content(&assistant_message_with_text(
            "hello"
        )));

        let thinking = AgentMessage::Message(Message::Assistant(AssistantMessage {
            content: vec![Some(AssistantContent::Thinking(ThinkingContent {
                thinking: Some("reasoning".to_string()),
                ..Default::default()
            }))],
            ..Default::default()
        }));
        assert!(has_meaningful_content(&thinking));

        let tool_call = AgentMessage::Message(Message::Assistant(AssistantMessage {
            content: vec![Some(AssistantContent::ToolCall(
                crate::types::ToolCallContent {
                    name: Some("search".to_string()),
                    arguments: json!({}).as_object().cloned().expect("json object"),
                    ..Default::default()
                },
            ))],
            ..Default::default()
        }));
        assert!(has_meaningful_content(&tool_call));
    }

    #[test]
    fn create_error_message_sets_stop_reason_and_usage() {
        let message = create_error_message(
            &Model {
                provider: "openai".to_string(),
                id: "gpt-5".to_string(),
                api: "openai-completions".to_string(),
                ..Default::default()
            },
            "boom",
            false,
        );

        let AgentMessage::Message(Message::Assistant(message)) = message else {
            panic!("expected assistant error message");
        };
        assert_eq!(message.stop_reason, Some(StopReason::Error));
        assert_eq!(message.error_message.as_deref(), Some("boom"));
        assert_eq!(message.usage, Some(zero_usage()));
    }
}
