use std::sync::Arc;
use std::time::Duration;
use tinyagent_rs::{
    Agent, AgentOptions, AgentState, AssistantContent, AssistantMessage, AssistantMessageEvent,
    AssistantStreamResponse, Model, StopReason, StreamFn, TextContent,
};
use tokio::time::{sleep, timeout};

fn test_model() -> Model {
    Model {
        provider: "openai".to_string(),
        id: "test-model".to_string(),
        api: "openai-completions".to_string(),
        base_url: Some("https://example.com/v1/chat/completions".to_string()),
        ..Model::default()
    }
}

#[tokio::test]
async fn abort_wait_for_idle_and_subscribe_restore_non_streaming_state() {
    let stream_fn: StreamFn = Arc::new(|_request| {
        Box::pin(async move {
            let (stream, event_tx, result_tx) = AssistantStreamResponse::channel();
            tokio::spawn(async move {
                let _ = event_tx.send(AssistantMessageEvent::Start {
                    partial: AssistantMessage::default(),
                });
                sleep(Duration::from_millis(50)).await;
                let _ = event_tx.send(AssistantMessageEvent::TextDelta {
                    content_index: 0,
                    delta: "partial".to_string(),
                    partial: AssistantMessage {
                        content: vec![Some(AssistantContent::Text(TextContent::new("partial")))],
                        ..AssistantMessage::default()
                    },
                });
                sleep(Duration::from_millis(100)).await;
                let final_message = AssistantMessage {
                    content: vec![Some(AssistantContent::Text(TextContent::new("done")))],
                    stop_reason: Some(StopReason::Stop),
                    api: Some("openai-completions".to_string()),
                    provider: Some("openai".to_string()),
                    model: Some("test-model".to_string()),
                    ..AssistantMessage::default()
                };
                let _ = result_tx.send(Ok(final_message));
            });

            Ok(stream)
        })
    });

    let agent = Agent::new(AgentOptions {
        model: Some(test_model()),
        stream_fn: Some(stream_fn),
        ..AgentOptions::default()
    });

    let mut subscriber = agent.subscribe();
    let _stream = agent.stream("hello").expect("agent stream should start");
    sleep(Duration::from_millis(20)).await;
    agent.abort();
    agent.wait_for_idle().await;

    let state: AgentState = agent.state();
    assert!(!state.is_streaming);
    assert!(state
        .messages
        .iter()
        .any(|message| matches!(message, tinyagent_rs::AgentMessage::Assistant(message) if message.stop_reason == Some(StopReason::Aborted))));

    let end_event = timeout(Duration::from_secs(1), async {
        loop {
            if let Ok(event) = subscriber.recv().await {
                if matches!(event, tinyagent_rs::AgentEvent::AgentEnd { .. }) {
                    break event;
                }
            }
        }
    })
    .await
    .expect("terminal event should arrive");

    assert!(matches!(
        end_event,
        tinyagent_rs::AgentEvent::AgentEnd { .. }
    ));
}
