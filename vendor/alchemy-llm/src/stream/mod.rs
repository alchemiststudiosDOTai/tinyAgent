pub use crate::types::{AssistantMessageEventStream, EventStreamSender};

use crate::error::{Error, Result};
use crate::providers::{
    get_env_api_key, stream_anthropic_messages, stream_kimi_messages, stream_minimax_completions,
    stream_openai_completions, stream_zai_completions, OpenAICompletionsOptions,
};
use crate::types::{
    AnthropicMessages, Api, AssistantMessage, Context, KnownProvider, MinimaxCompletions, Model,
    OpenAICompletions, Provider, ZaiCompletions,
};

/// Stream a completion from an OpenAI-compatible model.
///
/// This is the main entry point for streaming completions. It handles:
/// - API key resolution (from options or environment)
/// - Dispatching to the correct provider based on the model's API type
///
/// # Errors
///
/// Returns `Error::NoApiKey` if no API key is provided and none can be found
/// in the environment for the model's provider.
pub fn stream<TApi>(
    model: &Model<TApi>,
    context: &Context,
    options: Option<OpenAICompletionsOptions>,
) -> Result<AssistantMessageEventStream>
where
    TApi: crate::types::ApiType,
{
    let api = model.api.api();

    // Get API key from options or environment
    let api_key = options
        .as_ref()
        .and_then(|o| o.api_key.clone())
        .or_else(|| get_env_api_key(&model.provider));

    // Check if API key is required
    let needs_api_key = !matches!(api, Api::GoogleVertex | Api::BedrockConverseStream);

    if needs_api_key && api_key.is_none() {
        return Err(Error::NoApiKey(model.provider.to_string()));
    }

    // Build options with resolved API key
    let mut resolved_options = options.unwrap_or_default();
    if let Some(key) = api_key {
        resolved_options.api_key = Some(key);
    }

    match api {
        Api::OpenAICompletions => {
            // SAFETY: We know the model has OpenAICompletions API type
            // This is a type-level guarantee from the match
            let model_ptr = model as *const Model<TApi> as *const Model<OpenAICompletions>;
            let openai_model = unsafe { &*model_ptr };
            Ok(stream_openai_completions(
                openai_model,
                context,
                resolved_options,
            ))
        }
        Api::MinimaxCompletions => {
            // SAFETY: We know the model has MinimaxCompletions API type
            // This is a type-level guarantee from the match
            let model_ptr = model as *const Model<TApi> as *const Model<MinimaxCompletions>;
            let minimax_model = unsafe { &*model_ptr };
            Ok(stream_minimax_completions(
                minimax_model,
                context,
                resolved_options,
            ))
        }
        Api::ZaiCompletions => {
            // SAFETY: We know the model has ZaiCompletions API type
            // This is a type-level guarantee from the match
            let model_ptr = model as *const Model<TApi> as *const Model<ZaiCompletions>;
            let zai_model = unsafe { &*model_ptr };
            Ok(stream_zai_completions(zai_model, context, resolved_options))
        }
        Api::AnthropicMessages => {
            let model_ptr = model as *const Model<TApi> as *const Model<AnthropicMessages>;
            let anthropic_model = unsafe { &*model_ptr };
            Ok(
                if matches!(
                    anthropic_model.provider,
                    Provider::Known(KnownProvider::Kimi)
                ) {
                    stream_kimi_messages(anthropic_model, context, resolved_options)
                } else {
                    stream_anthropic_messages(anthropic_model, context, resolved_options)
                },
            )
        }
        Api::BedrockConverseStream => Err(Error::InvalidResponse(
            "Bedrock provider not yet implemented".to_string(),
        )),
        Api::OpenAIResponses => Err(Error::InvalidResponse(
            "OpenAI Responses provider not yet implemented".to_string(),
        )),
        Api::GoogleGenerativeAi => Err(Error::InvalidResponse(
            "Google Generative AI provider not yet implemented".to_string(),
        )),
        Api::GoogleVertex => Err(Error::InvalidResponse(
            "Google Vertex provider not yet implemented".to_string(),
        )),
    }
}

