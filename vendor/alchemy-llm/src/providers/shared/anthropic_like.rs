use serde::Deserialize;
use serde_json::json;

use super::{
    finish_current_block, handle_reasoning_delta, handle_text_delta, initialize_output,
    merge_headers, process_sse_stream_with_event, push_stream_done, push_stream_error,
    CurrentBlock, ReasoningDelta,
};
use crate::types::{
    AnthropicMessages, Api, AssistantMessage, AssistantMessageEvent, AssistantMessageEventStream,
    Content, Context, Cost, EventStreamSender, InputType, Message, Model, StopReason,
    ToolResultContent, Usage, UserContent, UserContentBlock,
};

const THINKING_SIGNATURE: &str = "thinking";

#[derive(Clone, Copy)]
pub(crate) enum AnthropicLikeAuth {
    XApiKey,
    Bearer,
}

#[derive(Clone, Copy)]
pub(crate) struct AnthropicLikeProviderConfig {
    pub auth: AnthropicLikeAuth,
    pub messages_endpoint: &'static str,
    pub version_header: Option<(&'static str, &'static str)>,
    pub beta_header: Option<(&'static str, &'static str)>,
}

pub(crate) fn stream_anthropic_like_messages(
    config: AnthropicLikeProviderConfig,
    model: &Model<AnthropicMessages>,
    context: &Context,
    options: crate::providers::OpenAICompletionsOptions,
) -> AssistantMessageEventStream {
    let (stream, sender) = AssistantMessageEventStream::new();
    let model = model.clone();
    let context = context.clone();
    tokio::spawn(async move { run_stream(config, model, context, options, sender).await });
    stream
}

async fn run_stream(
    config: AnthropicLikeProviderConfig,
    model: Model<AnthropicMessages>,
    context: Context,
    options: crate::providers::OpenAICompletionsOptions,
    mut sender: EventStreamSender,
) {
    let mut output = initialize_output(
        Api::AnthropicMessages,
        model.provider.clone(),
        model.id.clone(),
    );
    if let Err(e) =
        run_stream_inner(config, &model, &context, &options, &mut output, &mut sender).await
    {
        push_stream_error(&mut output, &mut sender, e);
    }
}

async fn run_stream_inner(
    config: AnthropicLikeProviderConfig,
    model: &Model<AnthropicMessages>,
    context: &Context,
    options: &crate::providers::OpenAICompletionsOptions,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
) -> Result<(), crate::Error> {
    let api_key = options
        .api_key
        .as_ref()
        .ok_or_else(|| crate::Error::NoApiKey(model.provider.to_string()))?;

    let client = build_client(config, api_key, model, options)?;
    let url = format!("{}{}", model.base_url, config.messages_endpoint);
    let response = client
        .post(&url)
        .json(&build_params(model, context, options))
        .send()
        .await?;

    if !response.status().is_success() {
        let status_code = response.status().as_u16();
        let body = response.text().await.unwrap_or_default();
        return Err(crate::Error::ApiError {
            status_code,
            message: body,
        });
    }

    sender.push(AssistantMessageEvent::Start {
        partial: output.clone(),
    });

    let mut current_block: Option<CurrentBlock> = None;

    process_sse_stream_with_event::<SseEvent, _>(response, |event_type, event| {
        process_event(&event_type, &event, output, sender, &mut current_block);
    })
    .await?;

    finish_current_block(&mut current_block, output, sender);
    push_stream_done(output, sender);
    Ok(())
}

fn build_client(
    config: AnthropicLikeProviderConfig,
    api_key: &str,
    model: &Model<AnthropicMessages>,
    options: &crate::providers::OpenAICompletionsOptions,
) -> Result<reqwest::Client, crate::Error> {
    let headers = build_headers(config, api_key, model, options)?;

    reqwest::Client::builder()
        .default_headers(headers)
        .build()
        .map_err(crate::Error::from)
}

