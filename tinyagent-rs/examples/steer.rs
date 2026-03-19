use futures::StreamExt;
use tinyagent_rs::{Agent, AgentEvent, AgentMessage, AgentOptions, Model, UserMessage};

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

    let mut stream = agent.stream("Start a long answer.")?;
    agent.steer(AgentMessage::User(UserMessage::text(
        "Actually answer with one short sentence.",
    )));

    while let Some(event) = stream.next().await {
        if let AgentEvent::MessageUpdate {
            assistant_message_event:
                Some(tinyagent_rs::AssistantMessageEvent::TextDelta { delta, .. }),
            ..
        } = event
        {
            print!("{delta}");
        }
    }

    let _ = stream.result().await?;
    println!();
    Ok(())
}
