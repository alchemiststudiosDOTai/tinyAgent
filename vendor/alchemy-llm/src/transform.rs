//! Message transformation for cross-provider compatibility.
//!
//! Transforms conversation history when switching between models/providers,
//! handling:
//! - Thinking block conversion (signature preservation vs text conversion)
//! - Tool call ID normalization
//! - Orphaned tool call handling (synthetic error results)
//! - Error/aborted message filtering

use crate::types::{
    Api, AssistantMessage, Content, Message, Provider, StopReason, TextContent, ToolCall,
    ToolCallId, ToolResultContent, ToolResultMessage,
};
use std::collections::{HashMap, HashSet};
use std::time::{SystemTime, UNIX_EPOCH};

/// Information about the target model for transformation.
#[derive(Debug, Clone)]
pub struct TargetModel {
    pub api: Api,
    pub provider: Provider,
    pub model_id: String,
}

/// Transform messages for cross-provider compatibility.
///
/// Handles:
/// - Thinking block conversion (signature preservation vs text conversion)
/// - Tool call ID normalization
/// - Orphaned tool call handling (synthetic error results)
/// - Error/aborted message filtering
///
/// # Arguments
///
/// * `messages` - The conversation messages to transform
/// * `target` - The target model information
/// * `normalize_tool_call_id` - Optional function to normalize tool call IDs
///
/// # Example
///
/// ```ignore
/// use alchemy::transform::{transform_messages, TargetModel};
/// use alchemy::types::{Api, Provider, KnownProvider};
///
/// let target = TargetModel {
///     api: Api::OpenAICompletions,
///     provider: Provider::Known(KnownProvider::OpenAI),
///     model_id: "gpt-4o".to_string(),
/// };
///
/// let transformed = transform_messages(&messages, &target, None);
/// ```
pub fn transform_messages<F>(
    messages: &[Message],
    target: &TargetModel,
    normalize_tool_call_id: Option<F>,
) -> Vec<Message>
where
    F: Fn(&str, &TargetModel, &AssistantMessage) -> String,
{
    let mut tool_call_id_map: HashMap<ToolCallId, ToolCallId> = HashMap::new();

    // First pass: transform messages
    let transformed: Vec<Message> = messages
        .iter()
        .filter_map(|msg| {
            transform_message(
                msg,
                target,
                normalize_tool_call_id.as_ref(),
                &mut tool_call_id_map,
            )
        })
        .collect();

    // Second pass: insert synthetic tool results for orphaned calls
    insert_synthetic_tool_results(transformed)
}

/// Transform messages without tool call ID normalization.
///
/// Convenience wrapper for `transform_messages` when no ID normalization is needed.
pub fn transform_messages_simple(messages: &[Message], target: &TargetModel) -> Vec<Message> {
    transform_messages::<fn(&str, &TargetModel, &AssistantMessage) -> String>(
        messages, target, None,
    )
}

fn transform_message<F>(
    msg: &Message,
    target: &TargetModel,
    normalize_fn: Option<&F>,
    id_map: &mut HashMap<ToolCallId, ToolCallId>,
) -> Option<Message>
where
    F: Fn(&str, &TargetModel, &AssistantMessage) -> String,
{
    match msg {
        Message::User(user) => Some(Message::User(user.clone())),

        Message::ToolResult(result) => {
            // Apply ID mapping if exists
            let tool_call_id = id_map
                .get(&result.tool_call_id)
                .cloned()
                .unwrap_or_else(|| result.tool_call_id.clone());

            Some(Message::ToolResult(ToolResultMessage {
                tool_call_id,
                tool_name: result.tool_name.clone(),
                content: result.content.clone(),
                details: result.details.clone(),
                is_error: result.is_error,
                timestamp: result.timestamp,
            }))
        }

        Message::Assistant(assistant) => {
            // Skip errored/aborted messages
            if matches!(
                assistant.stop_reason,
                StopReason::Error | StopReason::Aborted
            ) {
                return None;
            }

            let is_same_model = is_same_model_provider(assistant, target);

            let content = assistant
                .content
                .iter()
                .filter_map(|block| {
                    transform_content_block(
                        block,
                        is_same_model,
                        target,
                        assistant,
                        normalize_fn,
                        id_map,
                    )
                })
                .collect();

            Some(Message::Assistant(AssistantMessage {
                content,
                api: assistant.api,
                provider: assistant.provider.clone(),
                model: assistant.model.clone(),
                usage: assistant.usage.clone(),
                stop_reason: assistant.stop_reason,
                error_message: assistant.error_message.clone(),
                timestamp: assistant.timestamp,
            }))
        }
    }
}