fn build_headers(
    config: AnthropicLikeProviderConfig,
    api_key: &str,
    model: &Model<AnthropicMessages>,
    options: &crate::providers::OpenAICompletionsOptions,
) -> Result<reqwest::header::HeaderMap, crate::Error> {
    use reqwest::header::{HeaderMap, HeaderName, HeaderValue, AUTHORIZATION, CONTENT_TYPE};

    let mut headers = HeaderMap::new();
    headers.insert(CONTENT_TYPE, HeaderValue::from_static("application/json"));

    match config.auth {
        AnthropicLikeAuth::XApiKey => {
            headers.insert(
                HeaderName::from_static("x-api-key"),
                HeaderValue::from_str(api_key)
                    .map_err(|e| crate::Error::InvalidHeader(e.to_string()))?,
            );
        }
        AnthropicLikeAuth::Bearer => {
            headers.insert(
                AUTHORIZATION,
                HeaderValue::from_str(&format!("Bearer {api_key}"))
                    .map_err(|e| crate::Error::InvalidHeader(e.to_string()))?,
            );
        }
    }

    if let Some((name, value)) = config.version_header {
        headers.insert(
            HeaderName::from_static(name),
            HeaderValue::from_static(value),
        );
    }
    if let Some((name, value)) = config.beta_header {
        headers.insert(
            HeaderName::from_static(name),
            HeaderValue::from_static(value),
        );
    }

    merge_headers(&mut headers, model.headers.as_ref());
    merge_headers(&mut headers, options.headers.as_ref());
    Ok(headers)
}

pub(crate) fn build_params(
    model: &Model<AnthropicMessages>,
    context: &Context,
    options: &crate::providers::OpenAICompletionsOptions,
) -> serde_json::Value {
    let max_tokens = options.max_tokens.unwrap_or(model.max_tokens);
    let mut params = json!({
        "model": model.id,
        "stream": true,
        "max_tokens": max_tokens,
        "messages": convert_messages(model, context),
    });

    if let Some(sys) = &context.system_prompt {
        params["system"] = json!(sys);
    }
    if let Some(t) = options.temperature {
        params["temperature"] = json!(t);
    }
    if let Some(tools) = &context.tools {
        let defs: Vec<_> = tools
            .iter()
            .map(|t| {
                json!({
                    "name": t.name, "description": t.description, "input_schema": t.parameters,
                })
            })
            .collect();
        params["tools"] = json!(defs);
    }
    if model.reasoning {
        let budget = max_tokens.saturating_sub(100);
        if budget >= 1024 {
            params["thinking"] = json!({
                "type": "enabled",
                "budget_tokens": budget
            });
        }
    }

    params
}

fn convert_messages(model: &Model<AnthropicMessages>, context: &Context) -> Vec<serde_json::Value> {
    context
        .messages
        .iter()
        .filter_map(|m| match m {
            Message::User(u) => {
                Some(json!({"role": "user", "content": convert_user_content(model, &u.content)}))
            }
            Message::Assistant(a) => {
                let content = convert_assistant_content(a);
                (!content.is_empty()).then(|| json!({"role": "assistant", "content": content}))
            }
            Message::ToolResult(r) => {
                let blocks: Vec<serde_json::Value> = r
                    .content
                    .iter()
                    .map(|c| match c {
                        ToolResultContent::Text(t) => json!({"type": "text", "text": t.text}),
                        ToolResultContent::Image(img) => json!({
                            "type": "image", "source": {"type": "base64", "media_type": img.mime_type, "data": img.to_base64()}
                        }),
                    })
                    .collect();
                let content =
                    if blocks.len() == 1 && matches!(&r.content[0], ToolResultContent::Text(_)) {
                        json!(r.content.iter().filter_map(|c| match c {
                            ToolResultContent::Text(t) => Some(t.text.clone()),
                            _ => None,
                        }).collect::<Vec<_>>().join("\n"))
                    } else {
                        json!(blocks)
                    };
                Some(json!({"role": "user", "content": [{"type": "tool_result", "tool_use_id": r.tool_call_id.as_str(), "content": content, "is_error": r.is_error}]}))
            }
        })
        .collect()
}

fn convert_user_content(
    model: &Model<AnthropicMessages>,
    content: &UserContent,
) -> serde_json::Value {
    match content {
        UserContent::Text(text) => json!(text),
        UserContent::Multi(blocks) => json!(blocks.iter().filter_map(|b| match b {
            UserContentBlock::Text(t) => Some(json!({"type": "text", "text": t.text})),
            UserContentBlock::Image(img) if model.input.contains(&InputType::Image) => Some(json!({
                "type": "image", "source": {"type": "base64", "media_type": img.mime_type, "data": img.to_base64()}
            })),
            UserContentBlock::Image(_) => None,
        }).collect::<Vec<_>>()),
    }
}

