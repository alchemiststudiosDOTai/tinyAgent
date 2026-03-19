use crate::agent_options::{AgentLoopConfig, StreamRequest};
use crate::agent_types::{
    AgentContext, AgentEvent, AgentMessage, AssistantMessage, AssistantMessageEvent,
};
use crate::alchemy_stream::default_stream_fn;
use crate::error::{AgentError, Result};
use futures::{Stream, StreamExt};
use std::pin::Pin;
use std::task::{Context, Poll};
use tokio::sync::{mpsc, oneshot};
use tokio_stream::wrappers::UnboundedReceiverStream;
use tokio_util::sync::CancellationToken;

pub(crate) type AgentEventTx = mpsc::UnboundedSender<AgentEvent>;
pub(crate) type AgentResultTx = oneshot::Sender<Result<Vec<AgentMessage>>>;
pub(crate) type AssistantEventTx = mpsc::UnboundedSender<AssistantMessageEvent>;
pub(crate) type AssistantResultTx = oneshot::Sender<Result<AssistantMessage>>;
pub(crate) type TextTx = mpsc::UnboundedSender<String>;

pub struct AgentEventStream {
    receiver: UnboundedReceiverStream<AgentEvent>,
    result_rx: Option<oneshot::Receiver<Result<Vec<AgentMessage>>>>,
}

impl AgentEventStream {
    pub(crate) fn new(
        receiver: mpsc::UnboundedReceiver<AgentEvent>,
        result_rx: oneshot::Receiver<Result<Vec<AgentMessage>>>,
    ) -> Self {
        Self {
            receiver: UnboundedReceiverStream::new(receiver),
            result_rx: Some(result_rx),
        }
    }

    pub async fn result(mut self) -> Result<Vec<AgentMessage>> {
        let receiver = self
            .result_rx
            .take()
            .ok_or_else(|| AgentError::Internal("agent result already consumed".to_string()))?;

        receiver
            .await
            .map_err(|_| AgentError::Internal("agent stream ended without result".to_string()))?
    }
}

impl Stream for AgentEventStream {
    type Item = AgentEvent;

    fn poll_next(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        Pin::new(&mut self.receiver).poll_next(cx)
    }
}

pub struct AgentTextStream {
    receiver: UnboundedReceiverStream<String>,
}

impl AgentTextStream {
    pub(crate) fn new(receiver: mpsc::UnboundedReceiver<String>) -> Self {
        Self {
            receiver: UnboundedReceiverStream::new(receiver),
        }
    }
}

impl Stream for AgentTextStream {
    type Item = String;

    fn poll_next(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        Pin::new(&mut self.receiver).poll_next(cx)
    }
}

pub struct AssistantStreamResponse {
    receiver: UnboundedReceiverStream<AssistantMessageEvent>,
    result_rx: Option<oneshot::Receiver<Result<AssistantMessage>>>,
}

impl AssistantStreamResponse {
    pub fn channel() -> (
        Self,
        mpsc::UnboundedSender<AssistantMessageEvent>,
        oneshot::Sender<Result<AssistantMessage>>,
    ) {
        assistant_stream_channel()
    }

    pub(crate) fn new(
        receiver: mpsc::UnboundedReceiver<AssistantMessageEvent>,
        result_rx: oneshot::Receiver<Result<AssistantMessage>>,
    ) -> Self {
        Self {
            receiver: UnboundedReceiverStream::new(receiver),
            result_rx: Some(result_rx),
        }
    }

    pub async fn result(mut self) -> Result<AssistantMessage> {
        let receiver = self
            .result_rx
            .take()
            .ok_or_else(|| AgentError::Internal("assistant result already consumed".to_string()))?;

        receiver.await.map_err(|_| {
            AgentError::Internal("assistant stream ended without result".to_string())
        })?
    }

    pub fn from_events(
        events: Vec<AssistantMessageEvent>,
        result: Result<AssistantMessage>,
    ) -> Self {
        let (stream, event_tx, result_tx) = assistant_stream_channel();

        for event in events {
            let _ = event_tx.send(event);
        }
        let _ = result_tx.send(result);

        stream
    }
}

