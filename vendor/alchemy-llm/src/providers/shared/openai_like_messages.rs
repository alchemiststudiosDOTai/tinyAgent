use serde_json::json;

use crate::types::{
    ApiType, Content, Context, InputType, Message, Model, Tool, ToolResultContent, UserContent,
    UserContentBlock, UserMessage,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum SystemPromptRole {
    System,
    Developer,
}

impl SystemPromptRole {
    fn as_str(&self) -> &'static str {
        match self {
            Self::System => "system",
            Self::Developer => "developer",
        }
    }
}

const OPEN_THINK_TAG: &str = "<think>";
const CLOSE_THINK_TAG: &str = "</think>";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub(crate) enum AssistantThinkingMode {
    Omit,
    PlainText,
    ThinkTags,
}

#[derive(Debug, Clone, Copy)]
pub(crate) struct OpenAiLikeMessageOptions {
    pub system_role: SystemPromptRole,
    pub requires_tool_result_name: bool,
    pub assistant_thinking_mode: AssistantThinkingMode,
    pub assistant_content_as_string: bool,
    pub emit_reasoning_content_field: bool,
    pub tool_call_arguments_as_object: bool,
}

impl OpenAiLikeMessageOptions {
    pub(crate) fn openai_like(
        system_role: SystemPromptRole,
        requires_tool_result_name: bool,
        assistant_thinking_mode: AssistantThinkingMode,
    ) -> Self {
        Self {
            system_role,
            requires_tool_result_name,
            assistant_thinking_mode,
            ..Self::default()
        }
    }
}

impl Default for OpenAiLikeMessageOptions {
    fn default() -> Self {
        Self {
            system_role: SystemPromptRole::System,
            requires_tool_result_name: false,
            assistant_thinking_mode: AssistantThinkingMode::Omit,
            assistant_content_as_string: false,
            emit_reasoning_content_field: false,
            tool_call_arguments_as_object: false,
        }
    }
}

pub(crate) fn convert_messages<TApi: ApiType>(
    model: &Model<TApi>,
    context: &Context,
    options: &OpenAiLikeMessageOptions,
) -> serde_json::Value {
    let mut messages = Vec::new();

    push_system_prompt(&mut messages, context, options.system_role);

    for message in &context.messages {
        match message {
            Message::User(user) => messages.push(convert_user_message(model, user)),
            Message::Assistant(assistant) => {
                if let Some(converted) = convert_assistant_message(assistant, options) {
                    messages.push(converted);
                }
            }
            Message::ToolResult(result) => {
                messages.push(convert_tool_result(
                    result,
                    options.requires_tool_result_name,
                ));
            }
        }
    }

    json!(messages)
}

fn push_system_prompt(
    messages: &mut Vec<serde_json::Value>,
    context: &Context,
    role: SystemPromptRole,
) {
    let Some(system_prompt) = &context.system_prompt else {
        return;
    };

    messages.push(json!({
        "role": role.as_str(),
        "content": system_prompt,
    }));
}

fn convert_user_message<TApi: ApiType>(
    model: &Model<TApi>,
    user: &UserMessage,
) -> serde_json::Value {
    let content = user_content_to_json(model, &user.content);

    json!({
        "role": "user",
        "content": content,
    })
}

fn user_content_to_json<TApi: ApiType>(
    model: &Model<TApi>,
    content: &UserContent,
) -> serde_json::Value {
    match content {
        UserContent::Text(text) => json!(text),
        UserContent::Multi(blocks) => {
            let parts: Vec<serde_json::Value> = blocks
                .iter()
                .filter_map(|block| match block {
                    UserContentBlock::Text(text) => Some(json!({
                        "type": "text",
                        "text": text.text,
                    })),
                    UserContentBlock::Image(image) if model.input.contains(&InputType::Image) => {
                        Some(json!({
                            "type": "image_url",
                            "image_url": {
                                "url": format!(
                                    "data:{};base64,{}",
                                    image.mime_type,
                                    image.to_base64(),
                                )
                            }
                        }))
                    }
                    UserContentBlock::Image(_) => None,
                })
                .collect();

            json!(parts)
        }
    }
}

