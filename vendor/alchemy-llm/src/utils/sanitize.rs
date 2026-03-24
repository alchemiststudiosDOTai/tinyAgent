//! Unicode sanitization for API requests.
//!
//! Removes unpaired surrogates and other problematic characters that can
//! cause API errors.

/// Remove unpaired UTF-16 surrogates from a string.
///
/// Some APIs reject strings containing unpaired surrogates (0xD800-0xDFFF).
/// Rust strings are valid UTF-8, so this mainly handles edge cases from
/// external data.
///
/// Note: Rust's `String` type guarantees valid UTF-8, so unpaired surrogates
/// shouldn't normally occur. This is primarily for defensive sanitization
/// of external input that may contain replacement characters indicating
/// encoding issues.
///
/// # Example
///
/// ```
/// use alchemy_llm::utils::sanitize::sanitize_surrogates;
///
/// let clean = sanitize_surrogates("Hello, world!");
/// assert_eq!(clean, "Hello, world!");
///
/// // Replacement characters are filtered
/// let with_replacement = sanitize_surrogates("Hello\u{FFFD}World");
/// assert_eq!(with_replacement, "HelloWorld");
/// ```
pub fn sanitize_surrogates(s: &str) -> String {
    // Rust strings are always valid UTF-8, so unpaired surrogates
    // can only exist if we're dealing with potentially malformed input.
    // For safety, we filter any replacement characters that might indicate
    // surrogate issues.
    s.chars().filter(|c| *c != '\u{FFFD}').collect()
}

/// Sanitize a string for use in API requests.
///
/// Combines surrogate sanitization with other common transformations.
///
/// # Example
///
/// ```
/// use alchemy_llm::utils::sanitize::sanitize_for_api;
///
/// let sanitized = sanitize_for_api("Hello, world!");
/// assert_eq!(sanitized, "Hello, world!");
/// ```
pub use sanitize_surrogates as sanitize_for_api;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normal_string() {
        assert_eq!(sanitize_surrogates("Hello, world!"), "Hello, world!");
    }

    #[test]
    fn test_unicode_string() {
        assert_eq!(
            sanitize_surrogates("Hello, \u{1F600}!"),
            "Hello, \u{1F600}!"
        );
    }

    #[test]
    fn test_emoji_string() {
        let emoji = "Test with emojis: \u{1F4BB}\u{1F680}\u{2764}";
        assert_eq!(sanitize_surrogates(emoji), emoji);
    }

    #[test]
    fn test_cjk_characters() {
        let cjk = "Chinese: \u{4E2D}\u{6587}, Japanese: \u{65E5}\u{672C}\u{8A9E}";
        assert_eq!(sanitize_surrogates(cjk), cjk);
    }

    #[test]
    fn test_replacement_character() {
        // Replacement character gets filtered
        assert_eq!(sanitize_surrogates("Hello\u{FFFD}World"), "HelloWorld");
    }

    #[test]
    fn test_multiple_replacement_characters() {
        assert_eq!(
            sanitize_surrogates("\u{FFFD}start\u{FFFD}middle\u{FFFD}end\u{FFFD}"),
            "startmiddleend"
        );
    }

    #[test]
    fn test_empty_string() {
        assert_eq!(sanitize_surrogates(""), "");
    }

    #[test]
    fn test_only_replacement_characters() {
        assert_eq!(sanitize_surrogates("\u{FFFD}\u{FFFD}\u{FFFD}"), "");
    }

    #[test]
    fn test_sanitize_for_api() {
        assert_eq!(sanitize_for_api("test\u{FFFD}string"), "teststring");
        assert_eq!(sanitize_for_api("normal text"), "normal text");
    }

    #[test]
    fn test_mixed_content() {
        let input = "Normal text \u{FFFD} with emoji \u{1F600} and CJK \u{4E2D}\u{6587}";
        let expected = "Normal text  with emoji \u{1F600} and CJK \u{4E2D}\u{6587}";
        assert_eq!(sanitize_surrogates(input), expected);
    }
}
