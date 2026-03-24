//! Context overflow detection across different LLM providers.
//!
//! Detects when input exceeds a model's context window, either through
//! explicit error messages or by detecting silent overflow.

use crate::types::{AssistantMessage, StopReason};
use once_cell::sync::Lazy;
use regex::Regex;

/// Patterns to detect context overflow errors from different providers.
static OVERFLOW_PATTERNS: Lazy<Vec<Regex>> = Lazy::new(|| {
    vec![
        // Anthropic
        Regex::new(r"(?i)prompt is too long").expect("valid regex"),
        // Amazon Bedrock
        Regex::new(r"(?i)input is too long for requested model").expect("valid regex"),
        // OpenAI
        Regex::new(r"(?i)exceeds the context window").expect("valid regex"),
        // Google Gemini
        Regex::new(r"(?i)input token count.*exceeds the maximum").expect("valid regex"),
        // xAI Grok
        Regex::new(r"(?i)maximum prompt length is \d+").expect("valid regex"),
        // Groq
        Regex::new(r"(?i)reduce the length of the messages").expect("valid regex"),
        // OpenRouter
        Regex::new(r"(?i)maximum context length is \d+ tokens").expect("valid regex"),
        // GitHub Copilot
        Regex::new(r"(?i)exceeds the limit of \d+").expect("valid regex"),
        // llama.cpp
        Regex::new(r"(?i)exceeds the available context size").expect("valid regex"),
        // LM Studio
        Regex::new(r"(?i)greater than the context length").expect("valid regex"),
        // MiniMax
        Regex::new(r"(?i)context window exceeds limit").expect("valid regex"),
        // Generic patterns
        Regex::new(r"(?i)context[_ ]length[_ ]exceeded").expect("valid regex"),
        Regex::new(r"(?i)too many tokens").expect("valid regex"),
        Regex::new(r"(?i)token limit exceeded").expect("valid regex"),
    ]
});

/// Pattern for providers that return status codes without body (Cerebras, Mistral)
static STATUS_CODE_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"(?i)^4(00|13|29)\s*(status code)?\s*\(no body\)").expect("valid regex")
});

/// Check if an assistant message represents a context overflow error.
///
/// Handles two cases:
/// 1. **Error-based overflow**: Provider returns error with detectable message
/// 2. **Silent overflow**: Provider accepts but usage.input > context_window
///
/// # Arguments
///
/// * `message` - The assistant message to check
/// * `context_window` - Optional context window size for detecting silent overflow
///
/// # Provider Reliability
///
/// **Reliable detection:**
/// - Anthropic, OpenAI, Google Gemini, xAI, Groq, Cerebras, Mistral,
///   OpenRouter, llama.cpp, LM Studio
///
/// **Unreliable detection:**
/// - z.ai: Sometimes accepts silently (pass context_window to detect)
/// - Ollama: Silently truncates input (cannot detect)
///
/// # Example
///
/// ```ignore
/// use alchemy::utils::overflow::is_context_overflow;
///
/// if is_context_overflow(&message, Some(200_000)) {
///     // Handle overflow - maybe summarize conversation
/// }
/// ```
pub fn is_context_overflow(message: &AssistantMessage, context_window: Option<u32>) -> bool {
    // Case 1: Check error message patterns
    if message.stop_reason == StopReason::Error {
        if let Some(ref error_msg) = message.error_message {
            // Check known patterns
            if OVERFLOW_PATTERNS.iter().any(|p| p.is_match(error_msg)) {
                return true;
            }

            // Check for status code pattern (Cerebras, Mistral)
            if STATUS_CODE_PATTERN.is_match(error_msg) {
                return true;
            }
        }
    }

    // Case 2: Silent overflow (z.ai style)
    if let Some(window) = context_window {
        if message.stop_reason == StopReason::Stop {
            let input_tokens = message.usage.input;
            if input_tokens > window {
                return true;
            }
        }
    }

    false
}

