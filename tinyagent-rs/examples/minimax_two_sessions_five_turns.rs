use std::sync::Arc;

use anyhow::{Result, anyhow};
use async_trait::async_trait;
use serde_json::{Value, json};
use tinyagent_rs::{
    Agent, AgentEvent, AgentTool, AlchemyMinimaxProvider, ModelConfig, ThinkingLevel,
    ToolDefinition, ToolExecutionContext, ToolOutput, ToolUpdateCallback,
};

struct SessionTokenTool {
    token: &'static str,
}

#[async_trait]
impl AgentTool for SessionTokenTool {
    fn definition(&self) -> ToolDefinition {
        ToolDefinition::new(
            "get_session_token",
            "Returns the hidden token for this specific session.",
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
        Ok(ToolOutput::from_text(self.token))
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    run_session("A", "SESSION_ALPHA_48291").await?;
    run_session("B", "SESSION_BRAVO_73104").await?;
    Ok(())
}

async fn run_session(label: &str, expected_token: &'static str) -> Result<()> {
    let model = ModelConfig {
        provider: "minimax".to_string(),
        id: "MiniMax-M2.1".to_string(),
        api: "minimax-completions".to_string(),
        thinking_level: ThinkingLevel::Off,
    };

    let mut agent = Agent::builder(Box::new(AlchemyMinimaxProvider::default()))
        .model(model)
        .tool(Arc::new(SessionTokenTool {
            token: expected_token,
        }))
        .build()
        .await?;

    let prompts = [
        "Use the get_session_token tool to retrieve the hidden token for this session. Then answer with only the token.",
        "What exact token did you retrieve in the previous turn? Answer with only the token.",
        "Repeat the exact session token again. Answer with only the token.",
        "Without explanation, print the same session token one more time.",
        "Final check: output the exact session token again and nothing else.",
    ];

    for (index, prompt) in prompts.iter().enumerate() {
        let (final_text, tool_calls) = run_turn(&mut agent, prompt).await?;
        let normalized = final_text.trim().to_string();
        println!(
            "SESSION {label} TURN {} TOOL_CALLS {}",
            index + 1,
            tool_calls
        );
        println!("SESSION {label} TURN {} OUTPUT {}", index + 1, normalized);

        if normalized != expected_token {
            return Err(anyhow!(
                "session {label} turn {} returned {:?}, expected {:?}",
                index + 1,
                normalized,
                expected_token
            ));
        }
    }

    Ok(())
}

async fn run_turn(agent: &mut Agent, prompt: &str) -> Result<(String, usize)> {
    let mut stream = agent.stream(prompt).await?;
    let mut tool_calls = 0usize;

    while let Some(event) = stream.next().await {
        if matches!(event, AgentEvent::ToolExecutionStart { .. }) {
            tool_calls += 1;
        }
    }

    let result = stream.result().await?;
    Ok((result.final_text.unwrap_or_default(), tool_calls))
}
