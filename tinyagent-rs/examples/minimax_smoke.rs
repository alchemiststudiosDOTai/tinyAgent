use tinyagent_rs::{Agent, AlchemyMinimaxProvider, ModelConfig, ThinkingLevel};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let prompt = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "Reply in one short sentence: what model are you?".to_string());

    let model = ModelConfig {
        provider: "minimax".to_string(),
        id: "MiniMax-M2.1".to_string(),
        api: "minimax-completions".to_string(),
        thinking_level: ThinkingLevel::Off,
    };

    let mut agent = Agent::builder(Box::new(AlchemyMinimaxProvider::default()))
        .model(model)
        .build()
        .await?;

    let result = agent.prompt(prompt).await?;
    if let Some(text) = result {
        println!("{}", text.trim());
    }

    Ok(())
}