/// Get the overflow patterns (for testing).
pub fn get_overflow_patterns() -> &'static [Regex] {
    &OVERFLOW_PATTERNS
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{Api, Cost, KnownProvider, Provider, Usage};

    fn make_message(
        stop_reason: StopReason,
        error_message: Option<&str>,
        input: u32,
    ) -> AssistantMessage {
        AssistantMessage {
            content: vec![],
            api: Api::AnthropicMessages,
            provider: Provider::Known(KnownProvider::Anthropic),
            model: "test".to_string(),
            usage: Usage {
                input,
                output: 0,
                cache_read: 0,
                cache_write: 0,
                total_tokens: input,
                cost: Cost::default(),
            },
            stop_reason,
            error_message: error_message.map(String::from),
            timestamp: 0,
        }
    }

    #[test]
    fn test_anthropic_overflow() {
        let msg = make_message(
            StopReason::Error,
            Some("prompt is too long: 213462 tokens > 200000 maximum"),
            213462,
        );
        assert!(is_context_overflow(&msg, None));
    }

    #[test]
    fn test_openai_overflow() {
        let msg = make_message(
            StopReason::Error,
            Some("Your input exceeds the context window of this model"),
            100000,
        );
        assert!(is_context_overflow(&msg, None));
    }

    #[test]
    fn test_bedrock_overflow() {
        let msg = make_message(
            StopReason::Error,
            Some("The input is too long for requested model"),
            150000,
        );
        assert!(is_context_overflow(&msg, None));
    }

    #[test]
    fn test_gemini_overflow() {
        let msg = make_message(
            StopReason::Error,
            Some("Input token count (150000) exceeds the maximum allowed (128000)"),
            150000,
        );
        assert!(is_context_overflow(&msg, None));
    }

    #[test]
    fn test_groq_overflow() {
        let msg = make_message(
            StopReason::Error,
            Some("Please reduce the length of the messages"),
            100000,
        );
        assert!(is_context_overflow(&msg, None));
    }

    #[test]
    fn test_openrouter_overflow() {
        let msg = make_message(
            StopReason::Error,
            Some("This model's maximum context length is 8192 tokens"),
            10000,
        );
        assert!(is_context_overflow(&msg, None));
    }

    #[test]
    fn test_llamacpp_overflow() {
        let msg = make_message(
            StopReason::Error,
            Some("The request exceeds the available context size"),
            50000,
        );
        assert!(is_context_overflow(&msg, None));
    }

    #[test]
    fn test_generic_overflow() {
        let msg = make_message(StopReason::Error, Some("context_length_exceeded"), 100000);
        assert!(is_context_overflow(&msg, None));

        let msg2 = make_message(
            StopReason::Error,
            Some("Error: too many tokens in request"),
            100000,
        );
        assert!(is_context_overflow(&msg2, None));
    }

    #[test]
    fn test_status_code_overflow() {
        let msg = make_message(StopReason::Error, Some("413 status code (no body)"), 100000);
        assert!(is_context_overflow(&msg, None));

        let msg2 = make_message(StopReason::Error, Some("400 (no body)"), 100000);
        assert!(is_context_overflow(&msg2, None));
    }

    #[test]
    fn test_silent_overflow() {
        let msg = make_message(StopReason::Stop, None, 250000);
        assert!(is_context_overflow(&msg, Some(200000)));
        assert!(!is_context_overflow(&msg, Some(300000)));
        assert!(!is_context_overflow(&msg, None));
    }

    #[test]
    fn test_silent_overflow_with_cache() {
        let mut msg = make_message(StopReason::Stop, None, 100000);
        msg.usage.cache_read = 150000;
        // Silent overflow uses raw input tokens only.
        assert!(!is_context_overflow(&msg, Some(200000)));
    }

    #[test]
    fn test_no_overflow() {
        let msg = make_message(StopReason::Stop, None, 50000);
        assert!(!is_context_overflow(&msg, Some(200000)));
        assert!(!is_context_overflow(&msg, None));
    }

    #[test]
    fn test_error_without_overflow_message() {
        let msg = make_message(StopReason::Error, Some("Rate limit exceeded"), 50000);
        assert!(!is_context_overflow(&msg, None));
    }

    #[test]
    fn test_overflow_patterns_not_empty() {
        let patterns = get_overflow_patterns();
        assert!(!patterns.is_empty());
        assert!(patterns.len() >= 10);
    }
}