const ASSISTANT_CONTENT_PART_SEPARATOR: &str = "\n";

fn convert_assistant_message(
    assistant: &crate::types::AssistantMessage,
    options: &OpenAiLikeMessageOptions,
) -> Option<serde_json::Value> {
    let mut message = json!({
        "role": "assistant",
    });

    if let Some(content) = assistant_content_value(assistant, options) {
        message["content"] = content;
    }

    if options.emit_reasoning_content_field {
        if let Some(reasoning_content) = assistant_reasoning_content(assistant) {
            message["reasoning_content"] = json!(reasoning_content);
        }
    }

    let tool_calls = assistant_tool_calls(assistant, options.tool_call_arguments_as_object);
    if !tool_calls.is_empty() {
        message["tool_calls"] = json!(tool_calls);
    }

    let has_content = message.get("content").is_some();
    let has_reasoning_content = message.get("reasoning_content").is_some();
    let has_tool_calls = message.get("tool_calls").is_some();

    if !(has_content || has_reasoning_content || has_tool_calls) {
        return None;
    }

    Some(message)
}

fn assistant_content_value(
    assistant: &crate::types::AssistantMessage,
    options: &OpenAiLikeMessageOptions,
) -> Option<serde_json::Value> {
    let text_parts = assistant_text_parts(assistant, options.assistant_thinking_mode);

    if text_parts.is_empty() {
        return None;
    }

    if options.assistant_content_as_string {
        return Some(json!(text_parts.join(ASSISTANT_CONTENT_PART_SEPARATOR)));
    }

    Some(json!(text_parts
        .iter()
        .map(|text| json!({ "type": "text", "text": text }))
        .collect::<Vec<_>>()))
}

fn assistant_text_parts(
    assistant: &crate::types::AssistantMessage,
    thinking_mode: AssistantThinkingMode,
) -> Vec<String> {
    assistant
        .content
        .iter()
        .filter_map(|content| match content {
            Content::Text { inner } if !inner.text.is_empty() => Some(inner.text.clone()),
            Content::Thinking { inner } if !inner.thinking.is_empty() => {
                map_thinking_content(&inner.thinking, thinking_mode)
            }
            _ => None,
        })
        .collect()
}

fn assistant_reasoning_content(assistant: &crate::types::AssistantMessage) -> Option<String> {
    let reasoning_parts: Vec<String> = assistant
        .content
        .iter()
        .filter_map(|content| match content {
            Content::Thinking { inner } if !inner.thinking.is_empty() => {
                Some(inner.thinking.clone())
            }
            _ => None,
        })
        .collect();

    if reasoning_parts.is_empty() {
        return None;
    }

    Some(reasoning_parts.join(ASSISTANT_CONTENT_PART_SEPARATOR))
}

fn map_thinking_content(thinking: &str, mode: AssistantThinkingMode) -> Option<String> {
    match mode {
        AssistantThinkingMode::Omit => None,
        AssistantThinkingMode::PlainText => Some(thinking.to_string()),
        AssistantThinkingMode::ThinkTags => {
            Some(format!("{OPEN_THINK_TAG}{thinking}{CLOSE_THINK_TAG}"))
        }
    }
}

fn assistant_tool_calls(
    assistant: &crate::types::AssistantMessage,
    tool_call_arguments_as_object: bool,
) -> Vec<serde_json::Value> {
    assistant
        .content
        .iter()
        .filter_map(|content| match content {
            Content::ToolCall { inner } => {
                let arguments = if tool_call_arguments_as_object {
                    inner.arguments.clone()
                } else {
                    json!(inner.arguments.to_string())
                };

                Some(json!({
                    "id": inner.id,
                    "type": "function",
                    "function": {
                        "name": inner.name,
                        "arguments": arguments,
                    }
                }))
            }
            _ => None,
        })
        .collect()
}

fn convert_tool_result(
    result: &crate::types::ToolResultMessage,
    requires_tool_result_name: bool,
) -> serde_json::Value {
    let content = result
        .content
        .iter()
        .filter_map(|item| match item {
            ToolResultContent::Text(text) => Some(text.text.clone()),
            ToolResultContent::Image(_) => None,
        })
        .collect::<Vec<_>>()
        .join("\n");

    let mut message = json!({
        "role": "tool",
        "tool_call_id": result.tool_call_id,
        "content": content,
    });

    if requires_tool_result_name {
        message["name"] = json!(result.tool_name);
    }

    message
}

