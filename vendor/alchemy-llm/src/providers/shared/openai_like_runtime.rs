use std::collections::HashMap;

use futures::StreamExt;
use serde::de::DeserializeOwned;

use crate::types::{
    Api, AssistantMessage, AssistantMessageEvent, EventStreamSender, Provider, StopReason,
    StopReasonError, StopReasonSuccess, Usage,
};

use super::http::build_http_client;
use super::stream_blocks::{finish_current_block, CurrentBlock};
use super::timestamp::unix_timestamp_millis;

pub(crate) struct OpenAiLikeRequest<'a> {
    pub provider: &'a Provider,
    pub base_url: &'a str,
    pub api_key: &'a Option<String>,
    pub model_headers: Option<&'a HashMap<String, String>>,
    pub request_headers: Option<&'a HashMap<String, String>>,
    pub params: &'a serde_json::Value,
}

impl<'a> OpenAiLikeRequest<'a> {
    pub(crate) fn new(
        provider: &'a Provider,
        base_url: &'a str,
        api_key: &'a Option<String>,
        model_headers: Option<&'a HashMap<String, String>>,
        request_headers: Option<&'a HashMap<String, String>>,
        params: &'a serde_json::Value,
    ) -> Self {
        Self {
            provider,
            base_url,
            api_key,
            model_headers,
            request_headers,
            params,
        }
    }
}

pub(crate) fn require_api_key<'a>(
    api_key: &'a Option<String>,
    provider: &Provider,
) -> Result<&'a str, crate::Error> {
    api_key
        .as_deref()
        .ok_or_else(|| crate::Error::NoApiKey(provider.to_string()))
}

pub(crate) fn initialize_output(api: Api, provider: Provider, model: String) -> AssistantMessage {
    AssistantMessage {
        content: vec![],
        api,
        provider,
        model,
        usage: Usage::default(),
        stop_reason: StopReason::Stop,
        error_message: None,
        timestamp: unix_timestamp_millis(),
    }
}

pub(crate) fn push_stream_error(
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    error: crate::Error,
) {
    output.stop_reason = StopReason::Error;
    output.error_message = Some(error.to_string());

    sender.push(AssistantMessageEvent::Error {
        reason: StopReasonError::Error,
        error: output.clone(),
    });
}

pub(crate) fn push_stream_done(output: &AssistantMessage, sender: &mut EventStreamSender) {
    sender.push(AssistantMessageEvent::Done {
        reason: done_reason_from_stop_reason(output.stop_reason),
        message: output.clone(),
    });
}

pub(crate) async fn run_openai_like_stream<TChunk, TState, FChunk, FBeforeFinish>(
    request: OpenAiLikeRequest<'_>,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    state: &mut TState,
    mut process_chunk: FChunk,
    mut before_finish: FBeforeFinish,
) -> Result<(), crate::Error>
where
    TChunk: DeserializeOwned,
    FChunk: FnMut(
        TChunk,
        &mut TState,
        &mut AssistantMessage,
        &mut EventStreamSender,
        &mut Option<CurrentBlock>,
    ),
    FBeforeFinish: FnMut(
        &mut TState,
        &mut AssistantMessage,
        &mut EventStreamSender,
        &mut Option<CurrentBlock>,
    ),
{
    let api_key = require_api_key(request.api_key, request.provider)?;
    let client = build_http_client(api_key, request.model_headers, request.request_headers)?;
    let response = send_streaming_request(&client, request.base_url, request.params).await?;

    sender.push(AssistantMessageEvent::Start {
        partial: output.clone(),
    });

    let mut current_block: Option<CurrentBlock> = None;

    process_sse_stream::<TChunk, _>(response, |chunk| {
        process_chunk(chunk, state, output, sender, &mut current_block);
    })
    .await?;

    before_finish(state, output, sender, &mut current_block);
    finish_current_block(&mut current_block, output, sender);
    push_stream_done(output, sender);

    Ok(())
}

pub(crate) async fn run_openai_like_stream_without_state<TChunk, FChunk>(
    request: OpenAiLikeRequest<'_>,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    mut process_chunk: FChunk,
) -> Result<(), crate::Error>
where
    TChunk: DeserializeOwned,
    FChunk: FnMut(TChunk, &mut AssistantMessage, &mut EventStreamSender, &mut Option<CurrentBlock>),
{
    let mut state = ();

    run_openai_like_stream::<TChunk, _, _, _>(
        request,
        output,
        sender,
        &mut state,
        |chunk, _state, output, sender, current_block| {
            process_chunk(chunk, output, sender, current_block);
        },
        |_state, _output, _sender, _current_block| {},
    )
    .await
}

fn done_reason_from_stop_reason(stop_reason: StopReason) -> StopReasonSuccess {
    match stop_reason {
        StopReason::Stop => StopReasonSuccess::Stop,
        StopReason::Length => StopReasonSuccess::Length,
        StopReason::ToolUse => StopReasonSuccess::ToolUse,
        _ => StopReasonSuccess::Stop,
    }
}

