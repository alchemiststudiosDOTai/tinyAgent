use std::sync::Arc;

use anyhow::Result;
use async_trait::async_trait;
use serde_json::{Value, json};
use tinyagent_rs::{
    Agent, AgentEvent, AgentTool, AlchemyMinimaxProvider, ModelConfig, ThinkingLevel,
    ToolDefinition, ToolExecutionContext, ToolOutput, ToolUpdateCallback,
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
    let prompt = std::env::args().nth(1).unwrap_or_else(|| {
        "You must call the get_magic_word tool exactly once. After the tool returns, answer with only the returned value and nothing else.".to_string()
    });

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

    let mut stream = agent.stream(prompt).await?;
    while let Some(event) = stream.next().await {
        match event {
            AgentEvent::ToolExecutionStart {
                tool_call_id,
                tool_name,
                args,
            } => {
                println!("TOOL_START {tool_name} {tool_call_id} {args}");
            }
            AgentEvent::ToolExecutionEnd {
                tool_call_id,
                tool_name,
                result,
                is_error,
            } => {
                println!(
                    "TOOL_END {tool_name} {tool_call_id} error={is_error} result={:?}",
                    result
                );
            }
            _ => {}
        }
    }

    let result = stream.result().await?;
    println!("FINAL {:?}", result.final_text);

    Ok(())
}
