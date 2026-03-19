use tinyagent_rs::{Agent, AgentMessage, AgentOptions, Model};

#[tokio::test]
#[ignore]
async fn live_minimax_smoke() -> tinyagent_rs::Result<()> {
    if std::env::var("RUN_LIVE_ALCHEMY_TESTS").ok().as_deref() != Some("1") {
        return Ok(());
    }

    let _ = dotenv::dotenv();
    if std::env::var("MINIMAX_API_KEY").is_err() {
        return Ok(());
    }

    let agent = Agent::new(AgentOptions {
        model: Some(Model {
            provider: "minimax".to_string(),
            id: "MiniMax-M2.5".to_string(),
            api: "minimax-completions".to_string(),
            ..Model::default()
        }),
        ..AgentOptions::default()
    });

    let response = agent.prompt("Reply with the exact word PONG.").await?;
    let text = tinyagent_rs::extract_text(&AgentMessage::Assistant(response));
    assert!(text.to_uppercase().contains("PONG"));
    Ok(())
}
