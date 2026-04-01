use crate::types::{
    Api, AssistantMessage, Provider, StopReason, ZaiChatCompletionsOptions, ZaiResponseFormat,
    ZaiResponseFormatType, ZaiThinking, ZaiThinkingType,
};
use serde::de::DeserializeOwned;
use serde_json::json;

pub(crate) struct ExpectedFinalMessageShape<'a> {
    pub api: Api,
    pub provider: Provider,
    pub model: &'a str,
    pub stop_reason: StopReason,
    pub total_tokens: u32,
}

pub(crate) fn populated_zai_chat_completions_options() -> ZaiChatCompletionsOptions {
    ZaiChatCompletionsOptions {
        do_sample: Some(true),
        top_p: Some(0.75),
        max_tokens: Some(4096),
        stop: Some(["stop-here".to_string()]),
        tool_stream: Some(true),
        request_id: Some("request-1".to_string()),
        user_id: Some("user-2".to_string()),
        response_format: Some(ZaiResponseFormat {
            kind: ZaiResponseFormatType::JsonSchema,
            json_schema: Some(json!({"type": "object"})),
        }),
        thinking: Some(ZaiThinking {
            kind: ZaiThinkingType::Disabled,
            clear_thinking: Some(true),
        }),
    }
}

pub(crate) fn populated_zai_chat_completions_options_json() -> serde_json::Value {
    json!({
        "do_sample": true,
        "top_p": 0.75,
        "max_tokens": 4096,
        "stop": ["stop-here"],
        "tool_stream": true,
        "request_id": "request-1",
        "user_id": "user-2",
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "type": "object"
            }
        },
        "thinking": {
            "type": "disabled",
            "clear_thinking": true
        }
    })
}

pub(crate) fn build_final_message_shape_chunks<TChunk>(
    reasoning_delta: serde_json::Value,
) -> Vec<TChunk>
where
    TChunk: DeserializeOwned,
{
    vec![
        serde_json::from_value(json!({
            "choices": [{
                "delta": reasoning_delta
            }]
        }))
        .expect("valid reasoning chunk"),
        serde_json::from_value(json!({
            "choices": [{
                "delta": {"content": "answer"},
                "finish_reason": "stop"
            }]
        }))
        .expect("valid answer chunk"),
        serde_json::from_value(json!({
            "choices": [],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }))
        .expect("valid usage chunk"),
    ]
}

pub(crate) fn assert_final_message_shape(
    result: &AssistantMessage,
    expected: ExpectedFinalMessageShape<'_>,
) {
    assert_eq!(result.api, expected.api);
    assert_eq!(result.provider, expected.provider);
    assert_eq!(result.model, expected.model);
    assert_eq!(result.stop_reason, expected.stop_reason);
    assert_eq!(result.usage.total_tokens, expected.total_tokens);
}
