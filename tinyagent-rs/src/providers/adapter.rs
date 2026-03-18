use anyhow::Result;
use async_trait::async_trait;
use futures::stream::BoxStream;
use serde_json::Value;

use crate::types::{AgentContext, AssistantMessageEvent, ModelConfig, ToolDefinition};

#[derive(Debug, Clone, Default)]
pub struct ProviderOptions {
    pub temperature: Option<f32>,
    pub max_tokens: Option<u32>,
    pub continuation: Option<Value>,
}

#[derive(Debug, Clone)]
pub struct ProviderTurnRequest {
    pub model: ModelConfig,
    pub context: AgentContext,
    pub tools: Vec<ToolDefinition>,
    pub options: ProviderOptions,
}

pub type ProviderEventStream = BoxStream<'static, Result<AssistantMessageEvent>>;

pub struct ProviderTurnResponse {
    pub events: ProviderEventStream,
    pub continuation: Option<Value>,
}

#[async_trait]
pub trait ProviderAdapter: Send + Sync {
    async fn stream_turn(&mut self, request: ProviderTurnRequest) -> Result<ProviderTurnResponse>;
}
