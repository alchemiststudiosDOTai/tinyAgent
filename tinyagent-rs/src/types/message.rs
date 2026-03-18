use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

use super::{MessageContent, TextContent, ThinkingContent, ToolCallContent, ToolOutput};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct UserMessage {
    pub content: Vec<MessageContent>,
}

impl UserMessage {
    pub fn from_text(text: impl Into<String>) -> Self {
        Self {
            content: vec![MessageContent::Text(TextContent::new(text))],
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct AssistantMessage {
    pub content: Vec<MessageContent>,
    pub stop_reason: Option<String>,
}

impl AssistantMessage {
    pub fn from_text(text: impl Into<String>) -> Self {
        Self {
            content: vec![MessageContent::Text(TextContent::new(text))],
            stop_reason: Some("stop".to_string()),
        }
    }

    pub fn push_text_delta(&mut self, delta: &str) {
        match self.content.last_mut() {
            Some(MessageContent::Text(text)) => text.text.push_str(delta),
            _ => self
                .content
                .push(MessageContent::Text(TextContent::new(delta.to_string()))),
        }
    }

    pub fn push_thinking_delta(&mut self, delta: &str) {
        match self.content.last_mut() {
            Some(MessageContent::Thinking(thinking)) => thinking.text.push_str(delta),
            _ => self
                .content
                .push(MessageContent::Thinking(ThinkingContent::new(
                    delta.to_string(),
                ))),
        }
    }

    pub fn upsert_tool_call(&mut self, tool_call: ToolCallContent) {
        if let Some(MessageContent::ToolCall(existing)) = self
            .content
            .iter_mut()
            .find(|content| matches!(content, MessageContent::ToolCall(candidate) if candidate.id == tool_call.id))
        {
            *existing = tool_call;
        } else {
            self.content.push(MessageContent::ToolCall(tool_call));
        }
    }

    pub fn tool_calls(&self) -> Vec<ToolCallContent> {
        self.content
            .iter()
            .filter_map(|content| match content {
                MessageContent::ToolCall(tool_call) => Some(tool_call.clone()),
                _ => None,
            })
            .collect()
    }

    pub fn text(&self) -> String {
        self.content
            .iter()
            .filter_map(|content| match content {
                MessageContent::Text(text) => Some(text.text.as_str()),
                _ => None,
            })
            .collect()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ToolResultMessage {
    pub tool_call_id: String,
    pub tool_name: String,
    pub content: Vec<MessageContent>,
    pub details: Map<String, Value>,
    pub is_error: bool,
}

impl ToolResultMessage {
    pub fn from_output(tool_call: &ToolCallContent, output: ToolOutput, is_error: bool) -> Self {
        Self {
            tool_call_id: tool_call.id.clone(),
            tool_name: tool_call.name.clone(),
            content: output.content,
            details: output.details,
            is_error,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(tag = "role", rename_all = "snake_case")]
pub enum AgentMessage {
    User(UserMessage),
    Assistant(AssistantMessage),
    ToolResult(ToolResultMessage),
}

impl AgentMessage {
    pub fn user_text(text: impl Into<String>) -> Self {
        Self::User(UserMessage::from_text(text))
    }
}

pub fn extract_text(message: &AgentMessage) -> String {
    match message {
        AgentMessage::User(user) => user
            .content
            .iter()
            .filter_map(|content| match content {
                MessageContent::Text(text) => Some(text.text.as_str()),
                _ => None,
            })
            .collect(),
        AgentMessage::Assistant(assistant) => assistant.text(),
        AgentMessage::ToolResult(result) => result
            .content
            .iter()
            .filter_map(|content| match content {
                MessageContent::Text(text) => Some(text.text.as_str()),
                _ => None,
            })
            .collect(),
    }
}
