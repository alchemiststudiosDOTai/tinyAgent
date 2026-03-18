use std::{collections::HashMap, sync::Arc};

use anyhow::Result;
use async_trait::async_trait;
use serde_json::Value;
use tokio::sync::RwLock;

use crate::types::{ToolDefinition, ToolExecutionContext, ToolOutput};

pub type ToolUpdateCallback = Arc<dyn Fn(ToolOutput) + Send + Sync>;

#[async_trait]
pub trait AgentTool: Send + Sync {
    fn definition(&self) -> ToolDefinition;

    async fn execute(
        &self,
        context: ToolExecutionContext,
        args: Value,
        on_update: ToolUpdateCallback,
    ) -> Result<ToolOutput>;
}

#[derive(Default, Clone)]
pub struct ToolRegistry {
    tools: Arc<RwLock<HashMap<String, Arc<dyn AgentTool>>>>,
}

impl ToolRegistry {
    pub async fn register(&self, tool: Arc<dyn AgentTool>) {
        let name = tool.definition().name.clone();
        self.tools.write().await.insert(name, tool);
    }

    pub async fn definitions(&self) -> Vec<ToolDefinition> {
        let tools = self.tools.read().await;
        let mut definitions = tools
            .values()
            .map(|tool| tool.definition())
            .collect::<Vec<_>>();
        definitions.sort_by(|left, right| left.name.cmp(&right.name));
        definitions
    }

    pub async fn get(&self, name: &str) -> Option<Arc<dyn AgentTool>> {
        self.tools.read().await.get(name).cloned()
    }
}
