use serde::{Deserialize, Serialize};

use super::{AgentMessage, ToolDefinition};

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq)]
pub struct Context {
    pub system_prompt: String,
    pub messages: Vec<AgentMessage>,
    pub tools: Vec<ToolDefinition>,
}

pub type AgentContext = Context;