impl Stream for AssistantStreamResponse {
    type Item = AssistantMessageEvent;

    fn poll_next(mut self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Option<Self::Item>> {
        Pin::new(&mut self.receiver).poll_next(cx)
    }
}

pub(crate) fn agent_event_channel() -> (AgentEventStream, AgentEventTx, AgentResultTx) {
    let (event_tx, event_rx) = mpsc::unbounded_channel();
    let (result_tx, result_rx) = oneshot::channel();

    (
        AgentEventStream::new(event_rx, result_rx),
        event_tx,
        result_tx,
    )
}

pub(crate) fn assistant_stream_channel(
) -> (AssistantStreamResponse, AssistantEventTx, AssistantResultTx) {
    let (event_tx, event_rx) = mpsc::unbounded_channel();
    let (result_tx, result_rx) = oneshot::channel();

    (
        AssistantStreamResponse::new(event_rx, result_rx),
        event_tx,
        result_tx,
    )
}

pub(crate) fn text_channel() -> (AgentTextStream, TextTx) {
    let (tx, rx) = mpsc::unbounded_channel();
    (AgentTextStream::new(rx), tx)
}

pub async fn stream_assistant_response(
    context: &mut AgentContext,
    config: &AgentLoopConfig,
    abort: CancellationToken,
    event_tx: &AgentEventTx,
) -> Result<AssistantMessage> {
    if abort.is_cancelled() {
        return Err(AgentError::Aborted);
    }

    let request = StreamRequest {
        model: config.model.clone(),
        context: context.to_llm_context(),
        options: config.stream_options.clone(),
    };

    let stream_fn = config.stream_fn.clone().unwrap_or_else(default_stream_fn);
    let mut response = stream_fn(request).await?;
    let mut added_partial = false;

    while let Some(event) = response.next().await {
        if abort.is_cancelled() {
            return Err(AgentError::Aborted);
        }

        let Some(partial) = event.partial().cloned() else {
            continue;
        };

        match event {
            AssistantMessageEvent::Start { .. } => {
                context
                    .messages
                    .push(AgentMessage::Assistant(partial.clone()));
                let _ = event_tx.send(AgentEvent::MessageStart {
                    message: Some(AgentMessage::Assistant(partial)),
                });
                added_partial = true;
            }
            AssistantMessageEvent::TextStart { .. }
            | AssistantMessageEvent::TextDelta { .. }
            | AssistantMessageEvent::TextEnd { .. }
            | AssistantMessageEvent::ThinkingStart { .. }
            | AssistantMessageEvent::ThinkingDelta { .. }
            | AssistantMessageEvent::ThinkingEnd { .. }
            | AssistantMessageEvent::ToolCallStart { .. }
            | AssistantMessageEvent::ToolCallDelta { .. }
            | AssistantMessageEvent::ToolCallEnd { .. } => {
                if !added_partial {
                    context
                        .messages
                        .push(AgentMessage::Assistant(partial.clone()));
                    let _ = event_tx.send(AgentEvent::MessageStart {
                        message: Some(AgentMessage::Assistant(partial.clone())),
                    });
                    added_partial = true;
                } else if let Some(last) = context.messages.last_mut() {
                    *last = AgentMessage::Assistant(partial.clone());
                }

                let _ = event_tx.send(AgentEvent::MessageUpdate {
                    message: Some(AgentMessage::Assistant(partial)),
                    assistant_message_event: Some(event),
                });
            }
            AssistantMessageEvent::Done { .. } | AssistantMessageEvent::Error { .. } => {}
        }
    }

    let final_message = response.result().await?;
    if added_partial {
        if let Some(last) = context.messages.last_mut() {
            *last = AgentMessage::Assistant(final_message.clone());
        }
    } else {
        context
            .messages
            .push(AgentMessage::Assistant(final_message.clone()));
        let _ = event_tx.send(AgentEvent::MessageStart {
            message: Some(AgentMessage::Assistant(final_message.clone())),
        });
    }

    let _ = event_tx.send(AgentEvent::MessageEnd {
        message: Some(AgentMessage::Assistant(final_message.clone())),
    });

    Ok(final_message)
}
