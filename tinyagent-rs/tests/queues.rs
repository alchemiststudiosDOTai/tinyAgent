use serde_json::json;
use std::sync::{
    atomic::{AtomicBool, AtomicUsize, Ordering},
    Arc,
};
use std::time::Duration;
use tinyagent_rs::{
    agent_loop, AgentContext, AgentLoopConfig, AgentMessage, AgentTool, AgentToolResult,
    AssistantContent, AssistantMessage, AssistantStreamResponse, Model, StopReason, StreamFn,
    StreamOptions, TextContent, ToolCallContent, UserContent, UserMessage,
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

fn assistant_text(text: &str) -> AssistantMessage {
    AssistantMessage {
        content: vec![Some(AssistantContent::Text(TextContent::new(text)))],
        stop_reason: Some(StopReason::Stop),
        api: Some("openai-completions".to_string()),
        provider: Some("openai".to_string()),
        model: Some("test-model".to_string()),
        ..AssistantMessage::default()
    }
}

#[tokio::test]
async fn steering_is_consumed_before_follow_up_after_tool_batch() {
    let tool_finished = Arc::new(AtomicBool::new(false));
    let steering_returned = Arc::new(AtomicBool::new(false));
    let follow_up_calls = Arc::new(AtomicUsize::new(0));

    let stream_fn: StreamFn = Arc::new(move |request| {
        Box::pin(async move {
            let final_message = if request
                .context
                .messages
                .iter()
                .any(|message| matches!(message, tinyagent_rs::Message::User(UserMessage { content, .. }) if content.iter().any(|block| matches!(block, UserContent::Text(text) if text.text == "steer"))))
            {
                assistant_text("after steering")
            } else if request
                .context
                .messages
                .iter()
                .any(|message| matches!(message, tinyagent_rs::Message::User(UserMessage { content, .. }) if content.iter().any(|block| matches!(block, UserContent::Text(text) if text.text == "follow-up"))))
            {
                assistant_text("after follow up")
            } else if request
                .context
                .messages
                .iter()
                .any(|message| matches!(message, tinyagent_rs::Message::ToolResult(_)))
            {
                assistant_text("base complete")
            } else {
                AssistantMessage {
                    content: vec![Some(AssistantContent::ToolCall(ToolCallContent {
                        id: Some("call-1".to_string()),
                        name: Some("work".to_string()),
                        arguments: json!({}),
                        partial_json: None,
                        ..ToolCallContent::default()
                    }))],
                    stop_reason: Some(StopReason::ToolUse),
                    api: Some("openai-completions".to_string()),
                    provider: Some("openai".to_string()),
                    model: Some("test-model".to_string()),
                    ..AssistantMessage::default()
                }
            };

            Ok(AssistantStreamResponse::from_events(
                Vec::new(),
                Ok(final_message),
            ))
        })
    });

    let tool = AgentTool::new("work", "tool", json!({}), {
        let tool_finished = Arc::clone(&tool_finished);
        move |_id, _args, _abort, _on_update| {
            let tool_finished = Arc::clone(&tool_finished);
            async move {
                sleep(Duration::from_millis(10)).await;
                tool_finished.store(true, Ordering::SeqCst);
                Ok(AgentToolResult {
                    content: vec![UserContent::Text(TextContent::new("worked"))],
                    details: json!({"ok": true}),
                })
            }
        }
    });

    let steering_provider = {
        let tool_finished = Arc::clone(&tool_finished);
        let steering_returned = Arc::clone(&steering_returned);
        Arc::new(
            move || -> futures::future::BoxFuture<'static, Vec<AgentMessage>> {
                let tool_finished = Arc::clone(&tool_finished);
                let steering_returned = Arc::clone(&steering_returned);
                Box::pin(async move {
                    if tool_finished.load(Ordering::SeqCst)
                        && !steering_returned.swap(true, Ordering::SeqCst)
                    {
                        vec![user("steer")]
                    } else {
                        Vec::new()
                    }
                })
            },
        )
    };

    let follow_up_provider = {
        let follow_up_calls = Arc::clone(&follow_up_calls);
        Arc::new(
            move || -> futures::future::BoxFuture<'static, Vec<AgentMessage>> {
                let follow_up_calls = Arc::clone(&follow_up_calls);
                Box::pin(async move {
                    let call = follow_up_calls.fetch_add(1, Ordering::SeqCst);
                    if call == 0 {
                        vec![user("follow-up")]
                    } else {
                        Vec::new()
                    }
                })
            },
        )
    };

    let config = AgentLoopConfig {
        model: test_model(),
        stream_fn: Some(stream_fn),
        stream_options: StreamOptions::default(),
        max_turns: 6,
        get_steering_messages: Some(steering_provider),
        get_follow_up_messages: Some(follow_up_provider),
    };
    let context = AgentContext {
        tools: vec![tool],
        ..AgentContext::default()
    };

    let stream = agent_loop(vec![user("start")], context, config, None);
    let messages = stream.result().await.expect("queue run should succeed");

    let user_texts = messages
        .iter()
        .filter_map(|message| match message {
            AgentMessage::User(UserMessage { content, .. }) => Some(
                content
                    .iter()
                    .filter_map(|content| match content {
                        UserContent::Text(text) => Some(text.text.as_str()),
                        UserContent::Image(_) => None,
                    })
                    .collect::<String>(),
            ),
            _ => None,
        })
        .collect::<Vec<_>>();

    let steer_index = user_texts
        .iter()
        .position(|text| text == "steer")
        .expect("steering message should be present");
    let follow_up_index = user_texts
        .iter()
        .position(|text| text == "follow-up")
        .expect("follow-up message should be present");

    assert!(steer_index < follow_up_index);
}
