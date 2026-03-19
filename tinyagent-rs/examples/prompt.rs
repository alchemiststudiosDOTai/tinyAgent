use tinyagent_rs::{Agent, AgentOptions, Model};

#[tokio::main]
async fn main() -> tinyagent_rs::Result<()> {
    let agent = Agent::new(AgentOptions {
        model: Some(Model {
            provider: "minimax".to_string(),
            id: "MiniMax-M2.5".to_string(),
            api: "minimax-completions".to_string(),
            ..Model::default()
        }),
        ..AgentOptions::default()
    });

    let response = agent.prompt("Reply with a short greeting.").await?;
    println!(
        "{}",
        tinyagent_rs::extract_text(&tinyagent_rs::AgentMessage::Assistant(response))
    );
    Ok(())
}
