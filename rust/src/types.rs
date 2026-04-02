use std::collections::{HashSet, VecDeque};
use std::error::Error;
use std::fmt;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

use futures::future::BoxFuture;
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use tokio::sync::Notify;

pub type JsonPrimitive = Value;
pub type JsonValue = Value;
pub type JsonObject = Map<String, Value>;
pub type ToolCall = ToolCallContent;

macro_rules! literal_tag {
    ($name:ident, $value:literal) => {
        #[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
        pub enum $name {
            #[default]
            #[serde(rename = $value)]
            Value,
        }
    };
}

literal_tag!(TextContentType, "text");
literal_tag!(ImageContentType, "image");
literal_tag!(ThinkingContentType, "thinking");
literal_tag!(ToolCallContentType, "tool_call");
literal_tag!(UserRole, "user");
literal_tag!(AssistantRole, "assistant");
literal_tag!(ToolResultRole, "tool_result");
literal_tag!(AgentStartEventType, "agent_start");
literal_tag!(AgentEndEventType, "agent_end");
literal_tag!(TurnStartEventType, "turn_start");
literal_tag!(TurnEndEventType, "turn_end");
literal_tag!(MessageStartEventType, "message_start");
literal_tag!(MessageUpdateEventType, "message_update");
literal_tag!(MessageEndEventType, "message_end");
literal_tag!(ToolExecutionStartEventType, "tool_execution_start");
literal_tag!(ToolExecutionUpdateEventType, "tool_execution_update");
literal_tag!(ToolExecutionEndEventType, "tool_execution_end");

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum StopReason {
    Stop,
    Length,
    ToolUse,
    Error,
    Aborted,
}