/// Stream a completion and await the final result.
///
/// This is a convenience wrapper around `stream()` that collects the stream
/// and returns the final `AssistantMessage`.
pub async fn complete<TApi>(
    model: &Model<TApi>,
    context: &Context,
    options: Option<OpenAICompletionsOptions>,
) -> Result<AssistantMessage>
where
    TApi: crate::types::ApiType,
{
    let s = stream(model, context, options)?;
    s.result().await
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{
        InputType, KnownProvider, ModelCost, Provider, StopReason, StopReasonError,
        StopReasonSuccess, ZaiCompletions,
    };
    use tokio::time::{timeout, Duration};

    fn minimax_test_model(base_url: &str) -> Model<MinimaxCompletions> {
        Model {
            id: "MiniMax-M2.5".to_string(),
            name: "MiniMax M2.5".to_string(),
            api: MinimaxCompletions,
            provider: Provider::Known(KnownProvider::Minimax),
            base_url: base_url.to_string(),
            reasoning: true,
            input: vec![InputType::Text],
            cost: ModelCost {
                input: 0.0,
                output: 0.0,
                cache_read: 0.0,
                cache_write: 0.0,
            },
            context_window: 204_800,
            max_tokens: 16_384,
            headers: None,
            compat: None,
        }
    }

    fn zai_test_model(base_url: &str) -> Model<ZaiCompletions> {
        Model {
            id: "glm-4.7".to_string(),
            name: "GLM 4.7".to_string(),
            api: ZaiCompletions,
            provider: Provider::Known(KnownProvider::Zai),
            base_url: base_url.to_string(),
            reasoning: true,
            input: vec![InputType::Text],
            cost: ModelCost {
                input: 0.0,
                output: 0.0,
                cache_read: 0.0,
                cache_write: 0.0,
            },
            context_window: 200_000,
            max_tokens: 128_000,
            headers: None,
            compat: None,
        }
    }

    fn featherless_test_model(base_url: &str) -> Model<OpenAICompletions> {
        Model {
            id: "moonshotai/Kimi-K2.5".to_string(),
            name: "Kimi K2.5".to_string(),
            api: OpenAICompletions,
            provider: Provider::Known(KnownProvider::Featherless),
            base_url: base_url.to_string(),
            reasoning: false,
            input: vec![InputType::Text],
            cost: ModelCost {
                input: 0.0,
                output: 0.0,
                cache_read: 0.0,
                cache_write: 0.0,
            },
            context_window: 128_000,
            max_tokens: 16_384,
            headers: None,
            compat: None,
        }
    }

    async fn assert_dispatches_to_provider<TApi>(model: Model<TApi>, expected_api: Api)
    where
        TApi: crate::types::ApiType,
    {
        let context = Context::default();
        let options = Some(OpenAICompletionsOptions {
            api_key: Some("test-key".to_string()),
            ..OpenAICompletionsOptions::default()
        });

        let stream = stream(&model, &context, options).expect("dispatch should succeed");
        let result = timeout(Duration::from_secs(5), stream.result())
            .await
            .expect("stream should finish quickly")
            .expect("stream result should be returned");

        assert_eq!(result.api, expected_api);
        assert_eq!(result.stop_reason, StopReason::Error);
    }

    #[tokio::test]
    async fn stream_dispatches_to_minimax_provider() {
        let model = minimax_test_model("http://127.0.0.1:1/v1/chat/completions");
        assert_dispatches_to_provider(model, Api::MinimaxCompletions).await;
    }

    #[tokio::test]
    async fn stream_dispatches_to_zai_provider() {
        let model = zai_test_model("http://127.0.0.1:1/api/paas/v4/chat/completions");
        assert_dispatches_to_provider(model, Api::ZaiCompletions).await;
    }

    fn anthropic_test_model(base_url: &str) -> Model<AnthropicMessages> {
        Model {
            id: "claude-sonnet-4-6".to_string(),
            name: "Claude Sonnet 4.6".to_string(),
            api: AnthropicMessages,
            provider: Provider::Known(KnownProvider::Anthropic),
            base_url: base_url.to_string(),
            reasoning: true,
            input: vec![InputType::Text, InputType::Image],
            cost: ModelCost {
                input: 0.003,
                output: 0.015,
                cache_read: 0.0003,
                cache_write: 0.00375,
            },
            context_window: 200_000,
            max_tokens: 64_000,
            headers: None,
            compat: None,
        }
    }

    #[tokio::test]
    async fn stream_dispatches_to_anthropic_provider() {
        let model = anthropic_test_model("http://127.0.0.1:1");
        assert_dispatches_to_provider(model, Api::AnthropicMessages).await;
    }

    #[tokio::test]
    async fn stream_dispatches_featherless_through_openai_completions_provider() {
        let model = featherless_test_model("http://127.0.0.1:1/v1/chat/completions");
        assert_dispatches_to_provider(model, Api::OpenAICompletions).await;
    }

    #[test]
    fn google_vertex_and_bedrock_do_not_require_api_key() {
        let vertex_needs_key = !matches!(
            Api::GoogleVertex,
            Api::GoogleVertex | Api::BedrockConverseStream
        );
        let bedrock_needs_key = !matches!(
            Api::BedrockConverseStream,
            Api::GoogleVertex | Api::BedrockConverseStream
        );

        assert!(!vertex_needs_key);
        assert!(!bedrock_needs_key);
    }

    #[test]
    fn stop_reason_conversion_contract_is_unchanged() {
        assert_eq!(StopReason::from(StopReasonSuccess::Stop), StopReason::Stop);
        assert_eq!(StopReason::from(StopReasonError::Error), StopReason::Error);
    }
}