pub(crate) fn convert_tools(tools: &[Tool]) -> serde_json::Value {
    let converted: Vec<serde_json::Value> = tools
        .iter()
        .map(|tool| {
            json!({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "strict": false,
                }
            })
        })
        .collect();

    json!(converted)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{
        Api, AssistantMessage, Cost, KnownProvider, ModelCost, OpenAICompletions, Provider,
        StopReason, Usage,
    };

    fn make_model(input: Vec<InputType>) -> Model<OpenAICompletions> {
        Model {
            id: "test-model".to_string(),
            name: "Test model".to_string(),
            api: OpenAICompletions,
            provider: Provider::Known(KnownProvider::OpenAI),
            base_url: "https://example.com/v1/chat/completions".to_string(),
            reasoning: false,
            input,
            cost: ModelCost {
                input: 0.0,
                output: 0.0,
                cache_read: 0.0,
                cache_write: 0.0,
            },
            context_window: 128_000,
            max_tokens: 4_096,
            headers: None,
            compat: None,
        }
    }

    fn make_assistant_message(content: Vec<Content>) -> AssistantMessage {
        AssistantMessage {
            content,
            api: Api::OpenAICompletions,
            provider: Provider::Known(KnownProvider::OpenAI),
            model: "test-model".to_string(),
            usage: Usage {
                input: 0,
                output: 0,
                cache_read: 0,
                cache_write: 0,
                total_tokens: 0,
                cost: Cost::default(),
            },
            stop_reason: StopReason::Stop,
            error_message: None,
            timestamp: 0,
        }
    }

    fn convert_assistant_with_thinking(mode: AssistantThinkingMode) -> serde_json::Value {
        let model = make_model(vec![InputType::Text]);
        let context = Context {
            system_prompt: None,
            messages: vec![Message::Assistant(make_assistant_message(vec![
                Content::thinking("internal"),
                Content::text("answer"),
            ]))],
            tools: None,
        };

        convert_messages(
            &model,
            &context,
            &OpenAiLikeMessageOptions::openai_like(SystemPromptRole::System, false, mode),
        )
    }

    #[test]
    fn convert_messages_uses_system_role_option() {
        let model = make_model(vec![InputType::Text]);
        let context = Context {
            system_prompt: Some("sys".to_string()),
            messages: vec![],
            tools: None,
        };

        let params = convert_messages(
            &model,
            &context,
            &OpenAiLikeMessageOptions::openai_like(
                SystemPromptRole::Developer,
                false,
                AssistantThinkingMode::Omit,
            ),
        );

        assert_eq!(params[0]["role"], "developer");
        assert_eq!(params[0]["content"], "sys");
    }

    #[test]
    fn convert_messages_drops_images_for_text_only_model() {
        let model = make_model(vec![InputType::Text]);
        let context = Context {
            system_prompt: None,
            messages: vec![Message::User(UserMessage {
                content: UserContent::Multi(vec![UserContentBlock::Image(
                    crate::types::ImageContent {
                        data: vec![1, 2, 3],
                        mime_type: "image/png".to_string(),
                    },
                )]),
                timestamp: 0,
            })],
            tools: None,
        };

        let params = convert_messages(
            &model,
            &context,
            &OpenAiLikeMessageOptions::openai_like(
                SystemPromptRole::System,
                false,
                AssistantThinkingMode::Omit,
            ),
        );

        assert_eq!(params[0]["content"], serde_json::json!([]));
    }

    #[test]
    fn convert_messages_includes_assistant_text_content() {
        let model = make_model(vec![InputType::Text]);
        let context = Context {
            system_prompt: None,
            messages: vec![Message::Assistant(make_assistant_message(vec![
                Content::text("hello"),
            ]))],
            tools: None,
        };

        let params = convert_messages(
            &model,
            &context,
            &OpenAiLikeMessageOptions::openai_like(
                SystemPromptRole::System,
                false,
                AssistantThinkingMode::Omit,
            ),
        );

        assert_eq!(params[0]["role"], "assistant");
        assert_eq!(params[0]["content"][0]["text"], "hello");
    }

    #[test]
    fn convert_messages_omits_assistant_thinking_in_omit_mode() {
        let model = make_model(vec![InputType::Text]);
        let context = Context {
            system_prompt: None,
            messages: vec![Message::Assistant(make_assistant_message(vec![
                Content::thinking("internal"),
            ]))],
            tools: None,
        };

        let params = convert_messages(
            &model,
            &context,
            &OpenAiLikeMessageOptions::openai_like(
                SystemPromptRole::System,
                false,
                AssistantThinkingMode::Omit,
            ),
        );

        assert_eq!(params, serde_json::json!([]));
    }

    #[test]
    fn convert_messages_includes_assistant_thinking_as_plain_text() {
        let params = convert_assistant_with_thinking(AssistantThinkingMode::PlainText);

        assert_eq!(params[0]["content"][0]["text"], "internal");
        assert_eq!(params[0]["content"][1]["text"], "answer");
    }

    #[test]
    fn convert_messages_wraps_assistant_thinking_in_think_tags() {
        let params = convert_assistant_with_thinking(AssistantThinkingMode::ThinkTags);

        assert_eq!(params[0]["content"][0]["text"], "<think>internal</think>");
        assert_eq!(params[0]["content"][1]["text"], "answer");
    }

    #[test]
    fn convert_messages_zai_mode_matches_canonical_assistant_replay_shape() {
        let model = make_model(vec![InputType::Text]);
        let context = Context {
            system_prompt: None,
            messages: vec![Message::Assistant(make_assistant_message(vec![
                Content::thinking("first reason"),
                Content::text("final answer"),
                Content::tool_call("call_1", "get_weather", json!({"city": "Tokyo"})),
            ]))],
            tools: None,
        };
        let options = OpenAiLikeMessageOptions {
            assistant_content_as_string: true,
            emit_reasoning_content_field: true,
            tool_call_arguments_as_object: false,
            ..OpenAiLikeMessageOptions::openai_like(
                SystemPromptRole::System,
                false,
                AssistantThinkingMode::Omit,
            )
        };

        let params = convert_messages(&model, &context, &options);

        assert_eq!(
            params[0],
            json!({
                "role": "assistant",
                "reasoning_content": "first reason",
                "content": "final answer",
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": "{\"city\":\"Tokyo\"}"
                    }
                }]
            })
        );
    }

    #[test]
    fn convert_messages_keeps_assistant_with_reasoning_field_even_without_text_content() {
        let model = make_model(vec![InputType::Text]);
        let context = Context {
            system_prompt: None,
            messages: vec![Message::Assistant(make_assistant_message(vec![
                Content::thinking("hidden chain"),
            ]))],
            tools: None,
        };
        let options = OpenAiLikeMessageOptions {
            emit_reasoning_content_field: true,
            ..OpenAiLikeMessageOptions::openai_like(
                SystemPromptRole::System,
                false,
                AssistantThinkingMode::Omit,
            )
        };

        let params = convert_messages(&model, &context, &options);

        assert_eq!(params[0]["role"], "assistant");
        assert_eq!(params[0]["reasoning_content"], "hidden chain");
        assert!(params[0].get("content").is_none());
    }

    #[test]
    fn convert_messages_can_emit_tool_call_arguments_as_json_object() {
        let model = make_model(vec![InputType::Text]);
        let context = Context {
            system_prompt: None,
            messages: vec![Message::Assistant(make_assistant_message(vec![
                Content::tool_call("call_2", "calculator", json!({"a": 1, "b": 2})),
            ]))],
            tools: None,
        };
        let options = OpenAiLikeMessageOptions {
            tool_call_arguments_as_object: true,
            ..OpenAiLikeMessageOptions::default()
        };

        let params = convert_messages(&model, &context, &options);

        assert_eq!(
            params[0]["tool_calls"][0]["function"]["arguments"],
            json!({"a": 1, "b": 2})
        );
    }
}