pub const STOP_REASONS: &[StopReason] = &[
    StopReason::Stop,
    StopReason::Length,
    StopReason::ToolUse,
    StopReason::Error,
    StopReason::Aborted,
];

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ThinkingLevel {
    #[default]
    Off,
    Minimal,
    Low,
    Medium,
    High,
    Xhigh,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CostPayload {
    pub input: f64,
    pub output: f64,
    pub cache_read: f64,
    pub cache_write: f64,
    pub total: f64,
}

impl Default for CostPayload {
    fn default() -> Self {
        Self {
            input: 0.0,
            output: 0.0,
            cache_read: 0.0,
            cache_write: 0.0,
            total: 0.0,
        }
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct UsagePayload {
    pub input: u32,
    pub output: u32,
    pub cache_read: u32,
    pub cache_write: u32,
    pub total_tokens: u32,
    pub cost: CostPayload,
}

pub fn zero_usage() -> UsagePayload {
    UsagePayload::default()
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct ThinkingBudgets {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub thinking_budget: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<u32>,
}

pub enum MaybeAwaitable<T> {
    Ready(T),
    Future(BoxFuture<'static, T>),
}

impl<T> MaybeAwaitable<T> {
    pub fn ready(value: T) -> Self {
        Self::Ready(value)
    }

    pub fn from_future<F>(future: F) -> Self
    where
        F: std::future::Future<Output = T> + Send + 'static,
    {
        Self::Future(Box::pin(future))
    }

    pub async fn resolve(self) -> T {
        match self {
            Self::Ready(value) => value,
            Self::Future(future) => future.await,
        }
    }
}

impl<T> fmt::Debug for MaybeAwaitable<T> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Ready(_) => f.write_str("MaybeAwaitable::Ready(..)"),
            Self::Future(_) => f.write_str("MaybeAwaitable::Future(..)"),
        }
    }
}

impl<T> From<T> for MaybeAwaitable<T> {
    fn from(value: T) -> Self {
        Self::Ready(value)
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct CacheControl {
    #[serde(rename = "type", skip_serializing_if = "Option::is_none")]
    pub type_name: Option<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct TextContent {
    #[serde(rename = "type", default)]
    pub type_name: TextContentType,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub text: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub text_signature: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cache_control: Option<CacheControl>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct ImageContent {
    #[serde(rename = "type", default)]
    pub type_name: ImageContentType,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub url: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub mime_type: Option<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct ThinkingContent {
    #[serde(rename = "type", default)]
    pub type_name: ThinkingContentType,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub thinking: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub thinking_signature: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cache_control: Option<CacheControl>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct ToolCallContent {
    #[serde(rename = "type", default)]
    pub type_name: ToolCallContentType,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(default)]
    pub arguments: JsonObject,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub partial_json: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum AssistantContent {
    Text(TextContent),
    Thinking(ThinkingContent),
    ToolCall(ToolCallContent),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(untagged)]
pub enum UserContent {
    Text(TextContent),
    Image(ImageContent),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(untagged)]
pub enum ToolResultContent {
    Text(TextContent),
    Image(ImageContent),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct UserMessage {
    #[serde(default)]
    pub role: UserRole,
    #[serde(default)]
    pub content: Vec<UserContent>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<i64>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct AssistantMessage {
    #[serde(default)]
    pub role: AssistantRole,
    #[serde(default)]
    pub content: Vec<Option<AssistantContent>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stop_reason: Option<StopReason>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<i64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub api: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub provider: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub model: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub usage: Option<UsagePayload>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error_message: Option<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct ToolResultMessage {
    #[serde(default)]
    pub role: ToolResultRole,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_call_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_name: Option<String>,
    #[serde(default)]
    pub content: Vec<ToolResultContent>,
    #[serde(default)]
    pub details: JsonObject,
    #[serde(default)]
    pub is_error: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<i64>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct CustomAgentMessage {
    #[serde(default)]
    pub role: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<i64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum Message {
    User(UserMessage),
    Assistant(AssistantMessage),
    ToolResult(ToolResultMessage),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum AgentMessage {
    Message(Message),
    Custom(CustomAgentMessage),
}

pub type ConvertToLlmFn =
    Arc<dyn Fn(Vec<AgentMessage>) -> MaybeAwaitable<Vec<Message>> + Send + Sync>;
pub type TransformContextFn = Arc<
    dyn Fn(Vec<AgentMessage>, Option<Arc<Notify>>) -> BoxFuture<'static, Vec<AgentMessage>>
        + Send
        + Sync,
>;
pub type ApiKeyResolver = Arc<dyn Fn(String) -> MaybeAwaitable<Option<String>> + Send + Sync>;
pub type AgentMessageProvider =
    Arc<dyn Fn() -> BoxFuture<'static, Vec<AgentMessage>> + Send + Sync>;
pub type AgentToolUpdateCallback = Arc<dyn Fn(AgentToolResult) + Send + Sync>;
pub type AgentToolExecuteFn = Arc<
    dyn Fn(
            String,
            JsonObject,
            Option<Arc<Notify>>,
            AgentToolUpdateCallback,
        ) -> BoxFuture<'static, AgentToolResult>
        + Send
        + Sync,
>;

#[derive(Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct AgentToolResult {
    #[serde(default)]
    pub content: Vec<ToolResultContent>,
    #[serde(default)]
    pub details: JsonObject,
}

impl fmt::Debug for AgentToolResult {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("AgentToolResult")
            .field("content", &self.content)
            .field("details", &self.details)
            .finish()
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct Tool {
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub parameters: JsonObject,
}

#[derive(Clone, Default, Serialize, Deserialize)]
pub struct AgentTool {
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub description: String,
    #[serde(default)]
    pub parameters: JsonObject,
    #[serde(default)]
    pub label: String,
    #[serde(skip)]
    pub execute: Option<AgentToolExecuteFn>,
}

impl fmt::Debug for AgentTool {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("AgentTool")
            .field("name", &self.name)
            .field("description", &self.description)
            .field("parameters", &self.parameters)
            .field("label", &self.label)
            .field("execute", &self.execute.as_ref().map(|_| "<callable>"))
            .finish()
    }
}

impl PartialEq for AgentTool {
    fn eq(&self, other: &Self) -> bool {
        self.name == other.name
            && self.description == other.description
            && self.parameters == other.parameters
            && self.label == other.label
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct Context {
    #[serde(default)]
    pub system_prompt: String,
    #[serde(default)]
    pub messages: Vec<Message>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tools: Option<Vec<AgentTool>>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct AgentContext {
    #[serde(default)]
    pub system_prompt: String,
    #[serde(default)]
    pub messages: Vec<AgentMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tools: Option<Vec<AgentTool>>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct Model {
    #[serde(default)]
    pub provider: String,
    #[serde(default)]
    pub id: String,
    #[serde(default)]
    pub api: String,
    #[serde(default)]
    pub thinking_level: ThinkingLevel,
}

#[derive(Clone, Default, Serialize, Deserialize)]
pub struct SimpleStreamOptions {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub api_key: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<u32>,
    #[serde(skip)]
    pub signal: Option<Arc<Notify>>,
}

impl fmt::Debug for SimpleStreamOptions {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("SimpleStreamOptions")
            .field("api_key", &self.api_key.as_ref().map(|_| "<redacted>"))
            .field("temperature", &self.temperature)
            .field("max_tokens", &self.max_tokens)
            .field("signal", &self.signal.as_ref().map(|_| "<notify>"))
            .finish()
    }
}

impl PartialEq for SimpleStreamOptions {
    fn eq(&self, other: &Self) -> bool {
        self.api_key == other.api_key
            && self.temperature == other.temperature
            && self.max_tokens == other.max_tokens
    }
}

pub trait StreamResponse: Send {
    fn result<'a>(&'a mut self) -> BoxFuture<'a, AssistantMessage>;
    fn next_event<'a>(&'a mut self) -> BoxFuture<'a, Option<AssistantMessageEvent>>;
}

pub type StreamFn = Arc<
    dyn Fn(Model, Context, SimpleStreamOptions) -> BoxFuture<'static, Box<dyn StreamResponse>>
        + Send
        + Sync,
>;

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum AssistantMessageEventType {
    Start,
    TextStart,
    TextDelta,
    TextEnd,
    ThinkingStart,
    ThinkingDelta,
    ThinkingEnd,
    ToolCallStart,
    ToolCallDelta,
    ToolCallEnd,
    Done,
    Error,
}

pub const STREAM_UPDATE_EVENTS: &[AssistantMessageEventType] = &[
    AssistantMessageEventType::TextStart,
    AssistantMessageEventType::TextDelta,
    AssistantMessageEventType::TextEnd,
    AssistantMessageEventType::ThinkingStart,
    AssistantMessageEventType::ThinkingDelta,
    AssistantMessageEventType::ThinkingEnd,
    AssistantMessageEventType::ToolCallStart,
    AssistantMessageEventType::ToolCallDelta,
    AssistantMessageEventType::ToolCallEnd,
];

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum AssistantEventContent {
    Text(String),
    TextBlock(TextContent),
    ThinkingBlock(ThinkingContent),
    ToolCall(ToolCallContent),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum AssistantEventError {
    Message(AssistantMessage),
    Text(String),
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct AssistantMessageEvent {
    #[serde(rename = "type", skip_serializing_if = "Option::is_none")]
    pub event_type: Option<AssistantMessageEventType>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub partial: Option<AssistantMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub content_index: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub delta: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub content: Option<AssistantEventContent>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tool_call: Option<ToolCallContent>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<AssistantMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<AssistantEventError>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct AgentStartEvent {
    #[serde(rename = "type", default)]
    pub type_name: AgentStartEventType,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct AgentEndEvent {
    #[serde(rename = "type", default)]
    pub type_name: AgentEndEventType,
    #[serde(default)]
    pub messages: Vec<AgentMessage>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct TurnStartEvent {
    #[serde(rename = "type", default)]
    pub type_name: TurnStartEventType,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct TurnEndEvent {
    #[serde(rename = "type", default)]
    pub type_name: TurnEndEventType,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<AgentMessage>,
    #[serde(default)]
    pub tool_results: Vec<ToolResultMessage>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct MessageStartEvent {
    #[serde(rename = "type", default)]
    pub type_name: MessageStartEventType,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<AgentMessage>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct MessageUpdateEvent {
    #[serde(rename = "type", default)]
    pub type_name: MessageUpdateEventType,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<AgentMessage>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub assistant_message_event: Option<AssistantMessageEvent>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct MessageEndEvent {
    #[serde(rename = "type", default)]
    pub type_name: MessageEndEventType,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<AgentMessage>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum MessageEvent {
    Start(MessageStartEvent),
    Update(Box<MessageUpdateEvent>),
    End(MessageEndEvent),
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct ToolExecutionStartEvent {
    #[serde(rename = "type", default)]
    pub type_name: ToolExecutionStartEventType,
    #[serde(default)]
    pub tool_call_id: String,
    #[serde(default)]
    pub tool_name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub args: Option<JsonObject>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct ToolExecutionUpdateEvent {
    #[serde(rename = "type", default)]
    pub type_name: ToolExecutionUpdateEventType,
    #[serde(default)]
    pub tool_call_id: String,
    #[serde(default)]
    pub tool_name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub args: Option<JsonObject>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub partial_result: Option<AgentToolResult>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct ToolExecutionEndEvent {
    #[serde(rename = "type", default)]
    pub type_name: ToolExecutionEndEventType,
    #[serde(default)]
    pub tool_call_id: String,
    #[serde(default)]
    pub tool_name: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<AgentToolResult>,
    #[serde(default)]
    pub is_error: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum ToolExecutionEvent {
    Start(ToolExecutionStartEvent),
    Update(ToolExecutionUpdateEvent),
    End(ToolExecutionEndEvent),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum AgentEvent {
    AgentStart(AgentStartEvent),
    AgentEnd(AgentEndEvent),
    TurnStart(TurnStartEvent),
    TurnEnd(TurnEndEvent),
    MessageStart(MessageStartEvent),
    MessageUpdate(Box<MessageUpdateEvent>),
    MessageEnd(MessageEndEvent),
    ToolExecutionStart(ToolExecutionStartEvent),
    ToolExecutionUpdate(ToolExecutionUpdateEvent),
    ToolExecutionEnd(ToolExecutionEndEvent),
}

pub fn is_agent_end_event(event: &AgentEvent) -> bool {
    matches!(event, AgentEvent::AgentEnd(_))
}

pub fn is_turn_end_event(event: &AgentEvent) -> bool {
    matches!(event, AgentEvent::TurnEnd(_))
}

pub fn is_message_start_or_update_event(event: &AgentEvent) -> bool {
    matches!(
        event,
        AgentEvent::MessageStart(_) | AgentEvent::MessageUpdate(_)
    )
}

pub fn is_message_end_event(event: &AgentEvent) -> bool {
    matches!(event, AgentEvent::MessageEnd(_))
}

pub fn is_message_event(event: &AgentEvent) -> bool {
    matches!(
        event,
        AgentEvent::MessageStart(_) | AgentEvent::MessageUpdate(_) | AgentEvent::MessageEnd(_)
    )
}

pub fn is_tool_execution_start_event(event: &AgentEvent) -> bool {
    matches!(event, AgentEvent::ToolExecutionStart(_))
}

pub fn is_tool_execution_end_event(event: &AgentEvent) -> bool {
    matches!(event, AgentEvent::ToolExecutionEnd(_))
}

pub fn is_tool_execution_event(event: &AgentEvent) -> bool {
    matches!(
        event,
        AgentEvent::ToolExecutionStart(_)
            | AgentEvent::ToolExecutionUpdate(_)
            | AgentEvent::ToolExecutionEnd(_)
    )
}

#[derive(Clone)]
pub struct AgentLoopConfig {
    pub model: Model,
    pub convert_to_llm: ConvertToLlmFn,
    pub transform_context: Option<TransformContextFn>,
    pub get_api_key: Option<ApiKeyResolver>,
    pub get_steering_messages: Option<AgentMessageProvider>,
    pub get_follow_up_messages: Option<AgentMessageProvider>,
    pub api_key: Option<String>,
    pub temperature: Option<f64>,
    pub max_tokens: Option<u32>,
}

impl fmt::Debug for AgentLoopConfig {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("AgentLoopConfig")
            .field("model", &self.model)
            .field("convert_to_llm", &"<callback>")
            .field(
                "transform_context",
                &self.transform_context.as_ref().map(|_| "<callback>"),
            )
            .field(
                "get_api_key",
                &self.get_api_key.as_ref().map(|_| "<callback>"),
            )
            .field(
                "get_steering_messages",
                &self.get_steering_messages.as_ref().map(|_| "<callback>"),
            )
            .field(
                "get_follow_up_messages",
                &self.get_follow_up_messages.as_ref().map(|_| "<callback>"),
            )
            .field("api_key", &self.api_key.as_ref().map(|_| "<redacted>"))
            .field("temperature", &self.temperature)
            .field("max_tokens", &self.max_tokens)
            .finish()
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
pub struct AgentState {
    #[serde(default)]
    pub system_prompt: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub model: Option<Model>,
    #[serde(default)]
    pub thinking_level: ThinkingLevel,
    #[serde(default)]
    pub tools: Vec<AgentTool>,
    #[serde(default)]
    pub messages: Vec<AgentMessage>,
    #[serde(default)]
    pub is_streaming: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stream_message: Option<AgentMessage>,
    #[serde(default)]
    pub pending_tool_calls: HashSet<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

#[derive(Debug, Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct WakeupSignal;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum EventStreamQueueItem {
    Event(Box<AgentEvent>),
    Wakeup(WakeupSignal),
}

#[derive(Debug, Clone)]
pub struct EventStreamMessageError {
    message: String,
}

impl EventStreamMessageError {
    pub fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

impl fmt::Display for EventStreamMessageError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.message)
    }
}

impl Error for EventStreamMessageError {}

pub type EventStreamError = Arc<dyn Error + Send + Sync>;

pub fn event_stream_error(message: impl Into<String>) -> EventStreamError {
    Arc::new(EventStreamMessageError::new(message))
}

type IsEndEventFn = Arc<dyn Fn(&AgentEvent) -> bool + Send + Sync>;
type GetResultFn = Arc<dyn Fn(&AgentEvent) -> Vec<AgentMessage> + Send + Sync>;

pub struct EventStream {
    queue: Mutex<VecDeque<EventStreamQueueItem>>,
    notify: Notify,
    is_end_event: IsEndEventFn,
    get_result: GetResultFn,
    result: Mutex<Option<Vec<AgentMessage>>>,
    ended: AtomicBool,
    exception: Mutex<Option<EventStreamError>>,
}

impl fmt::Debug for EventStream {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let queue_len = self
            .queue
            .lock()
            .map(|queue| queue.len())
            .unwrap_or_default();
        let has_result = self
            .result
            .lock()
            .map(|result| result.is_some())
            .unwrap_or(false);
        let has_exception = self
            .exception
            .lock()
            .map(|exception| exception.is_some())
            .unwrap_or(false);

        f.debug_struct("EventStream")
            .field("queue_len", &queue_len)
            .field("has_result", &has_result)
            .field("ended", &self.ended.load(Ordering::SeqCst))
            .field("has_exception", &has_exception)
            .finish()
    }
}

impl EventStream {
    pub fn new<F, G>(is_end_event: F, get_result: G) -> Self
    where
        F: Fn(&AgentEvent) -> bool + Send + Sync + 'static,
        G: Fn(&AgentEvent) -> Vec<AgentMessage> + Send + Sync + 'static,
    {
        Self {
            queue: Mutex::new(VecDeque::new()),
            notify: Notify::new(),
            is_end_event: Arc::new(is_end_event),
            get_result: Arc::new(get_result),
            result: Mutex::new(None),
            ended: AtomicBool::new(false),
            exception: Mutex::new(None),
        }
    }

    pub fn push(&self, event: AgentEvent) {
        if self.ended.load(Ordering::SeqCst) {
            return;
        }

        let mut queue = self.lock_queue();
        queue.push_back(EventStreamQueueItem::Event(Box::new(event)));
        drop(queue);
        self.notify.notify_one();
    }

    pub fn end(&self, result: Vec<AgentMessage>) {
        {
            let mut stored_result = self.lock_result();
            *stored_result = Some(result);
        }
        self.ended.store(true, Ordering::SeqCst);
        let mut queue = self.lock_queue();
        queue.push_back(EventStreamQueueItem::Wakeup(WakeupSignal));
        drop(queue);
        self.notify.notify_one();
    }

    pub fn set_exception(&self, exc: EventStreamError) {
        if self.ended.load(Ordering::SeqCst) {
            return;
        }

        {
            let mut stored_exception = self.lock_exception();
            *stored_exception = Some(exc);
        }
        self.ended.store(true, Ordering::SeqCst);
        let mut queue = self.lock_queue();
        queue.push_back(EventStreamQueueItem::Wakeup(WakeupSignal));
        drop(queue);
        self.notify.notify_one();
    }

    pub async fn next(&self) -> Result<Option<AgentEvent>, EventStreamError> {
        loop {
            if let Some(item) = self.pop_queue_item() {
                match item {
                    EventStreamQueueItem::Wakeup(_) => {
                        if let Some(exc) = self.take_exception() {
                            return Err(exc);
                        }
                        if self.ended.load(Ordering::SeqCst) && self.is_queue_empty() {
                            return Ok(None);
                        }
                        continue;
                    }
                    EventStreamQueueItem::Event(event) => {
                        let event = *event;
                        if (self.is_end_event)(&event) {
                            let result = (self.get_result)(&event);
                            let mut stored_result = self.lock_result();
                            *stored_result = Some(result);
                            self.ended.store(true, Ordering::SeqCst);
                        }
                        return Ok(Some(event));
                    }
                }
            }

            if let Some(exc) = self.take_exception() {
                return Err(exc);
            }
            if self.ended.load(Ordering::SeqCst) {
                return Ok(None);
            }

            self.notify.notified().await;
        }
    }

    pub async fn result(&self) -> Result<Vec<AgentMessage>, EventStreamError> {
        loop {
            if self.is_queue_empty() {
                if let Some(exc) = self.take_exception() {
                    return Err(exc);
                }
                if self.ended.load(Ordering::SeqCst) {
                    break;
                }
            }

            match self.next().await? {
                Some(_) => {}
                None => break,
            }
        }

        let stored_result = self.lock_result();
        Ok(stored_result.clone().unwrap_or_default())
    }

    fn pop_queue_item(&self) -> Option<EventStreamQueueItem> {
        let mut queue = self.lock_queue();
        queue.pop_front()
    }

    fn is_queue_empty(&self) -> bool {
        let queue = self.lock_queue();
        queue.is_empty()
    }

    fn take_exception(&self) -> Option<EventStreamError> {
        let mut stored_exception = self.lock_exception();
        stored_exception.take()
    }

    fn lock_queue(&self) -> std::sync::MutexGuard<'_, VecDeque<EventStreamQueueItem>> {
        match self.queue.lock() {
            Ok(guard) => guard,
            Err(poisoned) => poisoned.into_inner(),
        }
    }

    fn lock_result(&self) -> std::sync::MutexGuard<'_, Option<Vec<AgentMessage>>> {
        match self.result.lock() {
            Ok(guard) => guard,
            Err(poisoned) => poisoned.into_inner(),
        }
    }

    fn lock_exception(&self) -> std::sync::MutexGuard<'_, Option<EventStreamError>> {
        match self.exception.lock() {
            Ok(guard) => guard,
            Err(poisoned) => poisoned.into_inner(),
        }
    }
}

