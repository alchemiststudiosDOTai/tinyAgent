use serde::{Deserialize, Serialize};
use serde_json::Value;

use super::{
    AgentMessage, AssistantMessage, MessageContent, ToolCallContent, ToolOutput, ToolResultMessage,
};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
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

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct AssistantMessageEvent {
    pub event_type: AssistantMessageEventType,
    pub partial: Option<AssistantMessage>,
    pub content_index: Option<usize>,
    pub delta: Option<String>,
    pub content: Option<MessageContent>,
    pub tool_call: Option<ToolCallContent>,
    pub reason: Option<String>,
    pub message: Option<AssistantMessage>,
    pub error: Option<String>,
}

impl AssistantMessageEvent {
    pub fn start() -> Self {
        Self {
            event_type: AssistantMessageEventType::Start,
            partial: None,
            content_index: None,
            delta: None,
            content: None,
            tool_call: None,
            reason: None,
            message: None,
            error: None,
        }
    }

    pub fn text_delta(delta: impl Into<String>) -> Self {
        Self {
            event_type: AssistantMessageEventType::TextDelta,
            partial: None,
            content_index: None,
            delta: Some(delta.into()),
            content: None,
            tool_call: None,
            reason: None,
            message: None,
            error: None,
        }
    }

    pub fn done(message: AssistantMessage) -> Self {
        Self {
            event_type: AssistantMessageEventType::Done,
            partial: None,
            content_index: None,
            delta: None,
            content: None,
            tool_call: None,
            reason: None,
            message: Some(message),
            error: None,
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
        message: Option<AssistantMessage>,
        tool_results: Vec<ToolResultMessage>,
    },
    MessageStart {
        message: AgentMessage,
    },
    MessageUpdate {
        message: AgentMessage,
        assistant_message_event: Option<AssistantMessageEvent>,
    },
    MessageEnd {
        message: AgentMessage,
    },
    ToolExecutionStart {
        tool_call_id: String,
        tool_name: String,
        args: Value,
    },
    ToolExecutionUpdate {
        tool_call_id: String,
        tool_name: String,
        args: Value,
        partial_result: ToolOutput,
    },
    ToolExecutionEnd {
        tool_call_id: String,
        tool_name: String,
        result: ToolOutput,
        is_error: bool,
    },
}