fn convert_assistant_content(assistant: &AssistantMessage) -> Vec<serde_json::Value> {
    assistant
        .content
        .iter()
        .filter_map(|c| match c {
            Content::Text { inner } if !inner.text.is_empty() => {
                Some(json!({"type": "text", "text": inner.text}))
            }
            Content::Thinking { inner } if !inner.thinking.is_empty() => {
                let mut block = json!({"type": "thinking", "thinking": inner.thinking});
                if let Some(sig) = &inner.thinking_signature {
                    block["signature"] = json!(sig);
                }
                Some(block)
            }
            Content::ToolCall { inner } => Some(
                json!({"type": "tool_use", "id": inner.id.as_str(), "name": inner.name, "input": inner.arguments}),
            ),
            _ => None,
        })
        .collect()
}

fn process_event(
    event_type: &str,
    event: &SseEvent,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
) {
    match event_type {
        "content_block_start" => handle_block_start(event, output, sender, current_block),
        "content_block_delta" => handle_block_delta(event, output, sender, current_block),
        "content_block_stop" => finish_current_block(current_block, output, sender),
        "message_start" => handle_message_start(event, output),
        "message_delta" => handle_message_delta(event, output),
        _ => {}
    }
}

fn handle_block_start(
    event: &SseEvent,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
) {
    finish_current_block(current_block, output, sender);
    let Some(block) = &event.content_block else {
        return;
    };
    if block.block_type != "tool_use" {
        return;
    }
    let id = block.id.clone().unwrap_or_default();
    let name = block.name.clone().unwrap_or_default();
    *current_block = Some(CurrentBlock::ToolCall {
        id: id.clone(),
        name: name.clone(),
        partial_args: String::new(),
    });
    output.content.push(Content::tool_call(
        id,
        name,
        serde_json::Value::Object(serde_json::Map::new()),
    ));
    sender.push(AssistantMessageEvent::ToolCallStart {
        content_index: output.content.len() - 1,
        partial: output.clone(),
    });
}

fn handle_block_delta(
    event: &SseEvent,
    output: &mut AssistantMessage,
    sender: &mut EventStreamSender,
    current_block: &mut Option<CurrentBlock>,
) {
    let Some(delta) = &event.delta else { return };
    match delta.delta_type.as_deref() {
        Some("text_delta") => {
            if let Some(text) = &delta.text {
                handle_text_delta(text, output, sender, current_block);
            }
        }
        Some("thinking_delta") => {
            if let Some(thinking) = &delta.thinking {
                handle_reasoning_delta(
                    ReasoningDelta {
                        text: thinking,
                        signature: THINKING_SIGNATURE,
                    },
                    output,
                    sender,
                    current_block,
                );
            }
        }
        Some("signature_delta") => {
            if let Some(sig) = &delta.signature {
                if let Some(CurrentBlock::Thinking { signature, .. }) = current_block {
                    *signature = sig.clone();
                }
            }
        }
        Some("input_json_delta") => {
            if let Some(partial) = &delta.partial_json {
                if let Some(CurrentBlock::ToolCall { partial_args, .. }) = current_block {
                    partial_args.push_str(partial);
                    sender.push(AssistantMessageEvent::ToolCallDelta {
                        content_index: output.content.len().saturating_sub(1),
                        delta: partial.clone(),
                        partial: output.clone(),
                    });
                }
            }
        }
        _ => {}
    }
}

fn handle_message_start(event: &SseEvent, output: &mut AssistantMessage) {
    let Some(msg) = &event.message else { return };
    let Some(u) = &msg.usage else { return };
    output.usage = Usage {
        input: u.input_tokens.unwrap_or(0),
        output: 0,
        cache_read: u.cache_read_input_tokens.unwrap_or(0),
        cache_write: u.cache_creation_input_tokens.unwrap_or(0),
        total_tokens: u.input_tokens.unwrap_or(0),
        cost: Cost::default(),
    };
}

fn handle_message_delta(event: &SseEvent, output: &mut AssistantMessage) {
    if let Some(delta) = &event.delta {
        if let Some(reason) = &delta.stop_reason {
            output.stop_reason = map_stop_reason(reason);
        }
    }
    if let Some(u) = &event.usage {
        output.usage.output = u.output_tokens.unwrap_or(0);
        output.usage.total_tokens = output.usage.input + output.usage.output;
    }
}

fn map_stop_reason(reason: &str) -> StopReason {
    match reason {
        "end_turn" | "stop_sequence" => StopReason::Stop,
        "max_tokens" => StopReason::Length,
        "tool_use" => StopReason::ToolUse,
        _ => StopReason::Stop,
    }
}