fn is_same_model_provider(msg: &AssistantMessage, target: &TargetModel) -> bool {
    msg.provider == target.provider && msg.api == target.api && msg.model == target.model_id
}

fn transform_content_block<F>(
    block: &Content,
    is_same_model: bool,
    target: &TargetModel,
    assistant: &AssistantMessage,
    normalize_fn: Option<&F>,
    id_map: &mut HashMap<ToolCallId, ToolCallId>,
) -> Option<Content>
where
    F: Fn(&str, &TargetModel, &AssistantMessage) -> String,
{
    match block {
        Content::Thinking { inner } => {
            // Same model with signature: keep for replay
            if is_same_model && inner.thinking_signature.is_some() {
                return Some(block.clone());
            }

            // Empty thinking: filter out
            if inner.thinking.trim().is_empty() {
                return None;
            }

            // Same model without signature: keep as-is
            if is_same_model {
                return Some(block.clone());
            }

            // Different model: convert to plain text (no <thinking> tags)
            Some(Content::text(&inner.thinking))
        }

        Content::Text { inner } => {
            if is_same_model {
                Some(block.clone())
            } else {
                // Strip signature if present
                Some(Content::Text {
                    inner: TextContent {
                        text: inner.text.clone(),
                        text_signature: None,
                    },
                })
            }
        }

        Content::ToolCall { inner } => {
            let mut new_call = inner.clone();

            // Strip thought signature for different model
            if !is_same_model {
                new_call.thought_signature = None;
            }

            // Normalize ID for different model
            if !is_same_model {
                if let Some(normalize) = normalize_fn {
                    let normalized_id =
                        ToolCallId::from(normalize(inner.id.as_str(), target, assistant));
                    if normalized_id != inner.id {
                        id_map.insert(inner.id.clone(), normalized_id.clone());
                        new_call.id = normalized_id;
                    }
                }
            }

            Some(Content::ToolCall { inner: new_call })
        }

        Content::Image { .. } => Some(block.clone()),
    }
}

fn insert_synthetic_tool_results(messages: Vec<Message>) -> Vec<Message> {
    let mut result: Vec<Message> = Vec::new();
    let mut pending_tool_calls: Vec<ToolCall> = Vec::new();
    let mut existing_result_ids: HashSet<ToolCallId> = HashSet::new();

    for msg in messages {
        match &msg {
            Message::Assistant(assistant) => {
                // Insert synthetic results for previous orphaned calls
                insert_orphaned_results(&mut result, &pending_tool_calls, &existing_result_ids);
                pending_tool_calls.clear();
                existing_result_ids.clear();

                // Track tool calls from this message
                for content in &assistant.content {
                    if let Content::ToolCall { inner } = content {
                        pending_tool_calls.push(inner.clone());
                    }
                }

                result.push(msg);
            }

            Message::ToolResult(tool_result) => {
                existing_result_ids.insert(tool_result.tool_call_id.clone());
                result.push(msg);
            }

            Message::User(_) => {
                // User message interrupts tool flow
                insert_orphaned_results(&mut result, &pending_tool_calls, &existing_result_ids);
                pending_tool_calls.clear();
                existing_result_ids.clear();

                result.push(msg);
            }
        }
    }

    // Handle any remaining orphaned calls at the end
    insert_orphaned_results(&mut result, &pending_tool_calls, &existing_result_ids);

    result
}

