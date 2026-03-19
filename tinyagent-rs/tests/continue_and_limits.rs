use serde_json::json;
use std::sync::{Arc, Mutex};
use std::time::Duration;
use tinyagent_rs::{
    agent_loop, agent_loop_continue, AgentContext, AgentError, AgentLoopConfig, AgentMessage,
    AgentTool, AgentToolResult, AssistantContent, AssistantMessage, AssistantStreamResponse, Model,
    StopReason, StreamFn, StreamOptions, TextContent, ToolCallContent, ToolResultMessage,
    UserContent, UserMessage,
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

fn user_message(text: &str) -> AgentMessage {
    AgentMessage::User(UserMessage::text(text))
}

fn tool_result_message(tool_call_id: &str) -> AgentMessage {
    AgentMessage::ToolResult(ToolResultMessage {
        tool_call_id: Some(tool_call_id.to_string()),
        tool_name: Some("echo".to_string()),
        content: vec![UserContent::Text(TextContent::new("tool"))],
        ..ToolResultMessage::default()
    })
}

fn assistant_message(
    content: Vec<Option<AssistantContent>>,
    stop_reason: StopReason,
) -> AssistantMessage {
    AssistantMessage {
        content,
        stop_reason: Some(stop_reason),
        api: Some("openai-completions".to_string()),
        provider: Some("openai".to_string()),
        model: Some("test-model".to_string()),
        ..AssistantMessage::default()
    }
}

fn final_text_stream(text: &'static str) -> StreamFn {
    Arc::new(move |_request| {
        Box::pin(async move {
            let final_message = assistant_message(
                vec![Some(AssistantContent::Text(TextContent::new(text)))],
                StopReason::Stop,
            );
            Ok(AssistantStreamResponse::from_events(
                Vec::new(),
                Ok(final_message),
            ))
        })
    })
}

#[tokio::test]
async fn continue_rejects_assistant_last_history() {
    let config = AgentLoopConfig {
        model: test_model(),
        stream_fn: Some(final_text_stream("ok")),
        stream_options: StreamOptions::default(),
        max_turns: 1,
        get_steering_messages: None,
        get_follow_up_messages: None,
    };

    let context = AgentContext {
        messages: vec![AgentMessage::Assistant(assistant_message(
            vec![Some(AssistantContent::Text(TextContent::new("done")))],
            StopReason::Stop,
        ))],
        ..AgentContext::default()
    };

    let error = match agent_loop_continue(context, config, None) {
        Ok(_) => panic!("assistant-last should fail"),
        Err(error) => error,
    };
    assert!(matches!(error, AgentError::CannotContinueFromAssistant));
}

#[tokio::test]
async fn continue_accepts_user_last_and_tool_result_last_contexts() {
    for messages in [
        vec![user_message("hello")],
        vec![tool_result_message("call-1")],
    ] {
        let config = AgentLoopConfig {
            model: test_model(),
            stream_fn: Some(final_text_stream("continued")),
            stream_options: StreamOptions::default(),
            max_turns: 1,
            get_steering_messages: None,
            get_follow_up_messages: None,
        };

        let context = AgentContext {
            messages,
            ..AgentContext::default()
        };

        let stream = agent_loop_continue(context, config, None).expect("continue should start");
        let messages = stream.result().await.expect("continue should succeed");
        let assistant = messages
            .into_iter()
            .find_map(|message| match message {
                AgentMessage::Assistant(message) => Some(message),
                _ => None,
            })
            .expect("assistant message should be produced");
        assert_eq!(assistant.model.as_deref(), Some("test-model"));
    }
}

#[tokio::test]
async fn appends_tool_results_in_original_call_order_and_enforces_max_turns() {
    let turn_counter = Arc::new(Mutex::new(0usize));
    let stream_fn: StreamFn = {
        let turn_counter = Arc::clone(&turn_counter);
        Arc::new(move |request| {
            let turn_counter = Arc::clone(&turn_counter);
            Box::pin(async move {
                let mut turn = turn_counter.lock().expect("turn counter lock poisoned");
                *turn += 1;

                let final_message = if request
                    .context
                    .messages
                    .iter()
                    .any(|message| matches!(message, tinyagent_rs::Message::ToolResult(_)))
                {
                    assistant_message(
                        vec![Some(AssistantContent::Text(TextContent::new("done")))],
                        StopReason::Stop,
                    )
                } else {
                    assistant_message(
                        vec![
                            Some(AssistantContent::ToolCall(ToolCallContent {
                                id: Some("call-a".to_string()),
                                name: Some("slow".to_string()),
                                arguments: json!({"value": "A"}),
                                partial_json: None,
                                ..ToolCallContent::default()
                            })),
                            Some(AssistantContent::ToolCall(ToolCallContent {
                                id: Some("call-b".to_string()),
                                name: Some("fast".to_string()),
                                arguments: json!({"value": "B"}),
                                partial_json: None,
                                ..ToolCallContent::default()
                            })),
                        ],
                        StopReason::ToolUse,
                    )
                };

                Ok(AssistantStreamResponse::from_events(
                    Vec::new(),
                    Ok(final_message),
                ))
            })
        })
    };

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
        stream_fn: Some(stream_fn.clone()),
        stream_options: StreamOptions::default(),
        max_turns: 4,
        get_steering_messages: None,
        get_follow_up_messages: None,
    };
    let context = AgentContext {
        tools: vec![slow.clone(), fast.clone()],
        ..AgentContext::default()
    };

    let stream = agent_loop(vec![user_message("start")], context, config, None);
    let messages = stream.result().await.expect("loop should succeed");
    let tool_results = messages
        .into_iter()
        .filter_map(|message| match message {
            AgentMessage::ToolResult(message) => Some(message),
            _ => None,
        })
        .collect::<Vec<_>>();

    assert_eq!(tool_results.len(), 2);
    assert_eq!(tool_results[0].tool_call_id.as_deref(), Some("call-a"));
    assert_eq!(tool_results[1].tool_call_id.as_deref(), Some("call-b"));

    let limited_config = AgentLoopConfig {
        max_turns: 1,
        stream_fn: Some(stream_fn),
        model: test_model(),
        stream_options: StreamOptions::default(),
        get_steering_messages: None,
        get_follow_up_messages: None,
    };
    let limited_context = AgentContext {
        tools: vec![slow, fast],
        ..AgentContext::default()
    };

    let limited_stream = agent_loop(
        vec![user_message("start")],
        limited_context,
        limited_config,
        None,
    );
    let error = limited_stream
        .result()
        .await
        .expect_err("second turn should exceed limit");
    assert!(matches!(error, AgentError::MaxTurnsExceeded { .. }));
}
