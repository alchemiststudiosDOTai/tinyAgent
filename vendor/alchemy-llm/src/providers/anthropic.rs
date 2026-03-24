use super::openai_completions::OpenAICompletionsOptions;
use super::shared::{
    stream_anthropic_like_messages, AnthropicLikeAuth, AnthropicLikeProviderConfig,
};
use crate::types::{AnthropicMessages, AssistantMessageEventStream, Context, Model};

const ANTHROPIC_CONFIG: AnthropicLikeProviderConfig = AnthropicLikeProviderConfig {
    auth: AnthropicLikeAuth::XApiKey,
    messages_endpoint: "/v1/messages",
    version_header: Some(("anthropic-version", "2023-06-01")),
    beta_header: Some(("anthropic-beta", "interleaved-thinking-2025-05-14")),
};

pub fn stream_anthropic_messages(
    model: &Model<AnthropicMessages>,
    context: &Context,
    options: OpenAICompletionsOptions,
) -> AssistantMessageEventStream {
    stream_anthropic_like_messages(ANTHROPIC_CONFIG, model, context, options)
}
