//! Tool call validation against JSON schemas.
//!
//! Validates tool call arguments against the tool's JSON schema definition,
//! returning useful error messages when validation fails.

use crate::error::{Error, Result};
use crate::types::{Tool, ToolCall};
use jsonschema::{Draft, JSONSchema};

/// Validate a tool call against available tools.
///
/// Finds the matching tool by name and validates arguments against its schema.
///
/// # Errors
///
/// Returns `Error::ToolNotFound` if no tool matches the tool call name.
/// Returns `Error::ToolValidationFailed` if arguments don't match the schema.
///
/// # Example
///
/// ```ignore
/// use alchemy::utils::validation::validate_tool_call;
///
/// let tools = vec![weather_tool];
/// let tool_call = ToolCall { name: "get_weather".into(), .. };
/// let validated = validate_tool_call(&tools, &tool_call)?;
/// ```
pub fn validate_tool_call(tools: &[Tool], tool_call: &ToolCall) -> Result<serde_json::Value> {
    let tool = tools
        .iter()
        .find(|t| t.name == tool_call.name)
        .ok_or_else(|| Error::ToolNotFound(tool_call.name.clone()))?;

    validate_tool_arguments(tool, tool_call)
}

/// Validate tool call arguments against the tool's JSON schema.
///
/// Returns the validated arguments on success.
///
/// # Errors
///
/// Returns `Error::ToolValidationFailed` with detailed error messages
/// listing each validation failure.
pub fn validate_tool_arguments(tool: &Tool, tool_call: &ToolCall) -> Result<serde_json::Value> {
    let schema = JSONSchema::options()
        .with_draft(Draft::Draft7)
        .compile(&tool.parameters)
        .map_err(|e| Error::ToolValidationFailed(format!("Schema compile error: {}", e)))?;

    let args = &tool_call.arguments;

    let validation_result = schema.validate(args);
    if let Err(errors) = validation_result {
        let error_messages: Vec<String> = errors
            .map(|err| {
                let path = err.instance_path.to_string();
                let path = if path.is_empty() {
                    "root".to_string()
                } else {
                    path
                };
                format!("  - {}: {}", path, err)
            })
            .collect();

        let error_msg = format!(
            "Validation failed for tool \"{}\":\n{}\n\nReceived arguments:\n{}",
            tool_call.name,
            error_messages.join("\n"),
            serde_json::to_string_pretty(args).unwrap_or_default()
        );

        return Err(Error::ToolValidationFailed(error_msg));
    }

    Ok(args.clone())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn make_tool(name: &str, schema: serde_json::Value) -> Tool {
        Tool {
            name: name.to_string(),
            description: "Test tool".to_string(),
            parameters: schema,
        }
    }

    fn make_tool_call(name: &str, arguments: serde_json::Value) -> ToolCall {
        ToolCall {
            id: "test-id".into(),
            name: name.to_string(),
            arguments,
            thought_signature: None,
        }
    }

    #[test]
    fn test_validate_valid_args() {
        let tool = make_tool(
            "get_weather",
            json!({
                "type": "object",
                "properties": {
                    "location": { "type": "string" }
                },
                "required": ["location"]
            }),
        );

        let tool_call = make_tool_call("get_weather", json!({ "location": "NYC" }));
        let result = validate_tool_arguments(&tool, &tool_call);
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), json!({ "location": "NYC" }));
    }

    #[test]
    fn test_validate_missing_required() {
        let tool = make_tool(
            "get_weather",
            json!({
                "type": "object",
                "properties": {
                    "location": { "type": "string" }
                },
                "required": ["location"]
            }),
        );

        let tool_call = make_tool_call("get_weather", json!({}));
        let result = validate_tool_arguments(&tool, &tool_call);
        assert!(result.is_err());

        let err = result.unwrap_err();
        assert!(matches!(err, Error::ToolValidationFailed(_)));
    }

    #[test]
    fn test_validate_wrong_type() {
        let tool = make_tool(
            "get_weather",
            json!({
                "type": "object",
                "properties": {
                    "location": { "type": "string" }
                },
                "required": ["location"]
            }),
        );

        let tool_call = make_tool_call("get_weather", json!({ "location": 123 }));
        let result = validate_tool_arguments(&tool, &tool_call);
        assert!(result.is_err());
    }

    #[test]
    fn test_validate_tool_call_not_found() {
        let tools = vec![make_tool(
            "get_weather",
            json!({
                "type": "object",
                "properties": {}
            }),
        )];

        let tool_call = make_tool_call("unknown_tool", json!({}));
        let result = validate_tool_call(&tools, &tool_call);
        assert!(result.is_err());
        assert!(matches!(result.unwrap_err(), Error::ToolNotFound(_)));
    }

    #[test]
    fn test_validate_tool_call_success() {
        let tools = vec![make_tool(
            "search",
            json!({
                "type": "object",
                "properties": {
                    "query": { "type": "string" }
                },
                "required": ["query"]
            }),
        )];

        let tool_call = make_tool_call("search", json!({ "query": "rust programming" }));
        let result = validate_tool_call(&tools, &tool_call);
        assert!(result.is_ok());
    }

    #[test]
    fn test_validate_nested_object() {
        let tool = make_tool(
            "create_user",
            json!({
                "type": "object",
                "properties": {
                    "name": { "type": "string" },
                    "address": {
                        "type": "object",
                        "properties": {
                            "city": { "type": "string" },
                            "zip": { "type": "string" }
                        },
                        "required": ["city"]
                    }
                },
                "required": ["name", "address"]
            }),
        );

        let tool_call = make_tool_call(
            "create_user",
            json!({
                "name": "Alice",
                "address": { "city": "Boston" }
            }),
        );
        let result = validate_tool_arguments(&tool, &tool_call);
        assert!(result.is_ok());

        // Missing nested required field
        let tool_call_bad = make_tool_call(
            "create_user",
            json!({
                "name": "Bob",
                "address": {}
            }),
        );
        let result_bad = validate_tool_arguments(&tool, &tool_call_bad);
        assert!(result_bad.is_err());
    }
}
