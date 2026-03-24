pub mod anthropic;
pub mod featherless;
pub mod kimi;
pub mod minimax;
pub mod zai;

pub use anthropic::{claude_haiku_4_5, claude_opus_4_6, claude_sonnet_4_6};
pub use featherless::featherless_model;
pub use kimi::kimi_k2_5;
pub use minimax::{
    minimax_cn_m2, minimax_cn_m2_1, minimax_cn_m2_1_highspeed, minimax_cn_m2_5,
    minimax_cn_m2_5_highspeed, minimax_cn_m2_7, minimax_cn_m2_7_highspeed, minimax_m2,
    minimax_m2_1, minimax_m2_1_highspeed, minimax_m2_5, minimax_m2_5_highspeed, minimax_m2_7,
    minimax_m2_7_highspeed,
};
pub use zai::{
    glm_4_32b_0414_128k, glm_4_5, glm_4_5_air, glm_4_5_airx, glm_4_5_flash, glm_4_5_x, glm_4_6,
    glm_4_7, glm_4_7_flash, glm_4_7_flashx, glm_5,
};
