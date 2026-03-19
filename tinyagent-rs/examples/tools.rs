use serde_json::json;
use tinyagent_rs::{
    Agent, AgentOptions, AgentTool, AgentToolResult, Model, TextContent, UserContent,
};

#[tokio::main]
async fn main() -> tinyagent_rs::Result<()> {
    let echo = AgentTool::new(
        "echo",
        "Echo a value",
        json!({"type": "object"}),
        |_id, args, _abort, _on_update| async move {
            Ok(AgentToolResult {
                content: vec![UserContent::Text(TextContent::new(
                    args.get("value")
                        .and_then(|value| value.as_str())
                        .unwrap_or_default(),
                ))],
                details: json!({"echoed": true}),
            })
        },
    );

    let agent = Agent::new(AgentOptions {
        model: Some(Model {
            provider: "minimax".to_string(),
            id: "MiniMax-M2.5".to_string(),
            api: "minimax-completions".to_string(),
            ..Model::default()
        }),
        tools: vec![echo],
        ..AgentOptions::default()
    });

    let response = agent
        .prompt("If useful, call the echo tool with {\"value\":\"hello\"}.")
        .await?;
    println!(
        "{}",
        tinyagent_rs::extract_text(&tinyagent_rs::AgentMessage::Assistant(response))
    );
    Ok(())
}
