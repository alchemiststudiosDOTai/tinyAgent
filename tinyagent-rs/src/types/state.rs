use serde::{Deserialize, Serialize};
use serde_json::Value;

use super::{AgentMessage, ModelConfig};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct AgentLoopConfig {
    pub model: ModelConfig,
    pub temperature: Option<f32>,
    pub max_tokens: Option<u32>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct AgentState {
    pub system_prompt: String,
    pub model: Option<ModelConfig>,
    pub messages: Vec<AgentMessage>,
    pub is_streaming: bool,
    pub error: Option<String>,
    pub provider_state: Option<Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct AgentRunResult {
    pub messages: Vec<AgentMessage>,
    pub final_text: Option<String>,
    pub provider_state: Option<Value>,
}
