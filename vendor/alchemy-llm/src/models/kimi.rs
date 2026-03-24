use crate::types::{AnthropicMessages, InputType, KnownProvider, Model, ModelCost, Provider};

const KIMI_BASE_URL: &str = "https://api.kimi.com/coding";
const DEFAULT_CONTEXT_WINDOW: u32 = 128_000;
const DEFAULT_MAX_OUTPUT_TOKENS: u32 = 16_384;
const ZERO_MODEL_COST: ModelCost = ModelCost {
    input: 0.0,
    output: 0.0,
    cache_read: 0.0,
    cache_write: 0.0,
};

/// Build the first-class Kimi Coding model on the shared Anthropic-style path.
///
/// The Kimi Coding API matches the Anthropic Messages request/stream shape closely
/// enough to reuse the same runtime contract while keeping Kimi as its own
/// provider identity and auth/base URL configuration.
pub fn kimi_k2_5() -> Model<AnthropicMessages> {
    Model {
        id: "kimi-coding".to_string(),
        name: "Kimi K2.5".to_string(),
        api: AnthropicMessages,
        provider: Provider::Known(KnownProvider::Kimi),
        base_url: KIMI_BASE_URL.to_string(),
        reasoning: true,
        input: vec![InputType::Text],
        cost: ZERO_MODEL_COST,
        context_window: DEFAULT_CONTEXT_WINDOW,
        max_tokens: DEFAULT_MAX_OUTPUT_TOKENS,
        headers: None,
        compat: None,
    }
}

#[cfg(test)]
mod tests {
    use super::{kimi_k2_5, KIMI_BASE_URL};
    use crate::types::{Api, ApiType, InputType, KnownProvider, Provider};

    #[test]
    fn kimi_model_uses_anthropic_messages_path() {
        let model = kimi_k2_5();

        assert_eq!(model.id, "kimi-coding");
        assert_eq!(model.name, "Kimi K2.5");
        assert_eq!(model.api.api(), Api::AnthropicMessages);
        assert_eq!(model.provider, Provider::Known(KnownProvider::Kimi));
        assert_eq!(model.base_url, KIMI_BASE_URL);
        assert!(model.reasoning);
        assert_eq!(model.input, vec![InputType::Text]);
        assert_eq!(model.context_window, 128_000);
        assert_eq!(model.max_tokens, 16_384);
        assert!(model.headers.is_none());
        assert!(model.compat.is_none());
    }
}
