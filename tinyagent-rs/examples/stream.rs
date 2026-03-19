use futures::StreamExt;
use tinyagent_rs::{Agent, AgentEvent, AgentOptions, Model};

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

    let mut stream = agent.stream("Count to three.")?;
    while let Some(event) = stream.next().await {
        match event {
            AgentEvent::MessageUpdate {
                assistant_message_event:
                    Some(tinyagent_rs::AssistantMessageEvent::TextDelta { delta, .. }),
                ..
            } => print!("{delta}"),
            AgentEvent::ToolExecutionStart { tool_name, .. } => {
                println!("\nusing tool: {tool_name}");
            }
            _ => {}
        }
    }

    let _ = stream.result().await?;
    println!();
    Ok(())
}