#[derive(Debug, Deserialize)]
struct SseEvent {
    delta: Option<SseDelta>,
    content_block: Option<ContentBlock>,
    message: Option<MessageStart>,
    usage: Option<AnthropicUsage>,
}

#[derive(Debug, Deserialize)]
struct SseDelta {
    #[serde(rename = "type")]
    delta_type: Option<String>,
    text: Option<String>,
    thinking: Option<String>,
    signature: Option<String>,
    partial_json: Option<String>,
    stop_reason: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ContentBlock {
    #[serde(rename = "type")]
    block_type: String,
    id: Option<String>,
    name: Option<String>,
}

#[derive(Debug, Deserialize)]
struct MessageStart {
    usage: Option<AnthropicUsage>,
}

#[derive(Debug, Deserialize)]
struct AnthropicUsage {
    input_tokens: Option<u32>,
    output_tokens: Option<u32>,
    cache_read_input_tokens: Option<u32>,
    cache_creation_input_tokens: Option<u32>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::providers::OpenAICompletionsOptions;
    use crate::types::{
        AssistantMessageEvent, KnownProvider, ModelCost, Provider, Tool, UserMessage,
    };
    use futures::executor::block_on;
    use futures::StreamExt;
    use reqwest::header::AUTHORIZATION;

    fn make_model(provider: KnownProvider, reasoning: bool) -> Model<AnthropicMessages> {
        Model {
            id: match provider {
                KnownProvider::Kimi => "kimi-coding".to_string(),
                _ => "claude-sonnet-4-6".to_string(),
            },
            name: match provider {
                KnownProvider::Kimi => "Kimi K2.5".to_string(),
                _ => "Claude Sonnet 4.6".to_string(),
            },
            api: AnthropicMessages,
            provider: Provider::Known(provider.clone()),
            base_url: match provider {
                KnownProvider::Kimi => "https://api.kimi.com/coding".to_string(),
                _ => "https://api.anthropic.com".to_string(),
            },
            reasoning,
            input: vec![InputType::Text, InputType::Image],
            cost: ModelCost {
                input: 0.003,
                output: 0.015,
                cache_read: 0.0003,
                cache_write: 0.00375,
            },
            context_window: 200_000,
            max_tokens: 8_192,
            headers: None,
            compat: None,
        }
    }

    fn make_context() -> Context {
        Context {
            system_prompt: Some("You are concise".to_string()),
            messages: vec![Message::User(UserMessage {
                content: UserContent::Text("Hello".to_string()),
                timestamp: 0,
            })],
            tools: None,
        }
    }

    fn make_output(provider: KnownProvider, model: &str) -> AssistantMessage {
        AssistantMessage {
            content: vec![],
            api: Api::AnthropicMessages,
            provider: Provider::Known(provider),
            model: model.to_string(),
            usage: Usage::default(),
            stop_reason: StopReason::Stop,
            error_message: None,
            timestamp: 0,
        }
    }

    fn run_events(
        events: Vec<(&str, SseEvent)>,
        provider: KnownProvider,
        model: &str,
    ) -> (Vec<AssistantMessageEvent>, AssistantMessage) {
        let (mut stream, mut sender) = AssistantMessageEventStream::new();
        let mut output = make_output(provider, model);
        let mut current_block = None;
        for (t, e) in events {
            process_event(t, &e, &mut output, &mut sender, &mut current_block);
        }
        finish_current_block(&mut current_block, &mut output, &mut sender);
        drop(sender);
        let collected = block_on(async move { stream.by_ref().collect::<Vec<_>>().await });
        (collected, output)
    }

    #[test]
    fn build_params_constructs_anthropic_format() {
        let params = build_params(
            &make_model(KnownProvider::Anthropic, false),
            &make_context(),
            &OpenAICompletionsOptions {
                temperature: Some(0.7),
                max_tokens: Some(1024),
                ..Default::default()
            },
        );
        assert_eq!(params["model"], "claude-sonnet-4-6");
        assert_eq!(params["max_tokens"], 1024);
        assert_eq!(params["system"], "You are concise");
        assert_eq!(params["temperature"], 0.7);
        assert!(params.get("thinking").is_none());
    }

    #[test]
    fn build_params_includes_thinking_for_reasoning() {
        let params = build_params(
            &make_model(KnownProvider::Anthropic, true),
            &make_context(),
            &OpenAICompletionsOptions {
                max_tokens: Some(4096),
                ..Default::default()
            },
        );
        assert_eq!(params["thinking"]["type"], "enabled");
        assert_eq!(params["thinking"]["budget_tokens"], 3996);
    }

