use std::sync::Arc;

use anyhow::Result;
use async_trait::async_trait;
use serde_json::{Value, json};
use tinyagent_rs::{
    Agent, AgentTool, AlchemyMinimaxProvider, ModelConfig, ThinkingLevel, ToolDefinition,
    ToolExecutionContext, ToolOutput, ToolUpdateCallback,
};

struct GetMagicWordTool;

#[async_trait]
impl AgentTool for GetMagicWordTool {
    fn definition(&self) -> ToolDefinition {
        ToolDefinition::new(
            "get_magic_word",
            "Returns the magic word. Call this instead of guessing.",
            json!({
                "type": "object",
                "properties": {},
                "additionalProperties": false
            }),
        )
    }

    async fn execute(
        &self,
        _context: ToolExecutionContext,
        _args: Value,
        _on_update: ToolUpdateCallback,
    ) -> Result<ToolOutput> {
        Ok(ToolOutput::from_text("CITRUS_TOOL_RESULT"))
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let model = ModelConfig {
        provider: "minimax".to_string(),
        id: "MiniMax-M2.1".to_string(),
        api: "minimax-completions".to_string(),
        thinking_level: ThinkingLevel::Off,
    };

    let mut agent = Agent::builder(Box::new(AlchemyMinimaxProvider::default()))
        .model(model)
        .tool(Arc::new(GetMagicWordTool))
        .build()
        .await?;

    let first = agent
        .prompt("You must call the get_magic_word tool exactly once. After the tool returns, answer with only the returned value and nothing else.")
        .await?;
    println!("TURN1 {:?}", first);

    let second = agent
        .prompt("What was the exact value returned by the tool in the previous turn? Answer with only that value.")
        .await?;
    println!("TURN2 {:?}", second);

    Ok(())
}
