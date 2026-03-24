//! Shared utilities for provider implementations.

mod anthropic_like;
mod http;
mod openai_like_messages;
mod openai_like_runtime;
mod stream_blocks;
mod timestamp;

pub(crate) use anthropic_like::{
    stream_anthropic_like_messages, AnthropicLikeAuth, AnthropicLikeProviderConfig,
};
pub(crate) use http::merge_headers;
pub(crate) use openai_like_messages::{
    convert_messages, convert_tools, AssistantThinkingMode, OpenAiLikeMessageOptions,
    SystemPromptRole,
};
pub(crate) use openai_like_runtime::{
    initialize_output, process_sse_stream_with_event, push_stream_done, push_stream_error,
    run_openai_like_stream, run_openai_like_stream_without_state, OpenAiLikeRequest,
};
pub(crate) use stream_blocks::finish_current_block;
pub(crate) use stream_blocks::{
    apply_deferred_tool_calls, handle_reasoning_delta, handle_text_delta, handle_tool_calls,
    map_stop_reason, prepare_openai_like_chunk, update_usage_from_chunk, CurrentBlock,
    OpenAiLikeStreamChunk, OpenAiLikeToolCallDelta, ReasoningDelta,
};
