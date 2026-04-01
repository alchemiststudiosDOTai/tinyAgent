use serde::{Deserialize, Serialize};
use std::fmt::{Display, Formatter};

/// Canonical tool call identifier used to correlate tool calls and tool results.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
#[serde(transparent)]
pub struct ToolCallId(String);

impl ToolCallId {
    pub fn as_str(&self) -> &str {
        &self.0
    }

    pub fn is_empty(&self) -> bool {
        self.0.is_empty()
    }

    pub fn into_inner(self) -> String {
        self.0
    }
}

impl Display for ToolCallId {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl AsRef<str> for ToolCallId {
    fn as_ref(&self) -> &str {
        self.as_str()
    }
}

impl From<String> for ToolCallId {
    fn from(value: String) -> Self {
        Self(value)
    }
}

impl From<&str> for ToolCallId {
    fn from(value: &str) -> Self {
        Self(value.to_string())
    }
}

impl From<ToolCallId> for String {
    fn from(value: ToolCallId) -> Self {
        value.0
    }
}

#[cfg(test)]
mod tests {
    use super::ToolCallId;

    #[test]
    fn tool_call_id_round_trip() {
        let id = ToolCallId::from("call-123");
        assert_eq!(id.as_str(), "call-123");
        assert_eq!(id.to_string(), "call-123");
        assert_eq!(id.into_inner(), "call-123");
    }
}
