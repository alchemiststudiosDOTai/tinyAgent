use std::pin::Pin;
use std::task::{Context, Poll};

use futures::channel::mpsc;
use futures::Stream;
use tokio::sync::oneshot;

use crate::error::{Error, Result};

use super::event::AssistantMessageEvent;
use super::message::AssistantMessage;

/// A stream of assistant message events.
///
/// This wraps an async channel and provides:
/// - Async iteration over events via `Stream` trait
/// - A `result()` method to await the final `AssistantMessage`
///
/// The stream is created by provider implementations and events are pushed
/// via the sender handle returned from `AssistantMessageEventStream::new()`.
pub struct AssistantMessageEventStream {
    receiver: mpsc::UnboundedReceiver<AssistantMessageEvent>,
    result_receiver: Option<oneshot::Receiver<AssistantMessage>>,
}

/// Handle for pushing events into an `AssistantMessageEventStream`.
pub struct EventStreamSender {
    sender: mpsc::UnboundedSender<AssistantMessageEvent>,
    result_sender: Option<oneshot::Sender<AssistantMessage>>,
}

impl AssistantMessageEventStream {
    /// Create a new event stream and sender pair.
    ///
    /// The sender is used by provider implementations to push events.
    /// The stream is returned to the caller for iteration.
    pub fn new() -> (Self, EventStreamSender) {
        let (tx, rx) = mpsc::unbounded();
        let (result_tx, result_rx) = oneshot::channel();

        let stream = Self {
            receiver: rx,
            result_receiver: Some(result_rx),
        };

        let sender = EventStreamSender {
            sender: tx,
            result_sender: Some(result_tx),
        };

        (stream, sender)
    }

    /// Await the final result of the stream.
    ///
    /// This consumes the result receiver, so it can only be called once.
    /// Returns the final `AssistantMessage` when the stream completes.
    pub async fn result(mut self) -> Result<AssistantMessage> {
        let receiver = self
            .result_receiver
            .take()
            .ok_or_else(|| Error::InvalidResponse("result() already called".to_string()))?;

        receiver
            .await
            .map_err(|_| Error::InvalidResponse("Stream ended without result".to_string()))
    }
}

impl Default for AssistantMessageEventStream {
    fn default() -> Self {
        let (stream, _sender) = Self::new();
        stream
    }
}

impl Stream for AssistantMessageEventStream {
    type Item = AssistantMessageEvent;

    fn poll_next(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        Pin::new(&mut self.receiver).poll_next(cx)
    }
}

impl EventStreamSender {
    /// Push an event to the stream.
    ///
    /// If the event is a terminal event (Done or Error), this also
    /// resolves the result future with the final message.
    pub fn push(&mut self, event: AssistantMessageEvent) {
        // Check if this is a terminal event
        let is_terminal = matches!(
            &event,
            AssistantMessageEvent::Done { .. } | AssistantMessageEvent::Error { .. }
        );

        // Extract the final message if terminal
        if is_terminal {
            let message = match &event {
                AssistantMessageEvent::Done { message, .. } => message.clone(),
                AssistantMessageEvent::Error { error, .. } => error.clone(),
                _ => unreachable!(),
            };

            // Send the result (ignore error if receiver dropped)
            if let Some(sender) = self.result_sender.take() {
                let _ = sender.send(message);
            }
        }

        // Send the event (ignore error if receiver dropped)
        let _ = self.sender.unbounded_send(event);
    }

    /// End the stream without sending a terminal event.
    ///
    /// This closes the channel. Any pending `result()` calls will fail.
    pub fn end(self) {
        // Dropping self closes the channels
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{Api, Provider, StopReason, StopReasonSuccess, Usage};
    use futures::StreamExt;

    fn make_test_message() -> AssistantMessage {
        AssistantMessage {
            content: vec![],
            api: Api::OpenAICompletions,
            provider: Provider::Known(crate::types::KnownProvider::OpenAI),
            model: "gpt-4".to_string(),
            usage: Usage::default(),
            stop_reason: StopReason::Stop,
            error_message: None,
            timestamp: 0,
        }
    }

    #[tokio::test]
    async fn test_stream_events() {
        let (mut stream, mut sender) = AssistantMessageEventStream::new();

        let msg = make_test_message();

        // Push events
        sender.push(AssistantMessageEvent::Start {
            partial: msg.clone(),
        });
        sender.push(AssistantMessageEvent::TextDelta {
            content_index: 0,
            delta: "Hello".to_string(),
            partial: msg.clone(),
        });
        sender.push(AssistantMessageEvent::Done {
            reason: StopReasonSuccess::Stop,
            message: msg.clone(),
        });

        // Collect events
        let events: Vec<_> = stream.by_ref().take(3).collect().await;
        assert_eq!(events.len(), 3);
        assert!(matches!(events[0], AssistantMessageEvent::Start { .. }));
        assert!(matches!(events[1], AssistantMessageEvent::TextDelta { .. }));
        assert!(matches!(events[2], AssistantMessageEvent::Done { .. }));
    }

    #[tokio::test]
    async fn test_result() {
        let (stream, mut sender) = AssistantMessageEventStream::new();

        let msg = make_test_message();

        sender.push(AssistantMessageEvent::Done {
            reason: StopReasonSuccess::Stop,
            message: msg.clone(),
        });

        let result = stream.result().await.expect("stream result should succeed");
        assert_eq!(result.model, "gpt-4");
    }
}
