use std::sync::Arc;

use anyhow::Result;

use crate::{
    providers::ProviderAdapter,
    tools::{AgentTool, ToolRegistry},
    types::{AgentLoopConfig, AgentState, ModelConfig},
};

use super::facade::Agent;

pub struct AgentBuilder {
    provider: Box<dyn ProviderAdapter>,
    system_prompt: String,
    model: Option<ModelConfig>,
    temperature: Option<f32>,
    max_tokens: Option<u32>,
    tools: Vec<Arc<dyn AgentTool>>,
}

impl AgentBuilder {
    pub fn new(provider: Box<dyn ProviderAdapter>) -> Self {
        Self {
            provider,
            system_prompt: String::new(),
            model: None,
            temperature: None,
            max_tokens: None,
            tools: Vec::new(),
        }
    }

    pub fn system_prompt(mut self, system_prompt: impl Into<String>) -> Self {
        self.system_prompt = system_prompt.into();
        self
    }

    pub fn model(mut self, model: ModelConfig) -> Self {
        self.model = Some(model);
        self
    }

    pub fn temperature(mut self, temperature: f32) -> Self {
        self.temperature = Some(temperature);
        self
    }

    pub fn max_tokens(mut self, max_tokens: u32) -> Self {
        self.max_tokens = Some(max_tokens);
        self
    }

    pub fn tool(mut self, tool: Arc<dyn AgentTool>) -> Self {
        self.tools.push(tool);
        self
    }

    pub async fn build(self) -> Result<Agent> {
        let registry = ToolRegistry::default();
        for tool in self.tools {
            registry.register(tool).await;
        }

        let model = self.model.unwrap_or_default();
        let state = AgentState {
            system_prompt: self.system_prompt,
            model: Some(model.clone()),
            ..AgentState::default()
        };
        let config = AgentLoopConfig {
            model,
            temperature: self.temperature,
            max_tokens: self.max_tokens,
        };

        Ok(Agent::new(self.provider, registry, config, state))
    }
}
