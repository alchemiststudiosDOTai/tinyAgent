//! Cross-provider utilities for consistent behavior across all LLM providers.
//!
//! This module provides utilities for:
//! - Tool call validation against JSON schemas
//! - Context overflow detection across different providers
//! - Unicode sanitization for API requests
//! - Partial JSON parsing for streaming tool calls

pub mod json_parse;
pub mod overflow;
pub mod sanitize;
pub mod think_tag_parser;
pub mod validation;

pub use json_parse::{parse_streaming_json, parse_streaming_json_smart};
pub use overflow::{get_overflow_patterns, is_context_overflow};
pub use sanitize::{sanitize_for_api, sanitize_surrogates};
pub use think_tag_parser::{ThinkFragment, ThinkTagParser};
pub use validation::{validate_tool_arguments, validate_tool_call};
