use crate::types::{InputType, KnownProvider, MinimaxCompletions, Model, ModelCost, Provider};

const MINIMAX_GLOBAL_BASE_URL: &str = "https://api.minimax.io/v1/chat/completions";
const MINIMAX_CN_BASE_URL: &str = "https://api.minimax.chat/v1/chat/completions";
const MINIMAX_CONTEXT_WINDOW: u32 = 204_800;
const MINIMAX_MAX_OUTPUT_TOKENS: u32 = 16_384;
const ZERO_MODEL_COST: ModelCost = ModelCost {
    input: 0.0,
    output: 0.0,
    cache_read: 0.0,
    cache_write: 0.0,
};

fn build_minimax_model(
    id: &str,
    name: &str,
    provider: KnownProvider,
    base_url: &str,
) -> Model<MinimaxCompletions> {
    Model {
        id: id.to_string(),
        name: name.to_string(),
        api: MinimaxCompletions,
        provider: Provider::Known(provider),
        base_url: base_url.to_string(),
        reasoning: true,
        input: vec![InputType::Text],
        cost: ZERO_MODEL_COST,
        context_window: MINIMAX_CONTEXT_WINDOW,
        max_tokens: MINIMAX_MAX_OUTPUT_TOKENS,
        headers: None,
        compat: None,
    }
}

pub fn minimax_m2_5() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2.5",
        "MiniMax M2.5",
        KnownProvider::Minimax,
        MINIMAX_GLOBAL_BASE_URL,
    )
}

pub fn minimax_m2_5_highspeed() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2.5-highspeed",
        "MiniMax M2.5 Highspeed",
        KnownProvider::Minimax,
        MINIMAX_GLOBAL_BASE_URL,
    )
}

pub fn minimax_m2_1() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2.1",
        "MiniMax M2.1",
        KnownProvider::Minimax,
        MINIMAX_GLOBAL_BASE_URL,
    )
}

pub fn minimax_m2_1_highspeed() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2.1-highspeed",
        "MiniMax M2.1 Highspeed",
        KnownProvider::Minimax,
        MINIMAX_GLOBAL_BASE_URL,
    )
}

pub fn minimax_m2() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2",
        "MiniMax M2",
        KnownProvider::Minimax,
        MINIMAX_GLOBAL_BASE_URL,
    )
}

pub fn minimax_cn_m2_5() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2.5",
        "MiniMax M2.5 (CN)",
        KnownProvider::MinimaxCn,
        MINIMAX_CN_BASE_URL,
    )
}

pub fn minimax_cn_m2_5_highspeed() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2.5-highspeed",
        "MiniMax M2.5 Highspeed (CN)",
        KnownProvider::MinimaxCn,
        MINIMAX_CN_BASE_URL,
    )
}

pub fn minimax_cn_m2_1() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2.1",
        "MiniMax M2.1 (CN)",
        KnownProvider::MinimaxCn,
        MINIMAX_CN_BASE_URL,
    )
}

pub fn minimax_cn_m2_1_highspeed() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2.1-highspeed",
        "MiniMax M2.1 Highspeed (CN)",
        KnownProvider::MinimaxCn,
        MINIMAX_CN_BASE_URL,
    )
}

pub fn minimax_m2_7() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2.7",
        "MiniMax M2.7",
        KnownProvider::Minimax,
        MINIMAX_GLOBAL_BASE_URL,
    )
}

pub fn minimax_m2_7_highspeed() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2.7-highspeed",
        "MiniMax M2.7 Highspeed",
        KnownProvider::Minimax,
        MINIMAX_GLOBAL_BASE_URL,
    )
}

pub fn minimax_cn_m2_7() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2.7",
        "MiniMax M2.7 (CN)",
        KnownProvider::MinimaxCn,
        MINIMAX_CN_BASE_URL,
    )
}

pub fn minimax_cn_m2_7_highspeed() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2.7-highspeed",
        "MiniMax M2.7 Highspeed (CN)",
        KnownProvider::MinimaxCn,
        MINIMAX_CN_BASE_URL,
    )
}

pub fn minimax_cn_m2() -> Model<MinimaxCompletions> {
    build_minimax_model(
        "MiniMax-M2",
        "MiniMax M2 (CN)",
        KnownProvider::MinimaxCn,
        MINIMAX_CN_BASE_URL,
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{Api, ApiType};

    #[test]
    fn minimax_model_has_first_class_api() {
        let model = minimax_m2_5();
        assert_eq!(model.api.api(), Api::MinimaxCompletions);
        assert_eq!(model.provider, Provider::Known(KnownProvider::Minimax));
        assert_eq!(model.base_url, MINIMAX_GLOBAL_BASE_URL);
    }

    #[test]
    fn minimax_cn_model_uses_cn_provider_and_url() {
        let model = minimax_cn_m2_1_highspeed();
        assert_eq!(model.api.api(), Api::MinimaxCompletions);
        assert_eq!(model.provider, Provider::Known(KnownProvider::MinimaxCn));
        assert_eq!(model.base_url, MINIMAX_CN_BASE_URL);
    }
}
