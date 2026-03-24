use crate::types::{InputType, KnownProvider, Model, ModelCost, OpenAICompletions, Provider};

const FEATHERLESS_BASE_URL: &str = "https://api.featherless.ai/v1/chat/completions";
const DEFAULT_CONTEXT_WINDOW: u32 = 128_000;
const DEFAULT_MAX_OUTPUT_TOKENS: u32 = 16_384;
const ZERO_MODEL_COST: ModelCost = ModelCost {
    input: 0.0,
    output: 0.0,
    cache_read: 0.0,
    cache_write: 0.0,
};

/// Build a first-class Featherless model on the shared OpenAI-compatible path.
///
/// Featherless exposes a large dynamic model catalog, so this constructor accepts
/// the model identifier directly instead of curating one helper per model.
/// Callers may override metadata fields on the returned model if they have more
/// precise limits from `/v1/models`.
pub fn featherless_model(id: impl Into<String>) -> Model<OpenAICompletions> {
    let id = id.into();

    Model {
        name: id.clone(),
        id,
        api: OpenAICompletions,
        provider: Provider::Known(KnownProvider::Featherless),
        base_url: FEATHERLESS_BASE_URL.to_string(),
        reasoning: false,
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
    use super::{featherless_model, FEATHERLESS_BASE_URL};
    use crate::types::{Api, ApiType, InputType, KnownProvider, Provider};

    #[test]
    fn featherless_model_uses_first_class_openai_compatible_path() {
        let model = featherless_model("moonshotai/Kimi-K2.5");

        assert_eq!(model.id, "moonshotai/Kimi-K2.5");
        assert_eq!(model.name, "moonshotai/Kimi-K2.5");
        assert_eq!(model.api.api(), Api::OpenAICompletions);
        assert_eq!(model.provider, Provider::Known(KnownProvider::Featherless));
        assert_eq!(model.base_url, FEATHERLESS_BASE_URL);
        assert!(!model.reasoning);
        assert_eq!(model.input, vec![InputType::Text]);
        assert_eq!(model.context_window, 128_000);
        assert_eq!(model.max_tokens, 16_384);
        assert!(model.headers.is_none());
        assert!(model.compat.is_none());
    }
}
