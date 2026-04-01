use alchemy_llm::types::{AssistantMessageEvent, Context, Message, UserContent, UserMessage};
use alchemy_llm::{minimax_m2_7, stream};
use futures::StreamExt;

#[tokio::main]
async fn main() -> alchemy_llm::Result<()> {
    println!("Testing MiniMax-M2.7...");

    let model = minimax_m2_7();
    println!("Model: {} (id: {})", model.name, model.id);
    println!("Provider: {:?}", model.provider);
    println!("Base URL: {}", model.base_url);
    println!("Reasoning: {}", model.reasoning);
    println!();

    let context = Context {
        system_prompt: Some("You are a helpful assistant. Keep responses brief.".to_string()),
        messages: vec![Message::User(UserMessage {
            content: UserContent::Text(
                "Say 'MiniMax M2.7 is working!' and nothing else.".to_string(),
            ),
            timestamp: 0,
        })],
        tools: None,
    };

    println!("Sending request...");
    let mut stream = stream(&model, &context, None)?;

    let mut content_received = false;
    while let Some(event) = stream.next().await {
        match event {
            AssistantMessageEvent::TextStart { .. } => println!("[TextStart]"),
            AssistantMessageEvent::TextDelta { delta, .. } => {
                print!("{}", delta);
                content_received = true;
            }
            AssistantMessageEvent::TextEnd { .. } => {
                println!();
                println!("[TextEnd]");
            }
            AssistantMessageEvent::ThinkingStart { .. } => println!("[ThinkingStart]"),
            AssistantMessageEvent::ThinkingDelta { delta, .. } => {
                println!("[Thinking: {}]", delta);
            }
            AssistantMessageEvent::ThinkingEnd { .. } => println!("[ThinkingEnd]"),
            AssistantMessageEvent::Done { message, .. } => {
                println!();
                println!("=== Complete ===");
                println!("Stop reason: {:?}", message.stop_reason);
                println!(
                    "Usage: {} input, {} output, {} total tokens",
                    message.usage.input, message.usage.output, message.usage.total_tokens
                );
                break;
            }
            AssistantMessageEvent::Error { error, .. } => {
                eprintln!("Error: {:?}", error);
                break;
            }
            _ => {}
        }
    }

    if content_received {
        println!("\n✓ MiniMax-M2.7 test passed!");
    } else {
        println!("\n✗ No content received");
    }

    Ok(())
}
