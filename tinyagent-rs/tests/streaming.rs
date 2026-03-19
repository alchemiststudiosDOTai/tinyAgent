use futures::StreamExt;
use std::sync::Arc;
use tinyagent_rs::{
    Agent, AgentOptions, AssistantContent, AssistantMessage, AssistantMessageEvent,
    AssistantStreamResponse, Model, StopReason, StreamFn, TextContent,
};

fn test_model() -> Model {
    Model {
        provider: "openai".to_string(),
        id: "test-model".to_string(),
        api: "openai-completions".to_string(),
        base_url: Some("https://example.com/v1/chat/completions".to_string()),
        ..Model::default()
    }
}

fn partial(thinking: &str, text: &str) -> AssistantMessage {
    AssistantMessage {
        content: vec![
            Some(AssistantContent::Thinking(
                tinyagent_rs::ThinkingContent::new(thinking),
            )),
            Some(AssistantContent::Text(TextContent::new(text))),
        ],
        api: Some("openai-completions".to_string()),
        provider: Some("openai".to_string()),
        model: Some("test-model".to_string()),
        ..AssistantMessage::default()
    }
}

fn synthetic_stream() -> StreamFn {
    Arc::new(|_request| {
        Box::pin(async move {
            let final_message = AssistantMessage {
                stop_reason: Some(StopReason::Stop),
                ..partial("consider carefully", "Hello world")
            };
            let events = vec![
                AssistantMessageEvent::Start {
                    partial: AssistantMessage::default(),
                },
                AssistantMessageEvent::ThinkingStart {
                    content_index: 0,
                    partial: partial("", ""),
                },
                AssistantMessageEvent::ThinkingDelta {
                    content_index: 0,
                    delta: "consider carefully".to_string(),
                    partial: partial("consider carefully", ""),
                },
                AssistantMessageEvent::TextStart {
                    content_index: 1,
                    partial: partial("consider carefully", ""),
                },
                AssistantMessageEvent::TextDelta {
                    content_index: 1,
                    delta: "Hello".to_string(),
                    partial: partial("consider carefully", "Hello"),
                },
                AssistantMessageEvent::TextDelta {
                    content_index: 1,
                    delta: " world".to_string(),
                    partial: partial("consider carefully", "Hello world"),
                },
                AssistantMessageEvent::Done {
                    reason: StopReason::Stop,
                    message: final_message.clone(),
                },
            ];

            Ok(AssistantStreamResponse::from_events(
                events,
                Ok(final_message),
            ))
        })
    })
}

#[tokio::test]
async fn emits_ordered_streaming_events_and_stream_text_deltas() {
    let agent = Agent::new(AgentOptions {
        model: Some(test_model()),
        stream_fn: Some(synthetic_stream()),
        ..AgentOptions::default()
    });

    let events = agent
        .stream("hello")
        .expect("stream should start")
        .collect::<Vec<_>>()
        .await;

    assert_eq!(events[0].kind(), "agent_start");
    assert_eq!(events[1].kind(), "turn_start");
    assert_eq!(events[2].kind(), "message_start");
    assert_eq!(events[3].kind(), "message_end");
    assert_eq!(events[4].kind(), "message_start");
    assert!(events.iter().any(|event| matches!(
        event,
        tinyagent_rs::AgentEvent::MessageUpdate {
            assistant_message_event: Some(AssistantMessageEvent::ThinkingDelta { .. }),
            ..
        }
    )));
    assert_eq!(events.last().expect("final event").kind(), "agent_end");

    let text_agent = Agent::new(AgentOptions {
        model: Some(test_model()),
        stream_fn: Some(synthetic_stream()),
        ..AgentOptions::default()
    });
    let deltas = text_agent
        .stream_text("hello")
        .expect("text stream should start")
        .collect::<Vec<_>>()
        .await;
    assert_eq!(deltas, vec!["Hello".to_string(), " world".to_string()]);
}
