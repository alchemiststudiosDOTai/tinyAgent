use crate::types::{InputType, KnownProvider, Model, ModelCost, Provider, ZaiCompletions};

const ZAI_BASE_URL: &str = "https://api.z.ai/api/paas/v4/chat/completions";
const LARGE_CONTEXT_WINDOW: u32 = 200_000;
const LARGE_MAX_OUTPUT_TOKENS: u32 = 128_000;
const STANDARD_CONTEXT_WINDOW: u32 = 128_000;
const STANDARD_MAX_OUTPUT_TOKENS: u32 = 96_000;
const GLM_4_32B_0414_128K_MAX_OUTPUT_TOKENS: u32 = 16_000;

const ZERO_MODEL_COST: ModelCost = ModelCost {
    input: 0.0,
    output: 0.0,
    cache_read: 0.0,
    cache_write: 0.0,
};

fn build_glm_model(
    id: &str,
    name: &str,
    context_window: u32,
    max_tokens: u32,
) -> Model<ZaiCompletions> {
    Model {
        id: id.to_string(),
        name: name.to_string(),
        api: ZaiCompletions,
        provider: Provider::Known(KnownProvider::Zai),
        base_url: ZAI_BASE_URL.to_string(),
        reasoning: true,
        input: vec![InputType::Text],
        cost: ZERO_MODEL_COST,
        context_window,
        max_tokens,
        headers: None,
        compat: None,
    }
}

pub fn glm_5() -> Model<ZaiCompletions> {
    build_glm_model(
        "glm-5",
        "GLM 5",
        LARGE_CONTEXT_WINDOW,
        LARGE_MAX_OUTPUT_TOKENS,
    )
}

pub fn glm_4_7() -> Model<ZaiCompletions> {
    build_glm_model(
        "glm-4.7",
        "GLM 4.7",
        LARGE_CONTEXT_WINDOW,
        LARGE_MAX_OUTPUT_TOKENS,
    )
}

pub fn glm_4_7_flash() -> Model<ZaiCompletions> {
    build_glm_model(
        "glm-4.7-flash",
        "GLM 4.7 Flash",
        LARGE_CONTEXT_WINDOW,
        LARGE_MAX_OUTPUT_TOKENS,
    )
}

pub fn glm_4_7_flashx() -> Model<ZaiCompletions> {
    build_glm_model(
        "glm-4.7-flashx",
        "GLM 4.7 FlashX",
        LARGE_CONTEXT_WINDOW,
        LARGE_MAX_OUTPUT_TOKENS,
    )
}

pub fn glm_4_6() -> Model<ZaiCompletions> {
    build_glm_model(
        "glm-4.6",
        "GLM 4.6",
        LARGE_CONTEXT_WINDOW,
        LARGE_MAX_OUTPUT_TOKENS,
    )
}

pub fn glm_4_5() -> Model<ZaiCompletions> {
    build_glm_model(
        "glm-4.5",
        "GLM 4.5",
        STANDARD_CONTEXT_WINDOW,
        STANDARD_MAX_OUTPUT_TOKENS,
    )
}

pub fn glm_4_5_air() -> Model<ZaiCompletions> {
    build_glm_model(
        "glm-4.5-air",
        "GLM 4.5 Air",
        STANDARD_CONTEXT_WINDOW,
        STANDARD_MAX_OUTPUT_TOKENS,
    )
}

pub fn glm_4_5_x() -> Model<ZaiCompletions> {
    build_glm_model(
        "glm-4.5-x",
        "GLM 4.5 X",
        STANDARD_CONTEXT_WINDOW,
        STANDARD_MAX_OUTPUT_TOKENS,
    )
}

pub fn glm_4_5_airx() -> Model<ZaiCompletions> {
    build_glm_model(
        "glm-4.5-airx",
        "GLM 4.5 AirX",
        STANDARD_CONTEXT_WINDOW,
        STANDARD_MAX_OUTPUT_TOKENS,
    )
}

pub fn glm_4_5_flash() -> Model<ZaiCompletions> {
    build_glm_model(
        "glm-4.5-flash",
        "GLM 4.5 Flash",
        STANDARD_CONTEXT_WINDOW,
        STANDARD_MAX_OUTPUT_TOKENS,
    )
}

pub fn glm_4_32b_0414_128k() -> Model<ZaiCompletions> {
    build_glm_model(
        "glm-4-32b-0414-128k",
        "GLM 4 32B 0414 128K",
        STANDARD_CONTEXT_WINDOW,
        GLM_4_32B_0414_128K_MAX_OUTPUT_TOKENS,
    )
}

#[cfg(test)]
mod tests {
    use super::{
        glm_4_32b_0414_128k, glm_4_5, glm_4_5_air, glm_4_5_airx, glm_4_5_flash, glm_4_5_x, glm_4_6,
        glm_4_7, glm_4_7_flash, glm_4_7_flashx, glm_5, ZAI_BASE_URL,
    };
    use crate::types::{Api, ApiType, InputType, KnownProvider, Model, Provider, ZaiCompletions};

    type Constructor = fn() -> Model<ZaiCompletions>;

    #[test]
    fn glm_model_constructors_match_catalog_contract() {
        let cases: [(Constructor, &str, u32, u32); 11] = [
            (glm_5, "glm-5", 200_000, 128_000),
            (glm_4_7, "glm-4.7", 200_000, 128_000),
            (glm_4_7_flash, "glm-4.7-flash", 200_000, 128_000),
            (glm_4_7_flashx, "glm-4.7-flashx", 200_000, 128_000),
            (glm_4_6, "glm-4.6", 200_000, 128_000),
            (glm_4_5, "glm-4.5", 128_000, 96_000),
            (glm_4_5_air, "glm-4.5-air", 128_000, 96_000),
            (glm_4_5_x, "glm-4.5-x", 128_000, 96_000),
            (glm_4_5_airx, "glm-4.5-airx", 128_000, 96_000),
            (glm_4_5_flash, "glm-4.5-flash", 128_000, 96_000),
            (glm_4_32b_0414_128k, "glm-4-32b-0414-128k", 128_000, 16_000),
        ];

        for (constructor, expected_id, expected_context_window, expected_max_tokens) in cases {
            let model = constructor();

            assert_eq!(model.id, expected_id);
            assert_eq!(model.api.api(), Api::ZaiCompletions);
            assert_eq!(model.provider, Provider::Known(KnownProvider::Zai));
            assert_eq!(model.base_url, ZAI_BASE_URL);
            assert!(model.reasoning);
            assert_eq!(model.input, vec![InputType::Text]);
            assert_eq!(model.context_window, expected_context_window);
            assert_eq!(model.max_tokens, expected_max_tokens);
            assert!(model.headers.is_none());
            assert!(model.compat.is_none());
        }
    }
}
