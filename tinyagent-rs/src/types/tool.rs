use serde::{Deserialize, Serialize};
use serde_json::{Map, Value, json};

use super::MessageContent;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ToolDefinition {
    pub name: String,
    pub description: String,
    pub parameters: Value,
}

impl ToolDefinition {
    pub fn new(name: impl Into<String>, description: impl Into<String>, parameters: Value) -> Self {
        Self {
            name: name.into(),
            description: description.into(),
            parameters,
        }
    }
}

impl Default for ToolDefinition {
    fn default() -> Self {
        Self {
            name: String::new(),
            description: String::new(),
            parameters: json!({}),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct ToolExecutionContext {
    pub tool_call_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct ToolOutput {
    pub content: Vec<MessageContent>,
    pub details: Map<String, Value>,
}

impl ToolOutput {
    pub fn from_text(text: impl Into<String>) -> Self {
        Self {
            content: vec![MessageContent::text(text)],
            details: Map::new(),
        }
    }
}
