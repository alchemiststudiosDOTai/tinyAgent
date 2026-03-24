use alchemy_llm::types::{AssistantMessageEvent, Context, Message, Tool, UserContent, UserMessage};
use alchemy_llm::{minimax_m2_7, stream};
use futures::StreamExt;
use serde_json::json;

#[tokio::main]
async fn main() -> alchemy_llm::Result<()> {
    println!("Testing MiniMax-M2.7 with tool calling...\n");

    let model = minimax_m2_7();
    println!("Model: {}\nProvider: {:?}\n", model.name, model.provider);

    let tools = vec![Tool::new(
        "multiply",
        "Multiply two numbers",
        json!({"type": "object", "properties": {
            "a": {"type": "number"},
            "b": {"type": "number"}
        }, "required": ["a", "b"]}),
    )];

    let context = Context {
        system_prompt: Some("Use the multiply tool for multiplication.".to_string()),
        messages: vec![Message::User(UserMessage {
            content: UserContent::Text("What is 123 times 456?".to_string()),
            timestamp: 0,
        })],
        tools: Some(tools),
    };

    println!("Sending: 'What is 123 times 456?'\n");

    let mut stream = stream(&model, &context, None)?;
    let mut in_thinking = false;

    while let Some(event) = stream.next().await {
        match event {
            AssistantMessageEvent::ThinkingStart { .. } => {
                in_thinking = true;
                print!("[Thinking: ");
            }
            AssistantMessageEvent::ThinkingDelta { delta, .. } => {
                if in_thinking {
                    print!("{}", delta);
                }
            }
            AssistantMessageEvent::ThinkingEnd { .. } => {
                in_thinking = false;
                println!("]");
            }
            AssistantMessageEvent::ToolCallStart { .. } => println!("[ToolCallStart]"),
            AssistantMessageEvent::ToolCallDelta { delta, .. } => print!("{}", delta),
            AssistantMessageEvent::ToolCallEnd { tool_call, .. } => {
                let args = &tool_call.arguments;
                let a = args.get("a").and_then(|v| v.as_f64()).unwrap_or(0.0);
                let b = args.get("b").and_then(|v| v.as_f64()).unwrap_or(0.0);
                println!(
                    "\n[ToolCallEnd] {}({}): {} × {} = {}",
                    tool_call.name,
                    tool_call.id,
                    a,
                    b,
                    a * b
                );
            }
            AssistantMessageEvent::Done { message, .. } => {
                println!("\n=== Complete ===");
                println!(
                    "Stop: {:?}, Usage: {} tokens",
                    message.stop_reason, message.usage.total_tokens
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

    println!("\n✓ Test complete!");
    Ok(())
}
