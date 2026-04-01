use base64::Engine;
use serde::{Deserialize, Serialize};

use super::tool_call_id::ToolCallId;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "camelCase")]
pub enum Content {
    #[serde(rename = "text")]
    Text {
        #[serde(flatten)]
        inner: TextContent,
    },
    #[serde(rename = "thinking")]
    Thinking {
        #[serde(flatten)]
        inner: ThinkingContent,
    },
    #[serde(rename = "image")]
    Image {
        #[serde(flatten)]
        inner: ImageContent,
    },
    #[serde(rename = "toolCall")]
    ToolCall {
        #[serde(flatten)]
        inner: ToolCall,
    },
}

impl Content {
    pub fn text(text: impl Into<String>) -> Self {
        Self::Text {
            inner: TextContent {
                text: text.into(),
                text_signature: None,
            },
        }
    }

    pub fn thinking(thinking: impl Into<String>) -> Self {
        Self::Thinking {
            inner: ThinkingContent {
                thinking: thinking.into(),
                thinking_signature: None,
            },
        }
    }

    pub fn tool_call(
        id: impl Into<ToolCallId>,
        name: impl Into<String>,
        arguments: serde_json::Value,
    ) -> Self {
        Self::ToolCall {
            inner: ToolCall {
                id: id.into(),
                name: name.into(),
                arguments,
                thought_signature: None,
            },
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TextContent {
    pub text: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub text_signature: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThinkingContent {
    pub thinking: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub thinking_signature: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ImageContent {
    pub data: Vec<u8>,
    pub mime_type: String,
}

impl ImageContent {
    pub fn from_base64(data: &str, mime_type: String) -> Result<Self, base64::DecodeError> {
        Ok(Self {
            data: base64::engine::general_purpose::STANDARD.decode(data)?,
            mime_type,
        })
    }

    pub fn to_base64(&self) -> String {
        base64::engine::general_purpose::STANDARD.encode(&self.data)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    pub id: ToolCallId,
    pub name: String,
    pub arguments: serde_json::Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub thought_signature: Option<String>,
}
