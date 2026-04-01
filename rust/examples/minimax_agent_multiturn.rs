use std::error::Error;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use alchemy_llm::minimax_m2_7;
use serde_json::{Map, Value, json};
use tinyagent_core::{
    Agent, AgentEvent, AgentOptions, AgentTool, AgentToolResult, AlchemyBackend, TextContent,
    ToolResultContent,
};

fn json_object(value: Value) -> Map<String, Value> {
    match value {
        Value::Object(map) => map,
        _ => Map::new(),
    }
}

fn render_number(value: f64) -> String {
    if value.fract() == 0.0 {
        (value as i64).to_string()
    } else {
        value.to_string()
    }
}

fn extract_number(args: &Map<String, Value>, key: &str) -> Result<f64, String> {
    match args.get(key).and_then(Value::as_f64) {
        Some(value) => Ok(value),
        None => Err(format!("missing numeric argument '{key}'")),
    }
}

fn text_result(text: impl Into<String>) -> AgentToolResult {
    AgentToolResult {
        content: vec![ToolResultContent::Text(TextContent {
            text: Some(text.into()),
            ..Default::default()
        })],
        details: Map::new(),
    }
}

fn multiply_tool() -> AgentTool {
    AgentTool {
        name: "multiply_numbers".to_string(),
        description: "Multiply two numbers and return the exact numeric result.".to_string(),
        parameters: json_object(json!({
            "type": "object",
            "properties": {
                "a": { "type": "number" },
                "b": { "type": "number" }
            },
            "required": ["a", "b"]
        })),
        label: "multiply".to_string(),
        execute: Some(Arc::new(|tool_call_id, args, _signal, on_update| {
            Box::pin(async move {
                on_update(text_result(format!("running {tool_call_id}")));

                let a = match extract_number(&args, "a") {
                    Ok(value) => value,
                    Err(error) => return text_result(error),
                };
                let b = match extract_number(&args, "b") {
                    Ok(value) => value,
                    Err(error) => return text_result(error),
                };

                AgentToolResult {
                    content: vec![ToolResultContent::Text(TextContent {
                        text: Some(render_number(a * b)),
                        ..Default::default()
                    })],
                    details: json_object(json!({
                        "tool_call_id": tool_call_id,
                        "operation": "multiply",
                        "a": a,
                        "b": b,
                        "result": a * b
                    })),
                }
            })
        })),
    }
}

fn add_tool() -> AgentTool {
    AgentTool {
        name: "add_numbers".to_string(),
        description: "Add two numbers and return the exact numeric result.".to_string(),
        parameters: json_object(json!({
            "type": "object",
            "properties": {
                "a": { "type": "number" },
                "b": { "type": "number" }
            },
            "required": ["a", "b"]
        })),
        label: "add".to_string(),
        execute: Some(Arc::new(|tool_call_id, args, _signal, on_update| {
            Box::pin(async move {
                on_update(text_result(format!("running {tool_call_id}")));

                let a = match extract_number(&args, "a") {
                    Ok(value) => value,
                    Err(error) => return text_result(error),
                };
                let b = match extract_number(&args, "b") {
                    Ok(value) => value,
                    Err(error) => return text_result(error),
                };

                AgentToolResult {
                    content: vec![ToolResultContent::Text(TextContent {
                        text: Some(render_number(a + b)),
                        ..Default::default()
                    })],
                    details: json_object(json!({
                        "tool_call_id": tool_call_id,
                        "operation": "add",
                        "a": a,
                        "b": b,
                        "result": a + b
                    })),
                }
            })
        })),
    }
}

fn digits_only(text: &str) -> String {
    text.chars().filter(|char| char.is_ascii_digit()).collect()
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let backend = AlchemyBackend::new(minimax_m2_7());
    let mut agent = Agent::new(AgentOptions {
        stream_fn: Some(backend.stream_fn()),
        ..Default::default()
    });
    agent.set_model(backend.runtime_model());
    agent.set_system_prompt(
        "You are a strict arithmetic agent. Always use the provided tools for arithmetic. \
         When the user refers to a previous result, resolve it from the conversation. \
         After the tool returns, answer with the exact number only.",
    );
    agent.set_tools(vec![multiply_tool(), add_tool()]);

    let tool_call_count = Arc::new(AtomicUsize::new(0));
    let tool_call_counter = Arc::clone(&tool_call_count);
    agent.subscribe(Arc::new(move |event| {
        if matches!(event, AgentEvent::ToolExecutionStart(_)) {
            tool_call_counter.fetch_add(1, Ordering::SeqCst);
        }
    }));

    println!("running turn 1...");
    let turn_1 = agent
        .prompt_text("What is 123 times 456? Use a tool.")
        .await?;
    println!("turn_1={turn_1}");

    println!("running turn 2...");
    let turn_2 = agent
        .prompt_text("Take that previous result and add 10 using a tool.")
        .await?;
    println!("turn_2={turn_2}");

    let tool_calls = tool_call_count.load(Ordering::SeqCst);
    println!("tool_call_count={tool_calls}");
    println!("message_count={}", agent.state().messages.len());

    if tool_calls < 2 {
        return Err(std::io::Error::other(format!(
            "expected at least 2 tool calls, got {tool_calls}"
        ))
        .into());
    }

    let turn_1_digits = digits_only(&turn_1);
    if !turn_1_digits.contains("56088") {
        return Err(std::io::Error::other(format!(
            "expected first turn to contain 56088, got '{turn_1}'"
        ))
        .into());
    }

    let turn_2_digits = digits_only(&turn_2);
    if !turn_2_digits.contains("56098") {
        return Err(std::io::Error::other(format!(
            "expected second turn to contain 56098, got '{turn_2}'"
        ))
        .into());
    }

    Ok(())
}