pub(crate) async fn send_streaming_request(
    client: &reqwest::Client,
    base_url: &str,
    params: &serde_json::Value,
) -> Result<reqwest::Response, crate::Error> {
    let response = client.post(base_url).json(params).send().await?;

    if response.status().is_success() {
        return Ok(response);
    }

    let status_code = response.status().as_u16();
    let body = response.text().await.unwrap_or_default();

    Err(crate::Error::ApiError {
        status_code,
        message: body,
    })
}

pub(crate) async fn process_sse_stream<TChunk, F>(
    response: reqwest::Response,
    mut on_chunk: F,
) -> Result<(), crate::Error>
where
    TChunk: DeserializeOwned,
    F: FnMut(TChunk),
{
    let mut stream = response.bytes_stream();
    let mut buffer = String::new();
    let mut done_received = false;

    while let Some(chunk_result) = stream.next().await {
        let chunk = chunk_result?;
        buffer.push_str(&String::from_utf8_lossy(&chunk));

        while let Some(line_end) = buffer.find('\n') {
            let line = buffer[..line_end].trim().to_string();
            buffer = buffer[line_end + 1..].to_string();

            if line.is_empty() || line.starts_with(':') {
                continue;
            }

            if let Some(data) = sse_field_value(&line, "data") {
                if data == "[DONE]" {
                    done_received = true;
                    break;
                }

                if let Ok(chunk) = serde_json::from_str::<TChunk>(data) {
                    on_chunk(chunk);
                }
            }
        }

        if done_received {
            break;
        }
    }

    Ok(())
}

pub(crate) async fn process_sse_stream_with_event<TChunk, F>(
    response: reqwest::Response,
    mut on_chunk: F,
) -> Result<(), crate::Error>
where
    TChunk: DeserializeOwned,
    F: FnMut(String, TChunk),
{
    let mut stream = response.bytes_stream();
    let mut buffer = String::new();
    let mut current_event_type = String::new();

    while let Some(chunk_result) = stream.next().await {
        let chunk = chunk_result?;
        buffer.push_str(&String::from_utf8_lossy(&chunk));

        while let Some(line_end) = buffer.find('\n') {
            let line = buffer[..line_end].trim().to_string();
            buffer = buffer[line_end + 1..].to_string();

            if line.is_empty() || line.starts_with(':') {
                continue;
            }

            if let Some(event_type) = sse_field_value(&line, "event") {
                current_event_type = event_type.to_string();
                continue;
            }

            if let Some(data) = sse_field_value(&line, "data") {
                let data = data.trim();
                if data == "[DONE]" {
                    break;
                }
                if let Ok(parsed) = serde_json::from_str::<TChunk>(data) {
                    on_chunk(current_event_type.clone(), parsed);
                }
                current_event_type.clear();
            }
        }
    }

    Ok(())
}

fn sse_field_value<'a>(line: &'a str, field: &str) -> Option<&'a str> {
    let prefix = format!("{field}:");
    line.strip_prefix(&prefix)
        .map(|value| value.strip_prefix(' ').unwrap_or(value))
}

#[cfg(test)]
mod tests {
    use super::{done_reason_from_stop_reason, require_api_key, sse_field_value};
    use crate::types::{KnownProvider, Provider, StopReason, StopReasonSuccess};

    #[test]
    fn stop_reason_maps_to_done_reason() {
        assert_eq!(
            done_reason_from_stop_reason(StopReason::Stop),
            StopReasonSuccess::Stop
        );
        assert_eq!(
            done_reason_from_stop_reason(StopReason::Length),
            StopReasonSuccess::Length
        );
        assert_eq!(
            done_reason_from_stop_reason(StopReason::ToolUse),
            StopReasonSuccess::ToolUse
        );
        assert_eq!(
            done_reason_from_stop_reason(StopReason::Error),
            StopReasonSuccess::Stop
        );
    }

    #[test]
    fn require_api_key_returns_key_when_present() {
        let provider = Provider::Known(KnownProvider::OpenAI);
        let key = Some("test-key".to_string());

        let resolved = require_api_key(&key, &provider).expect("api key should be present");
        assert_eq!(resolved, "test-key");
    }

    #[test]
    fn require_api_key_errors_when_missing() {
        let provider = Provider::Known(KnownProvider::OpenAI);
        let key = None;

        let error = require_api_key(&key, &provider).expect_err("api key should be required");
        assert_eq!(
            error.to_string(),
            "No API key provided for provider: openai"
        );
    }

    #[test]
    fn sse_field_value_accepts_lines_with_or_without_space() {
        assert_eq!(
            sse_field_value("event: message_start", "event"),
            Some("message_start")
        );
        assert_eq!(
            sse_field_value("event:message_start", "event"),
            Some("message_start")
        );
        assert_eq!(
            sse_field_value("data: {\"ok\":true}", "data"),
            Some("{\"ok\":true}")
        );
        assert_eq!(
            sse_field_value("data:{\"ok\":true}", "data"),
            Some("{\"ok\":true}")
        );
    }
}
