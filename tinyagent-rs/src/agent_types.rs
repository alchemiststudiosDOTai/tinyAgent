use crate::error::Result;
use futures::future::BoxFuture;
use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::collections::{BTreeSet, HashMap};
use std::fmt;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio_util::sync::CancellationToken;

pub type JsonObject = Map<String, Value>;
pub type ToolUpdateCallback = Arc<dyn Fn(AgentToolResult) + Send + Sync>;
pub type ToolExecutor = Arc<
    dyn Fn(
            String,
            JsonObject,
            CancellationToken,
            ToolUpdateCallback,
        ) -> BoxFuture<'static, Result<AgentToolResult>>
        + Send
        + Sync,
>;

pub fn current_timestamp() -> i64 {
    match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(duration) => duration.as_millis() as i64,
        Err(error) => -(error.duration().as_millis() as i64),
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum ThinkingLevel {
    Off,
    Minimal,
    Low,
    Medium,
    High,
    Xhigh,
}

impl Default for ThinkingLevel {
    fn default() -> Self {
        Self::Off
    }
}

impl ThinkingLevel {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Off => "off",
            Self::Minimal => "minimal",
            Self::Low => "low",
            Self::Medium => "medium",
            Self::High => "high",
            Self::Xhigh => "xhigh",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum QueueMode {
    OneAtATime,
    All,
}

impl Default for QueueMode {
    fn default() -> Self {
        Self::OneAtATime
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct ThinkingBudgets {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub thinking_budget: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct TextContent {
    #[serde(rename = "type", default = "default_text_kind")]
    pub kind: String,
    #[serde(default)]
    pub text: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub text_signature: Option<String>,
}

fn default_text_kind() -> String {
    "text".to_string()
}

impl TextContent {
    pub fn new(text: impl Into<String>) -> Self {
        Self {
            kind: default_text_kind(),
            text: text.into(),
            text_signature: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct ImageContent {
    #[serde(rename = "type", default = "default_image_kind")]
    pub kind: String,
    pub url: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub mime_type: Option<String>,
}

fn default_image_kind() -> String {
    "image".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct ThinkingContent {
    #[serde(rename = "type", default = "default_thinking_kind")]
    pub kind: String,
    #[serde(default)]
    pub thinking: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub thinking_signature: Option<String>,
}

fn default_thinking_kind() -> String {
    "thinking".to_string()
}

impl ThinkingContent {
    pub fn new(thinking: impl Into<String>) -> Self {
        Self {
            kind: default_thinking_kind(),
            thinking: thinking.into(),
            thinking_signature: None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct ToolCallContent {
    #[serde(rename = "type", default = "default_tool_call_kind")]
    pub kind: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    #[serde(default)]
    pub arguments: Value,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub partial_json: Option<String>,
}

fn default_tool_call_kind() -> String {
    "tool_call".to_string()
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum UserContent {
    Text(TextContent),
    Image(ImageContent),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(untagged)]
pub enum AssistantContent {
    Text(TextContent),
    Thinking(ThinkingContent),
    ToolCall(ToolCallContent),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct Model {
    pub provider: String,
    pub id: String,
    pub api: String,
    #[serde(default)]
    pub thinking_level: ThinkingLevel,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub base_url: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub headers: Option<HashMap<String, String>>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum StopReason {
    Complete,
    Error,
    Aborted,
    ToolCalls,
    Stop,
    Length,
    ToolUse,
}

impl StopReason {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Complete => "complete",
            Self::Error => "error",
            Self::Aborted => "aborted",
            Self::ToolCalls => "tool_calls",
            Self::Stop => "stop",
            Self::Length => "length",
            Self::ToolUse => "tool_use",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct UserMessage {
    pub role: String,
    #[serde(default)]
    pub content: Vec<UserContent>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<i64>,
}

impl Default for UserMessage {
    fn default() -> Self {
        Self {
            role: "user".to_string(),
            content: Vec::new(),
            timestamp: Some(current_timestamp()),
        }
    }
}

impl UserMessage {
    pub fn text(text: impl Into<String>) -> Self {
        Self {
            content: vec![UserContent::Text(TextContent::new(text))],
            ..Self::default()
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AssistantMessage {
    pub role: String,
    #[serde(default)]
    pub content: Vec<Option<AssistantContent>>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub stop_reason: Option<StopReason>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub api: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub provider: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub model: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub usage: Option<Value>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub error_message: Option<String>,
}

impl Default for AssistantMessage {
    fn default() -> Self {
        Self {
            role: "assistant".to_string(),
            content: Vec::new(),
            stop_reason: None,
            timestamp: Some(current_timestamp()),
            api: None,
            provider: None,
            model: None,
            usage: None,
            error_message: None,
        }
    }
}

impl AssistantMessage {
    pub fn push_content(&mut self, index: usize, content: AssistantContent) {
        if self.content.len() <= index {
            self.content.resize(index + 1, None);
        }
        self.content[index] = Some(content);
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ToolResultMessage {
    pub role: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tool_call_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub tool_name: Option<String>,
    #[serde(default)]
    pub content: Vec<UserContent>,
    #[serde(default)]
    pub details: Value,
    #[serde(default)]
    pub is_error: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<i64>,
}

impl Default for ToolResultMessage {
    fn default() -> Self {
        Self {
            role: "tool_result".to_string(),
            tool_call_id: None,
            tool_name: None,
            content: Vec::new(),
            details: Value::Object(JsonObject::new()),
            is_error: false,
            timestamp: Some(current_timestamp()),
        }
    }
}

impl ToolResultMessage {
    pub fn from_result(
        tool_call_id: impl Into<String>,
        tool_name: impl Into<String>,
        result: AgentToolResult,
        is_error: bool,
    ) -> Self {
        Self {
            tool_call_id: Some(tool_call_id.into()),
            tool_name: Some(tool_name.into()),
            content: result.content,
            details: result.details,
            is_error,
            ..Self::default()
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct CustomAgentMessage {
    pub role: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub timestamp: Option<i64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub payload: Option<Value>,
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
    User(UserMessage),
    Assistant(AssistantMessage),
    ToolResult(ToolResultMessage),
    Custom(CustomAgentMessage),
}

impl AgentMessage {
    pub fn role(&self) -> &str {
        match self {
            Self::User(message) => &message.role,
            Self::Assistant(message) => &message.role,
            Self::ToolResult(message) => &message.role,
            Self::Custom(message) => &message.role,
        }
    }

    pub fn as_message(&self) -> Option<Message> {
        match self {
            Self::User(message) => Some(Message::User(message.clone())),
            Self::Assistant(message) => Some(Message::Assistant(message.clone())),
            Self::ToolResult(message) => Some(Message::ToolResult(message.clone())),
            Self::Custom(_) => None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct AgentToolResult {
    #[serde(default)]
    pub content: Vec<UserContent>,
    #[serde(default)]
    pub details: Value,
}

#[derive(Clone, Default)]
pub struct AgentTool {
    pub name: String,
    pub description: String,
    pub parameters: Value,
    pub label: String,
    pub(crate) executor: Option<ToolExecutor>,
}

impl fmt::Debug for AgentTool {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("AgentTool")
            .field("name", &self.name)
            .field("description", &self.description)
            .field("parameters", &self.parameters)
            .field("label", &self.label)
            .finish()
    }
}

impl AgentTool {
    pub fn new<F, Fut>(
        name: impl Into<String>,
        description: impl Into<String>,
        parameters: Value,
        execute: F,
    ) -> Self
    where
        F: Fn(String, JsonObject, CancellationToken, ToolUpdateCallback) -> Fut
            + Send
            + Sync
            + 'static,
        Fut: std::future::Future<Output = Result<AgentToolResult>> + Send + 'static,
    {
        Self {
            name: name.into(),
            description: description.into(),
            parameters,
            label: String::new(),
            executor: Some(Arc::new(move |tool_call_id, args, abort, on_update| {
                Box::pin(execute(tool_call_id, args, abort, on_update))
            })),
        }
    }

    pub fn call(
        &self,
        tool_call_id: String,
        args: JsonObject,
        abort: CancellationToken,
        on_update: ToolUpdateCallback,
    ) -> BoxFuture<'static, Result<AgentToolResult>> {
        match &self.executor {
            Some(executor) => executor(tool_call_id, args, abort, on_update),
            None => Box::pin(async { Ok(AgentToolResult::default()) }),
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct Context {
    pub system_prompt: String,
    pub messages: Vec<Message>,
    pub tools: Vec<AgentTool>,
}

#[derive(Debug, Clone, Default)]
pub struct AgentContext {
    pub system_prompt: String,
    pub messages: Vec<AgentMessage>,
    pub tools: Vec<AgentTool>,
}

impl AgentContext {
    pub fn to_llm_context(&self) -> Context {
        let messages = self
            .messages
            .iter()
            .filter_map(AgentMessage::as_message)
            .collect::<Vec<_>>();

        Context {
            system_prompt: self.system_prompt.clone(),
            messages,
            tools: self.tools.clone(),
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct AgentState {
    pub system_prompt: String,
    pub model: Option<Model>,
    pub thinking_level: ThinkingLevel,
    pub tools: Vec<AgentTool>,
    pub messages: Vec<AgentMessage>,
    pub is_streaming: bool,
    pub stream_message: Option<AgentMessage>,
    pub pending_tool_calls: BTreeSet<String>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum AssistantMessageEvent {
    Start {
        partial: AssistantMessage,
    },
    TextStart {
        content_index: usize,
        partial: AssistantMessage,
    },
    TextDelta {
        content_index: usize,
        delta: String,
        partial: AssistantMessage,
    },
    TextEnd {
        content_index: usize,
        content: String,
        partial: AssistantMessage,
    },
    ThinkingStart {
        content_index: usize,
        partial: AssistantMessage,
    },
    ThinkingDelta {
        content_index: usize,
        delta: String,
        partial: AssistantMessage,
    },
    ThinkingEnd {
        content_index: usize,
        content: String,
        partial: AssistantMessage,
    },
    ToolCallStart {
        content_index: usize,
        partial: AssistantMessage,
    },
    ToolCallDelta {
        content_index: usize,
        delta: String,
        partial: AssistantMessage,
    },
    ToolCallEnd {
        content_index: usize,
        tool_call: ToolCallContent,
        partial: AssistantMessage,
    },
    Done {
        reason: StopReason,
        message: AssistantMessage,
    },
    Error {
        reason: StopReason,
        error: AssistantMessage,
    },
}

impl AssistantMessageEvent {
    pub fn partial(&self) -> Option<&AssistantMessage> {
        match self {
            Self::Start { partial }
            | Self::TextStart { partial, .. }
            | Self::TextDelta { partial, .. }
            | Self::TextEnd { partial, .. }
            | Self::ThinkingStart { partial, .. }
            | Self::ThinkingDelta { partial, .. }
            | Self::ThinkingEnd { partial, .. }
            | Self::ToolCallStart { partial, .. }
            | Self::ToolCallDelta { partial, .. }
            | Self::ToolCallEnd { partial, .. } => Some(partial),
            Self::Done { message, .. } => Some(message),
            Self::Error { error, .. } => Some(error),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum AgentEvent {
    AgentStart,
    AgentEnd {
        messages: Vec<AgentMessage>,
    },
    TurnStart,
    TurnEnd {
        message: Option<AgentMessage>,
        tool_results: Vec<ToolResultMessage>,
    },
    MessageStart {
        message: Option<AgentMessage>,
    },
    MessageUpdate {
        message: Option<AgentMessage>,
        assistant_message_event: Option<AssistantMessageEvent>,
    },
    MessageEnd {
        message: Option<AgentMessage>,
    },
    ToolExecutionStart {
        tool_call_id: String,
        tool_name: String,
        args: Option<Value>,
    },
    ToolExecutionUpdate {
        tool_call_id: String,
        tool_name: String,
        args: Option<Value>,
        partial_result: Option<AgentToolResult>,
    },
    ToolExecutionEnd {
        tool_call_id: String,
        tool_name: String,
        result: Option<AgentToolResult>,
        is_error: bool,
    },
}

impl AgentEvent {
    pub fn kind(&self) -> &'static str {
        match self {
            Self::AgentStart => "agent_start",
            Self::AgentEnd { .. } => "agent_end",
            Self::TurnStart => "turn_start",
            Self::TurnEnd { .. } => "turn_end",
            Self::MessageStart { .. } => "message_start",
            Self::MessageUpdate { .. } => "message_update",
            Self::MessageEnd { .. } => "message_end",
            Self::ToolExecutionStart { .. } => "tool_execution_start",
            Self::ToolExecutionUpdate { .. } => "tool_execution_update",
            Self::ToolExecutionEnd { .. } => "tool_execution_end",
        }
    }
}

pub fn extract_text(message: &AgentMessage) -> String {
    match message {
        AgentMessage::User(message) => message
            .content
            .iter()
            .filter_map(|content| match content {
                UserContent::Text(text) => Some(text.text.as_str()),
                UserContent::Image(_) => None,
            })
            .collect(),
        AgentMessage::Assistant(message) => message
            .content
            .iter()
            .filter_map(|content| match content {
                Some(AssistantContent::Text(text)) => Some(text.text.as_str()),
                _ => None,
            })
            .collect(),
        AgentMessage::ToolResult(message) => message
            .content
            .iter()
            .filter_map(|content| match content {
                UserContent::Text(text) => Some(text.text.as_str()),
                UserContent::Image(_) => None,
            })
            .collect(),
        AgentMessage::Custom(_) => String::new(),
    }
}
