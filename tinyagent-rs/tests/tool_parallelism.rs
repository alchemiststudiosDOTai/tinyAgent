use futures::StreamExt;
use serde_json::json;
use std::sync::Arc;
use std::time::Duration;
use tinyagent_rs::{
    agent_loop, AgentContext, AgentEvent, AgentLoopConfig, AgentMessage, AgentTool,
    AgentToolResult, AssistantContent, AssistantMessage, AssistantStreamResponse, Model,
    StopReason, StreamFn, StreamOptions, TextContent, ToolCallContent, UserContent, UserMessage,
};
use tokio::time::sleep;

fn test_model() -> Model {
    Model {
        provider: "openai".to_string(),
        id: "test-model".to_string(),
        api: "openai-completions".to_string(),
        base_url: Some("https://example.com/v1/chat/completions".to_string()),
        ..Model::default()
    }
}

fn user(text: &str) -> AgentMessage {
    AgentMessage::User(UserMessage::text(text))
}

fn tool_call_assistant() -> AssistantMessage {
    AssistantMessage {
        content: vec![
            Some(AssistantContent::ToolCall(ToolCallContent {
                id: Some("call-1".to_string()),
                name: Some("slow".to_string()),
                arguments: json!({"value": "A"}),
                partial_json: None,
                ..ToolCallContent::default()
            })),
            Some(AssistantContent::ToolCall(ToolCallContent {
                id: Some("call-2".to_string()),
                name: Some("fast".to_string()),
                arguments: json!({"value": "B"}),
                partial_json: None,
                ..ToolCallContent::default()
            })),
        ],
        stop_reason: Some(StopReason::ToolUse),
        api: Some("openai-completions".to_string()),
        provider: Some("openai".to_string()),
        model: Some("test-model".to_string()),
        ..AssistantMessage::default()
    }
}

#[tokio::test]
async fn parallel_tool_start_events_precede_end_events_and_replay_is_ordered() {
    let stream_fn: StreamFn = Arc::new(|request| {
        Box::pin(async move {
            let final_message = if request
                .context
                .messages
                .iter()
                .any(|message| matches!(message, tinyagent_rs::Message::ToolResult(_)))
            {
                AssistantMessage {
                    content: vec![Some(AssistantContent::Text(TextContent::new("done")))],
                    stop_reason: Some(StopReason::Stop),
                    api: Some("openai-completions".to_string()),
                    provider: Some("openai".to_string()),
                    model: Some("test-model".to_string()),
                    ..AssistantMessage::default()
                }
            } else {
                tool_call_assistant()
            };

            Ok(AssistantStreamResponse::from_events(
                Vec::new(),
                Ok(final_message),
            ))
        })
    });

    let slow = AgentTool::new(
        "slow",
        "slow tool",
        json!({}),
        |_id, args, _abort, _on_update| async move {
            sleep(Duration::from_millis(40)).await;
            Ok(AgentToolResult {
                content: vec![UserContent::Text(TextContent::new(
                    args.get("value")
                        .and_then(|value| value.as_str())
                        .unwrap_or_default(),
                ))],
                details: json!({"tool": "slow"}),
            })
        },
    );
    let fast = AgentTool::new(
        "fast",
        "fast tool",
        json!({}),
        |_id, args, _abort, _on_update| async move {
            sleep(Duration::from_millis(5)).await;
            Ok(AgentToolResult {
                content: vec![UserContent::Text(TextContent::new(
                    args.get("value")
                        .and_then(|value| value.as_str())
                        .unwrap_or_default(),
                ))],
                details: json!({"tool": "fast"}),
            })
        },
    );

    let config = AgentLoopConfig {
        model: test_model(),
        stream_fn: Some(stream_fn),
        stream_options: StreamOptions::default(),
        max_turns: 4,
        get_steering_messages: None,
        get_follow_up_messages: None,
    };
    let context = AgentContext {
        tools: vec![slow, fast],
        ..AgentContext::default()
    };

    let events = agent_loop(vec![user("start")], context, config, None)
        .collect::<Vec<_>>()
        .await;

    let start_positions = events
        .iter()
        .enumerate()
        .filter_map(|(index, event)| match event {
            AgentEvent::ToolExecutionStart { tool_call_id, .. } => {
                Some((tool_call_id.clone(), index))
            }
            _ => None,
        })
        .collect::<Vec<_>>();
    let end_positions = events
        .iter()
        .enumerate()
        .filter_map(|(index, event)| match event {
            AgentEvent::ToolExecutionEnd { tool_call_id, .. } => {
                Some((tool_call_id.clone(), index))
            }
            _ => None,
        })
        .collect::<Vec<_>>();

    assert_eq!(start_positions.len(), 2);
    assert_eq!(end_positions.len(), 2);
    let max_start = start_positions
        .iter()
        .map(|(_, index)| *index)
        .max()
        .unwrap();
    let min_end = end_positions.iter().map(|(_, index)| *index).min().unwrap();
    assert!(max_start < min_end);

    let tool_result_ids = events
        .iter()
        .filter_map(|event| match event {
            AgentEvent::MessageEnd {
                message: Some(AgentMessage::ToolResult(message)),
            } => message.tool_call_id.clone(),
            _ => None,
        })
        .collect::<Vec<_>>();
    assert_eq!(
        tool_result_ids,
        vec!["call-1".to_string(), "call-2".to_string()]
    );
}
