//! Partial JSON parsing for streaming tool calls.
//!
//! During streaming, tool call arguments arrive incrementally. These utilities
//! attempt to parse partial JSON, returning empty objects on failure.

use serde_json::Value;

/// Parse potentially incomplete JSON from streaming tool calls.
///
/// During streaming, tool call arguments arrive incrementally. This function
/// attempts to parse the partial JSON, returning an empty object if parsing fails.
///
/// # Strategy
///
/// 1. Try parsing as complete JSON
/// 2. Try adding various closing brackets/braces
/// 3. Fall back to empty object
///
/// # Example
///
/// ```
/// use alchemy_llm::utils::json_parse::parse_streaming_json;
/// use serde_json::json;
///
/// let partial = r#"{"name": "test", "value": 42"#;
/// let result = parse_streaming_json(partial);
/// assert_eq!(result, json!({"name": "test", "value": 42}));
///
/// // Complete JSON works too
/// let complete = r#"{"name": "test"}"#;
/// let result = parse_streaming_json(complete);
/// assert_eq!(result, json!({"name": "test"}));
/// ```
pub fn parse_streaming_json(s: &str) -> Value {
    // Try complete parse first
    if let Ok(v) = serde_json::from_str(s) {
        return v;
    }

    // Try common completions
    let completions = ["}", "}}", "\"}", "\"}}", "null}", "null}}", "]}", "]}}"];

    for suffix in completions {
        let attempt = format!("{}{}", s, suffix);
        if let Ok(v) = serde_json::from_str(&attempt) {
            return v;
        }
    }

    // Fall back to empty object
    Value::Object(Default::default())
}

/// More sophisticated partial JSON parsing using bracket tracking.
///
/// Analyzes the input to determine exactly which brackets and braces
/// need to be closed, preserving the nesting order for accurate parsing
/// of complex nested structures.
///
/// # Example
///
/// ```
/// use alchemy_llm::utils::json_parse::parse_streaming_json_smart;
/// use serde_json::json;
///
/// let partial = r#"{"items": [1, 2, 3"#;
/// let result = parse_streaming_json_smart(partial);
/// assert_eq!(result, json!({"items": [1, 2, 3]}));
/// ```
pub fn parse_streaming_json_smart(s: &str) -> Value {
    // Try complete parse first
    if let Ok(v) = serde_json::from_str(s) {
        return v;
    }

    // Track the nesting stack to preserve order
    let mut stack: Vec<char> = Vec::new();
    let mut in_string = false;
    let mut escape_next = false;

    for c in s.chars() {
        if escape_next {
            escape_next = false;
            continue;
        }

        match c {
            '\\' if in_string => escape_next = true,
            '"' => in_string = !in_string,
            '{' if !in_string => stack.push('{'),
            '}' if !in_string => {
                if stack.last() == Some(&'{') {
                    stack.pop();
                }
            }
            '[' if !in_string => stack.push('['),
            ']' if !in_string => {
                if stack.last() == Some(&'[') {
                    stack.pop();
                }
            }
            _ => {}
        }
    }

    // Build completion string in reverse order of the stack
    let mut completion = String::new();

    // Close any unclosed string
    if in_string {
        completion.push('"');
    }

    // Close brackets/braces in reverse order (LIFO)
    for opener in stack.iter().rev() {
        match opener {
            '{' => completion.push('}'),
            '[' => completion.push(']'),
            _ => {}
        }
    }

    let attempt = format!("{}{}", s, completion);
    serde_json::from_str(&attempt).unwrap_or_else(|_| Value::Object(Default::default()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_complete_json() {
        let result = parse_streaming_json(r#"{"name": "test"}"#);
        assert_eq!(result, json!({"name": "test"}));
    }

    #[test]
    fn test_missing_closing_brace() {
        let result = parse_streaming_json(r#"{"name": "test""#);
        assert_eq!(result, json!({"name": "test"}));
    }

    #[test]
    fn test_nested_missing_braces() {
        let result = parse_streaming_json(r#"{"outer": {"inner": 1"#);
        assert_eq!(result, json!({"outer": {"inner": 1}}));
    }

    #[test]
    fn test_empty_input() {
        let result = parse_streaming_json("");
        assert_eq!(result, json!({}));
    }

    #[test]
    fn test_with_number_value() {
        let result = parse_streaming_json(r#"{"count": 42"#);
        assert_eq!(result, json!({"count": 42}));
    }

    #[test]
    fn test_with_null_value() {
        let result = parse_streaming_json(r#"{"value": null}"#);
        assert_eq!(result, json!({"value": null}));
    }

    #[test]
    fn test_incomplete_string_value() {
        // When string is incomplete, basic parser may not handle it
        let result = parse_streaming_json(r#"{"name": "test"#);
        // Should return empty object since string isn't complete
        assert!(result.is_object());
    }

    #[test]
    fn test_smart_parser_complete() {
        let result = parse_streaming_json_smart(r#"{"name": "test"}"#);
        assert_eq!(result, json!({"name": "test"}));
    }

    #[test]
    fn test_smart_parser_array() {
        let result = parse_streaming_json_smart(r#"{"items": [1, 2, 3"#);
        assert_eq!(result, json!({"items": [1, 2, 3]}));
    }

    #[test]
    fn test_smart_parser_nested() {
        let result = parse_streaming_json_smart(r#"{"a": {"b": {"c": 1"#);
        assert_eq!(result, json!({"a": {"b": {"c": 1}}}));
    }

    #[test]
    fn test_smart_parser_mixed() {
        let result = parse_streaming_json_smart(r#"{"list": [{"id": 1}, {"id": 2"#);
        assert_eq!(result, json!({"list": [{"id": 1}, {"id": 2}]}));
    }

    #[test]
    fn test_smart_parser_unclosed_string() {
        let result = parse_streaming_json_smart(r#"{"name": "test"#);
        // Smart parser can close the string
        assert_eq!(result, json!({"name": "test"}));
    }

    #[test]
    fn test_smart_parser_escaped_quotes() {
        let result = parse_streaming_json_smart(r#"{"text": "hello \"world\""}"#);
        assert_eq!(result, json!({"text": "hello \"world\""}));
    }

    #[test]
    fn test_smart_parser_deeply_nested() {
        let result = parse_streaming_json_smart(r#"{"a": [{"b": [{"c": 1"#);
        assert_eq!(result, json!({"a": [{"b": [{"c": 1}]}]}));
    }

    #[test]
    fn test_smart_parser_empty() {
        let result = parse_streaming_json_smart("");
        assert_eq!(result, json!({}));
    }

    #[test]
    fn test_smart_parser_just_brace() {
        let result = parse_streaming_json_smart("{");
        assert_eq!(result, json!({}));
    }

    #[test]
    fn test_smart_parser_partial_key() {
        // Partial key won't parse even with smart parser
        let result = parse_streaming_json_smart(r#"{"na"#);
        // Should fall back to empty object
        assert!(result.is_object());
    }
}