    #[test]
    fn build_params_uses_input_schema_for_tools() {
        let ctx = Context {
            system_prompt: None,
            tools: Some(vec![Tool::new(
                "get_weather",
                "Get weather",
                json!({"type": "object"}),
            )]),
            messages: vec![Message::User(UserMessage {
                content: UserContent::Text("t".into()),
                timestamp: 0,
            })],
        };
        let params = build_params(
            &make_model(KnownProvider::Anthropic, false),
            &ctx,
            &Default::default(),
        );
        assert_eq!(params["tools"][0]["name"], "get_weather");
        assert_eq!(params["tools"][0]["input_schema"]["type"], "object");
    }

    #[test]
    fn build_client_uses_x_api_key_for_anthropic() {
        let headers = build_headers(
            AnthropicLikeProviderConfig {
                auth: AnthropicLikeAuth::XApiKey,
                messages_endpoint: "/v1/messages",
                version_header: Some(("anthropic-version", "2023-06-01")),
                beta_header: Some(("anthropic-beta", "interleaved-thinking-2025-05-14")),
            },
            "test-key",
            &make_model(KnownProvider::Anthropic, false),
            &OpenAICompletionsOptions::default(),
        )
        .expect("headers should build");
        assert_eq!(
            headers
                .get("x-api-key")
                .expect("x-api-key header should exist"),
            "test-key"
        );
        assert_eq!(
            headers
                .get("anthropic-version")
                .expect("anthropic-version should exist"),
            "2023-06-01"
        );
    }

    #[test]
    fn build_client_uses_bearer_auth_for_kimi() {
        let headers = build_headers(
            AnthropicLikeProviderConfig {
                auth: AnthropicLikeAuth::Bearer,
                messages_endpoint: "/v1/messages",
                version_header: None,
                beta_header: None,
            },
            "test-key",
            &make_model(KnownProvider::Kimi, false),
            &OpenAICompletionsOptions::default(),
        )
        .expect("headers should build");
        assert_eq!(
            headers
                .get(AUTHORIZATION)
                .expect("authorization header should exist"),
            "Bearer test-key"
        );
        assert!(headers.get("anthropic-version").is_none());
        assert!(headers.get("anthropic-beta").is_none());
    }

    #[test]
    fn text_delta_emits_text_events() {
        let e: SseEvent =
            serde_json::from_value(json!({"delta": {"type": "text_delta", "text": "Hello"}}))
                .unwrap();
        let (events, output) = run_events(
            vec![("content_block_delta", e)],
            KnownProvider::Anthropic,
            "claude",
        );
        assert!(matches!(events[0], AssistantMessageEvent::TextStart { .. }));
        assert!(matches!(&output.content[0], Content::Text { inner } if inner.text == "Hello"));
    }

    #[test]
    fn thinking_delta_emits_thinking_events() {
        let e: SseEvent =
            serde_json::from_value(json!({"delta": {"type": "thinking_delta", "thinking": "hmm"}}))
                .unwrap();
        let (events, output) = run_events(
            vec![("content_block_delta", e)],
            KnownProvider::Anthropic,
            "claude",
        );
        assert!(matches!(
            events[0],
            AssistantMessageEvent::ThinkingStart { .. }
        ));
        assert!(
            matches!(&output.content[0], Content::Thinking { inner } if inner.thinking == "hmm")
        );
    }

    #[test]
    fn tool_use_block_emits_tool_call() {
        let start: SseEvent = serde_json::from_value(
            json!({"content_block": {"type": "tool_use", "id": "toolu_1", "name": "calc"}}),
        )
        .unwrap();
        let delta: SseEvent = serde_json::from_value(
            json!({"delta": {"type": "input_json_delta", "partial_json": "{\"x\":1}"}}),
        )
        .unwrap();
        let stop: SseEvent = serde_json::from_value(json!({})).unwrap();
        let (events, output) = run_events(
            vec![
                ("content_block_start", start),
                ("content_block_delta", delta),
                ("content_block_stop", stop),
            ],
            KnownProvider::Kimi,
            "kimi-coding",
        );

        assert!(matches!(
            &events[0],
            AssistantMessageEvent::ToolCallStart { .. }
        ));
        assert!(matches!(
            &output.content[0],
            Content::ToolCall { inner } if inner.name == "calc"
        ));
    }
}
