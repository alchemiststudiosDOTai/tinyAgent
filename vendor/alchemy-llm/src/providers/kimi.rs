use super::openai_completions::OpenAICompletionsOptions;
use super::shared::{
    stream_anthropic_like_messages, AnthropicLikeAuth, AnthropicLikeProviderConfig,
};
use crate::types::{AnthropicMessages, AssistantMessageEventStream, Context, Model};

const KIMI_CONFIG: AnthropicLikeProviderConfig = AnthropicLikeProviderConfig {
    auth: AnthropicLikeAuth::Bearer,
    messages_endpoint: "/v1/messages",
    version_header: None,
    beta_header: None,
};

pub fn stream_kimi_messages(
    model: &Model<AnthropicMessages>,
    context: &Context,
    options: OpenAICompletionsOptions,
) -> AssistantMessageEventStream {
    stream_anthropic_like_messages(KIMI_CONFIG, model, context, options)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::kimi::kimi_k2_5;
    use crate::types::{
        Api, AssistantMessageEvent, Content, KnownProvider, Message, Provider, StopReason, Tool,
        UserContent, UserMessage,
    };
    use futures::StreamExt;
    use std::env;

    fn require_live_api_key() {
        assert!(
            env::var("KIMI_API_KEY").is_ok(),
            "KIMI_API_KEY must be set to run live Kimi tests"
        );
    }

    fn text_context(prompt: &str) -> Context {
        Context {
            system_prompt: Some("You are concise.".to_string()),
            messages: vec![Message::User(UserMessage {
                content: UserContent::Text(prompt.to_string()),
                timestamp: 0,
            })],
            tools: None,
        }
    }

    #[tokio::test]
    #[ignore = "live API test"]
    async fn live_kimi_complete_returns_typed_text_message() {
        require_live_api_key();

        let model = kimi_k2_5();
        let result = crate::complete(
            &model,
            &text_context("Reply with exactly: hello from kimi"),
            Some(OpenAICompletionsOptions {
                max_tokens: Some(64),
                ..Default::default()
            }),
        )
        .await
        .expect("kimi complete should succeed");

        assert_eq!(result.api, Api::AnthropicMessages);
        assert_eq!(result.provider, Provider::Known(KnownProvider::Kimi));
        assert_eq!(result.model, "kimi-coding");
        assert!(matches!(
            result.stop_reason,
            StopReason::Stop | StopReason::Length
        ));
        assert!(matches!(result.content.first(), Some(Content::Text { .. })));
    }

    #[tokio::test]
    #[ignore = "live API test"]
    async fn live_kimi_stream_emits_typed_text_events() {
        require_live_api_key();

        let model = kimi_k2_5();
        let mut stream = crate::stream(
            &model,
            &text_context("Say hello in one short sentence."),
            Some(OpenAICompletionsOptions {
                max_tokens: Some(64),
                ..Default::default()
            }),
        )
        .expect("kimi stream should start");

        let events: Vec<_> = stream.by_ref().collect().await;

        assert!(events.iter().any(|event| matches!(
            event,
            AssistantMessageEvent::Start { partial }
                if partial.provider == Provider::Known(KnownProvider::Kimi)
                    && partial.api == Api::AnthropicMessages
        )));
        assert!(events
            .iter()
            .any(|event| matches!(event, AssistantMessageEvent::TextStart { .. })));
        assert!(events
            .iter()
            .any(|event| matches!(event, AssistantMessageEvent::TextDelta { .. })));
        assert!(events.iter().any(|event| matches!(
            event,
            AssistantMessageEvent::Done { message, .. }
                if message.provider == Provider::Known(KnownProvider::Kimi)
        )));
    }

    #[tokio::test]
    #[ignore = "live API test"]
    async fn live_kimi_complete_accepts_reasoning_enabled_requests() {
        require_live_api_key();

        let model = kimi_k2_5();
        let result = crate::complete(
            &model,
            &text_context(
                "Think step by step, but keep the final answer to one short sentence: what is 27 times 14?",
            ),
            Some(OpenAICompletionsOptions {
                max_tokens: Some(256),
                ..Default::default()
            }),
        )
        .await
        .expect("kimi reasoning request should succeed");

        assert_eq!(result.api, Api::AnthropicMessages);
        assert_eq!(result.provider, Provider::Known(KnownProvider::Kimi));
        assert!(matches!(
            result.stop_reason,
            StopReason::Stop | StopReason::Length
        ));
        assert!(!result.content.is_empty());

        if let Some(Content::Thinking { inner }) = result
            .content
            .iter()
            .find(|content| matches!(content, Content::Thinking { .. }))
        {
            assert!(!inner.thinking.is_empty());
        }
    }

    #[tokio::test]
    #[ignore = "live API test"]
    async fn live_kimi_complete_returns_typed_tool_call() {
        require_live_api_key();

        let model = kimi_k2_5();
        let context = Context {
            system_prompt: None,
            messages: vec![Message::User(UserMessage {
                content: UserContent::Text(
                    "Use the get_weather tool for Austin, TX. Do not answer directly.".to_string(),
                ),
                timestamp: 0,
            })],
            tools: Some(vec![Tool::new(
                "get_weather",
                "Get the weather for a city",
                serde_json::json!({
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"}
                    },
                    "required": ["city"]
                }),
            )]),
        };

        let result = crate::complete(
            &model,
            &context,
            Some(OpenAICompletionsOptions {
                max_tokens: Some(256),
                ..Default::default()
            }),
        )
        .await
        .expect("kimi tool call should succeed");

        assert_eq!(result.api, Api::AnthropicMessages);
        assert_eq!(result.provider, Provider::Known(KnownProvider::Kimi));
        assert_eq!(result.stop_reason, StopReason::ToolUse);
        assert!(matches!(
            result.content.first(),
            Some(Content::ToolCall { inner })
                if inner.name == "get_weather"
                    && inner.arguments["city"] == serde_json::json!("Austin, TX")
        ));
    }
}
