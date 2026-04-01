use crate::types::{AnthropicMessages, InputType, KnownProvider, Model, ModelCost, Provider};

const ANTHROPIC_BASE_URL: &str = "https://api.anthropic.com";

fn build_anthropic_model(
    id: &str,
    name: &str,
    reasoning: bool,
    context_window: u32,
    max_tokens: u32,
    cost: ModelCost,
) -> Model<AnthropicMessages> {
    Model {
        id: id.to_string(),
        name: name.to_string(),
        api: AnthropicMessages,
        provider: Provider::Known(KnownProvider::Anthropic),
        base_url: ANTHROPIC_BASE_URL.to_string(),
        reasoning,
        input: vec![InputType::Text, InputType::Image],
        cost,
        context_window,
        max_tokens,
        headers: None,
        compat: None,
    }
}

pub fn claude_opus_4_6() -> Model<AnthropicMessages> {
    build_anthropic_model(
        "claude-opus-4-6",
        "Claude Opus 4.6",
        true,
        200_000,
        128_000,
        ModelCost {
            input: 0.005,
            output: 0.025,
            cache_read: 0.0005,
            cache_write: 0.00625,
        },
    )
}

pub fn claude_sonnet_4_6() -> Model<AnthropicMessages> {
    build_anthropic_model(
        "claude-sonnet-4-6",
        "Claude Sonnet 4.6",
        true,
        200_000,
        64_000,
        ModelCost {
            input: 0.003,
            output: 0.015,
            cache_read: 0.0003,
            cache_write: 0.00375,
        },
    )
}

pub fn claude_haiku_4_5() -> Model<AnthropicMessages> {
    build_anthropic_model(
        "claude-haiku-4-5-20251001",
        "Claude Haiku 4.5",
        true,
        200_000,
        64_000,
        ModelCost {
            input: 0.001,
            output: 0.005,
            cache_read: 0.0001,
            cache_write: 0.00125,
        },
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{Api, ApiType};

    #[test]
    fn claude_opus_4_6_has_correct_api_and_provider() {
        let model = claude_opus_4_6();
        assert_eq!(model.api.api(), Api::AnthropicMessages);
        assert_eq!(model.provider, Provider::Known(KnownProvider::Anthropic));
        assert!(model.reasoning);
        assert_eq!(model.max_tokens, 128_000);
    }

    #[test]
    fn all_models_support_reasoning() {
        for model in [claude_opus_4_6(), claude_sonnet_4_6(), claude_haiku_4_5()] {
            assert!(model.reasoning, "{} should support reasoning", model.name);
        }
    }
}