fn insert_orphaned_results(
    result: &mut Vec<Message>,
    pending: &[ToolCall],
    existing: &HashSet<ToolCallId>,
) {
    for tc in pending {
        if !existing.contains(&tc.id) {
            result.push(Message::ToolResult(ToolResultMessage {
                tool_call_id: tc.id.clone(),
                tool_name: tc.name.clone(),
                content: vec![ToolResultContent::Text(TextContent {
                    text: "No result provided".to_string(),
                    text_signature: None,
                })],
                details: None,
                is_error: true,
                timestamp: current_timestamp(),
            }));
        }
    }
}

fn current_timestamp() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as i64)
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{KnownProvider, ThinkingContent, Usage, UserContent, UserMessage};

    fn make_target(api: Api, provider: KnownProvider, model_id: &str) -> TargetModel {
        TargetModel {
            api,
            provider: Provider::Known(provider),
            model_id: model_id.to_string(),
        }
    }

    fn make_assistant(
        api: Api,
        provider: KnownProvider,
        model: &str,
        content: Vec<Content>,
    ) -> AssistantMessage {
        AssistantMessage {
            content,
            api,
            provider: Provider::Known(provider),
            model: model.to_string(),
            usage: Usage::default(),
            stop_reason: StopReason::Stop,
            error_message: None,
            timestamp: 0,
        }
    }

    fn make_user(text: &str) -> UserMessage {
        UserMessage {
            content: UserContent::Text(text.to_string()),
            timestamp: 0,
        }
    }

    fn transform_single_assistant_to_openai(content: Content) -> Vec<Message> {
        let assistant = make_assistant(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
            vec![content],
        );
        let messages = vec![Message::Assistant(assistant)];
        let target = make_target(Api::OpenAICompletions, KnownProvider::OpenAI, "gpt-4o");

        transform_messages_simple(&messages, &target)
    }

    fn assert_single_assistant_message(messages: &[Message]) -> &AssistantMessage {
        assert_eq!(messages.len(), 1);
        match &messages[0] {
            Message::Assistant(assistant) => assistant,
            _ => panic!("Expected assistant message"),
        }
    }

    #[test]
    fn test_user_message_passthrough() {
        let messages = vec![Message::User(make_user("Hello"))];

        let target = make_target(Api::OpenAICompletions, KnownProvider::OpenAI, "gpt-4o");
        let result = transform_messages_simple(&messages, &target);

        assert_eq!(result.len(), 1);
        assert!(matches!(result[0], Message::User(_)));
    }

    #[test]
    fn test_filter_error_messages() {
        let mut assistant = make_assistant(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
            vec![Content::text("Some text")],
        );
        assistant.stop_reason = StopReason::Error;
        assistant.error_message = Some("API error".to_string());

        let messages = vec![
            Message::User(make_user("Hello")),
            Message::Assistant(assistant),
        ];

        let target = make_target(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
        );
        let result = transform_messages_simple(&messages, &target);

        // Error message should be filtered out
        assert_eq!(result.len(), 1);
        assert!(matches!(result[0], Message::User(_)));
    }

    #[test]
    fn test_filter_aborted_messages() {
        let mut assistant = make_assistant(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
            vec![Content::text("Partial")],
        );
        assistant.stop_reason = StopReason::Aborted;

        let messages = vec![Message::Assistant(assistant)];

        let target = make_target(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
        );
        let result = transform_messages_simple(&messages, &target);

        assert!(result.is_empty());
    }

    #[test]
    fn test_thinking_same_model_with_signature() {
        let thinking = ThinkingContent {
            thinking: "Let me think...".to_string(),
            thinking_signature: Some("sig123".to_string()),
        };
        let assistant = make_assistant(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
            vec![Content::Thinking { inner: thinking }],
        );

        let messages = vec![Message::Assistant(assistant)];

        let target = make_target(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
        );
        let result = transform_messages_simple(&messages, &target);

        // Same model with signature: keep thinking
        assert_eq!(result.len(), 1);
        if let Message::Assistant(a) = &result[0] {
            assert!(matches!(a.content[0], Content::Thinking { .. }));
        } else {
            panic!("Expected assistant message");
        }
    }

    #[test]
    fn test_thinking_different_model_to_text() {
        let thinking = ThinkingContent {
            thinking: "Let me think about this carefully.".to_string(),
            thinking_signature: Some("sig123".to_string()),
        };
        let result = transform_single_assistant_to_openai(Content::Thinking { inner: thinking });

        // Thinking should be converted to text
        let assistant = assert_single_assistant_message(&result);
        assert_eq!(assistant.content.len(), 1);
        if let Content::Text { inner } = &assistant.content[0] {
            assert_eq!(inner.text, "Let me think about this carefully.");
            assert!(inner.text_signature.is_none());
        } else {
            panic!("Expected text content");
        }
    }

    #[test]
    fn test_empty_thinking_filtered() {
        let thinking = ThinkingContent {
            thinking: "   ".to_string(),
            thinking_signature: None,
        };
        let assistant = make_assistant(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
            vec![
                Content::Thinking { inner: thinking },
                Content::text("Hello!"),
            ],
        );

        let messages = vec![Message::Assistant(assistant)];

        let target = make_target(Api::OpenAICompletions, KnownProvider::OpenAI, "gpt-4o");
        let result = transform_messages_simple(&messages, &target);

        // Empty thinking should be filtered
        if let Message::Assistant(a) = &result[0] {
            assert_eq!(a.content.len(), 1);
            assert!(matches!(a.content[0], Content::Text { .. }));
        } else {
            panic!("Expected assistant message");
        }
    }

    #[test]
    fn test_text_signature_stripped_for_different_model() {
        let text = TextContent {
            text: "Hello".to_string(),
            text_signature: Some("sig456".to_string()),
        };
        let assistant = make_assistant(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
            vec![Content::Text { inner: text }],
        );

        let messages = vec![Message::Assistant(assistant)];

        let target = make_target(Api::OpenAICompletions, KnownProvider::OpenAI, "gpt-4o");
        let result = transform_messages_simple(&messages, &target);

        if let Message::Assistant(a) = &result[0] {
            if let Content::Text { inner } = &a.content[0] {
                assert_eq!(inner.text, "Hello");
                assert!(inner.text_signature.is_none());
            } else {
                panic!("Expected text content");
            }
        }
    }

    #[test]
    fn test_tool_call_id_normalization() {
        use serde_json::json;

        let tool_call = ToolCall {
            id: "original-id-123".into(),
            name: "search".to_string(),
            arguments: json!({"query": "test"}),
            thought_signature: Some("sig".to_string()),
        };
        let assistant = make_assistant(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
            vec![Content::ToolCall { inner: tool_call }],
        );

        let tool_result = ToolResultMessage {
            tool_call_id: "original-id-123".into(),
            tool_name: "search".to_string(),
            content: vec![ToolResultContent::Text(TextContent {
                text: "results".to_string(),
                text_signature: None,
            })],
            details: None,
            is_error: false,
            timestamp: 0,
        };

        let messages = vec![
            Message::Assistant(assistant),
            Message::ToolResult(tool_result),
        ];

        let target = make_target(Api::OpenAICompletions, KnownProvider::OpenAI, "gpt-4o");

        // Normalize IDs to OpenAI format
        let normalize = |id: &str, _target: &TargetModel, _msg: &AssistantMessage| -> String {
            format!("call_{}", id.replace('-', "_"))
        };

        let result = transform_messages(&messages, &target, Some(normalize));

        assert_eq!(result.len(), 2);

        // Check tool call ID was normalized
        if let Message::Assistant(a) = &result[0] {
            if let Content::ToolCall { inner } = &a.content[0] {
                assert_eq!(inner.id.as_str(), "call_original_id_123");
                assert!(inner.thought_signature.is_none()); // Stripped for different model
            }
        }

        // Check tool result ID was also normalized
        if let Message::ToolResult(r) = &result[1] {
            assert_eq!(r.tool_call_id.as_str(), "call_original_id_123");
        }
    }

    #[test]
    fn test_orphaned_tool_call_synthetic_result() {
        use serde_json::json;

        let tool_call = ToolCall {
            id: "call-123".into(),
            name: "search".to_string(),
            arguments: json!({"query": "test"}),
            thought_signature: None,
        };
        let assistant = make_assistant(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
            vec![Content::ToolCall { inner: tool_call }],
        );

        // User message interrupts without tool result
        let messages = vec![
            Message::Assistant(assistant),
            Message::User(make_user("Never mind")),
        ];

        let target = make_target(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
        );
        let result = transform_messages_simple(&messages, &target);

        // Should have synthetic tool result inserted
        assert_eq!(result.len(), 3);
        assert!(matches!(result[0], Message::Assistant(_)));

        if let Message::ToolResult(r) = &result[1] {
            assert_eq!(r.tool_call_id.as_str(), "call-123");
            assert_eq!(r.tool_name, "search");
            assert!(r.is_error);
        } else {
            panic!("Expected tool result at index 1");
        }

        assert!(matches!(result[2], Message::User(_)));
    }

    #[test]
    fn test_multiple_tool_calls_partial_results() {
        use serde_json::json;

        let assistant = make_assistant(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
            vec![
                Content::ToolCall {
                    inner: ToolCall {
                        id: "call-1".into(),
                        name: "tool_a".to_string(),
                        arguments: json!({}),
                        thought_signature: None,
                    },
                },
                Content::ToolCall {
                    inner: ToolCall {
                        id: "call-2".into(),
                        name: "tool_b".to_string(),
                        arguments: json!({}),
                        thought_signature: None,
                    },
                },
            ],
        );

        // Only one result provided
        let result1 = ToolResultMessage {
            tool_call_id: "call-1".into(),
            tool_name: "tool_a".to_string(),
            content: vec![ToolResultContent::Text(TextContent {
                text: "result a".to_string(),
                text_signature: None,
            })],
            details: None,
            is_error: false,
            timestamp: 0,
        };

        let messages = vec![
            Message::Assistant(assistant),
            Message::ToolResult(result1),
            Message::User(make_user("Continue")),
        ];

        let target = make_target(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
        );
        let result = transform_messages_simple(&messages, &target);

        // Should have: assistant, result1, synthetic result for call-2, user
        assert_eq!(result.len(), 4);

        // Find the synthetic result
        let synthetic = result.iter().find(|m| {
            if let Message::ToolResult(r) = m {
                r.tool_call_id.as_str() == "call-2"
            } else {
                false
            }
        });
        assert!(synthetic.is_some());

        if let Some(Message::ToolResult(r)) = synthetic {
            assert!(r.is_error);
            assert_eq!(r.tool_name, "tool_b");
        }
    }

    #[test]
    fn test_no_synthetic_when_all_results_present() {
        use serde_json::json;

        let assistant = make_assistant(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
            vec![Content::ToolCall {
                inner: ToolCall {
                    id: "call-1".into(),
                    name: "search".to_string(),
                    arguments: json!({}),
                    thought_signature: None,
                },
            }],
        );

        let result1 = ToolResultMessage {
            tool_call_id: "call-1".into(),
            tool_name: "search".to_string(),
            content: vec![ToolResultContent::Text(TextContent {
                text: "found it".to_string(),
                text_signature: None,
            })],
            details: None,
            is_error: false,
            timestamp: 0,
        };

        let messages = vec![Message::Assistant(assistant), Message::ToolResult(result1)];

        let target = make_target(
            Api::AnthropicMessages,
            KnownProvider::Anthropic,
            "claude-sonnet-4-20250514",
        );
        let result = transform_messages_simple(&messages, &target);

        // No synthetic results needed
        assert_eq!(result.len(), 2);
    }

    #[test]
    fn test_image_content_passthrough() {
        use crate::types::ImageContent;

        let image = ImageContent {
            data: vec![1, 2, 3],
            mime_type: "image/png".to_string(),
        };
        let result = transform_single_assistant_to_openai(Content::Image { inner: image });

        let assistant = assert_single_assistant_message(&result);
        assert!(matches!(assistant.content[0], Content::Image { .. }));
    }
}
