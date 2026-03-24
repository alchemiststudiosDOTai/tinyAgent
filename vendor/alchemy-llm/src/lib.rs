pub mod error;
pub mod models;
pub mod providers;
pub mod stream;
pub mod transform;
pub mod types;
pub mod utils;

#[cfg(test)]
pub(crate) mod test_helpers;

pub use error::{Error, Result};
pub use models::{
    claude_haiku_4_5, claude_opus_4_6, claude_sonnet_4_6, featherless_model, glm_4_32b_0414_128k,
    glm_4_5, glm_4_5_air, glm_4_5_airx, glm_4_5_flash, glm_4_5_x, glm_4_6, glm_4_7, glm_4_7_flash,
    glm_4_7_flashx, glm_5, kimi_k2_5, minimax_cn_m2, minimax_cn_m2_1, minimax_cn_m2_1_highspeed,
    minimax_cn_m2_5, minimax_cn_m2_5_highspeed, minimax_cn_m2_7, minimax_cn_m2_7_highspeed,
    minimax_m2, minimax_m2_1, minimax_m2_1_highspeed, minimax_m2_5, minimax_m2_5_highspeed,
    minimax_m2_7, minimax_m2_7_highspeed,
};
pub use providers::{
    get_env_api_key, stream_anthropic_messages, stream_kimi_messages, stream_minimax_completions,
    stream_openai_completions, OpenAICompletionsOptions,
};
pub use stream::{complete, stream, AssistantMessageEventStream};
pub use transform::{transform_messages, transform_messages_simple, TargetModel};
pub use utils::{
    is_context_overflow, parse_streaming_json, parse_streaming_json_smart, sanitize_for_api,
    sanitize_surrogates, validate_tool_arguments, validate_tool_call, ThinkFragment,
    ThinkTagParser,
};
