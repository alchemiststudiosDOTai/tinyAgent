use std::collections::HashMap;
use std::error::Error;
use std::fmt;
use std::str::FromStr;

use alchemy_llm::providers::openai_completions::{OpenAICompletionsOptions, ReasoningEffort, ToolChoice};
use alchemy_llm::types::{
    self as alchemy_types, Api as AlchemyApi, ApiType, AssistantMessage as AlchemyAssistantMessage,
    AssistantMessageEvent as AlchemyAssistantMessageEvent,
    Content as AlchemyContent, Context as AlchemyContext, Cost as AlchemyCost,
    ImageContent as AlchemyImageContent, InputType, Message as AlchemyMessage, Model as AlchemyModel,
    ModelCost, Provider as AlchemyProvider, StopReason as AlchemyStopReason, Tool as AlchemyTool,
    ToolCall as AlchemyToolCall, ToolResultContent as AlchemyToolResultContent,
    ToolResultMessage as AlchemyToolResultMessage, Usage as AlchemyUsage,
    UserContent as AlchemyUserContent, UserContentBlock as AlchemyUserContentBlock,
    UserMessage as AlchemyUserMessage, ZaiChatCompletionsOptions,
};
use base64::Engine;

use crate::types::{
    self, AgentTool, AssistantContent, AssistantEventContent, AssistantEventError,
    AssistantMessage, AssistantMessageEvent, AssistantMessageEventType, Context, CostPayload,
    ImageContent, Model, SimpleStreamOptions, StopReason, TextContent, ThinkingContent,
    ToolCallContent, ToolResultContent, ToolResultMessage, UsagePayload, UserContent, UserMessage,
};

pub trait TryIntoAlchemy<T> {
    fn try_into_alchemy(&self) -> Result<T, AlchemyContractError>;
}

pub trait TryFromAlchemy<T>: Sized {
    fn try_from_alchemy(value: &T) -> Result<Self, AlchemyContractError>;
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AlchemyContractError {
    MissingField(&'static str),
    ApiMismatch {
        runtime: String,
        typed: &'static str,
    },
    ProviderMismatch {
        runtime: String,
        typed: String,
    },
    UnknownApi(String),
    ToolCallArgumentsMustBeObject,
    ToolResultDetailsMustBeObject,
    UnsupportedImageUrl(String),
    UnsupportedAssistantContent(&'static str),
    InvalidDataUrl,
    InvalidBase64Image(String),
}

impl fmt::Display for AlchemyContractError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingField(field) => write!(f, "missing required field: {field}"),
            Self::ApiMismatch { runtime, typed } => {
                write!(f, "runtime api '{runtime}' does not match typed api '{typed}'")
            }
            Self::ProviderMismatch { runtime, typed } => {
                write!(
                    f,
                    "runtime provider '{runtime}' does not match typed provider '{typed}'"
                )
            }
            Self::UnknownApi(api) => write!(f, "unknown api '{api}'"),
            Self::ToolCallArgumentsMustBeObject => {
                f.write_str("tool call arguments must be a JSON object")
            }
            Self::ToolResultDetailsMustBeObject => {
                f.write_str("tool result details must be a JSON object")
            }
            Self::UnsupportedImageUrl(url) => {
                write!(f, "unsupported image url '{url}'; expected a data: URL")
            }
            Self::UnsupportedAssistantContent(kind) => {
                write!(f, "unsupported assistant content for alchemy: {kind}")
            }
            Self::InvalidDataUrl => f.write_str("invalid data URL"),
            Self::InvalidBase64Image(message) => write!(f, "invalid base64 image: {message}"),
        }
    }
}

impl Error for AlchemyContractError {}

#[derive(Debug, Clone)]
pub struct AlchemyModelSpec<TApi: ApiType> {
    pub api: TApi,
    pub provider: AlchemyProvider,
    pub base_url: String,
    pub name: String,
    pub input: Vec<InputType>,
    pub cost: ModelCost,
    pub context_window: u32,
    pub max_tokens: u32,
    pub headers: Option<HashMap<String, String>>,
    pub compat: Option<TApi::Compat>,
}

#[derive(Debug, Clone, Default)]
pub struct OpenAIOptionsSpec {
    pub tool_choice: Option<ToolChoice>,
    pub reasoning_effort: Option<ReasoningEffort>,
    pub headers: Option<HashMap<String, String>>,
    pub zai: Option<ZaiChatCompletionsOptions>,
}

pub struct AlchemyRequest<TApi: ApiType> {
    pub model: AlchemyModel<TApi>,
    pub context: AlchemyContext,
    pub options: OpenAICompletionsOptions,
}

pub fn build_alchemy_model<TApi>(
    runtime: &Model,
    spec: AlchemyModelSpec<TApi>,
) -> Result<AlchemyModel<TApi>, AlchemyContractError>
where
    TApi: ApiType,
{
    let typed_api = spec.api.api().as_str();
    if !runtime.api.is_empty() && runtime.api != typed_api {
        return Err(AlchemyContractError::ApiMismatch {
            runtime: runtime.api.clone(),
            typed: typed_api,
        });
    }

    let typed_provider = spec.provider.as_str().to_string();
    if !runtime.provider.is_empty() && runtime.provider != typed_provider {
        return Err(AlchemyContractError::ProviderMismatch {
            runtime: runtime.provider.clone(),
            typed: typed_provider,
        });
    }

    if runtime.id.is_empty() {
        return Err(AlchemyContractError::MissingField("model.id"));
    }

    Ok(AlchemyModel {
        id: runtime.id.clone(),
        name: spec.name,
        api: spec.api,
        provider: spec.provider,
        base_url: spec.base_url,
        reasoning: runtime.thinking_level != crate::types::ThinkingLevel::Off,
        input: spec.input,
        cost: spec.cost,
        context_window: spec.context_window,
        max_tokens: spec.max_tokens,
        headers: spec.headers,
        compat: spec.compat,
    })
}

pub fn build_openai_options(
    runtime_model: &Model,
    runtime_options: &SimpleStreamOptions,
    spec: OpenAIOptionsSpec,
) -> OpenAICompletionsOptions {
    OpenAICompletionsOptions {
        api_key: runtime_options.api_key.clone(),
        temperature: runtime_options.temperature,
        max_tokens: runtime_options.max_tokens,
        tool_choice: spec.tool_choice,
        reasoning_effort: spec
            .reasoning_effort
            .or_else(|| reasoning_effort_from_level(runtime_model.thinking_level)),
        headers: spec.headers,
        zai: spec.zai,
    }
}

pub fn build_alchemy_request<TApi>(
    runtime_model: &Model,
    runtime_context: &Context,
    runtime_options: &SimpleStreamOptions,
    model_spec: AlchemyModelSpec<TApi>,
    option_spec: OpenAIOptionsSpec,
) -> Result<AlchemyRequest<TApi>, AlchemyContractError>
where
    TApi: ApiType,
{
    Ok(AlchemyRequest {
        model: build_alchemy_model(runtime_model, model_spec)?,
        context: runtime_context.try_into_alchemy()?,
        options: build_openai_options(runtime_model, runtime_options, option_spec),
    })
}

fn reasoning_effort_from_level(level: crate::types::ThinkingLevel) -> Option<ReasoningEffort> {
    match level {
        crate::types::ThinkingLevel::Off => None,
        crate::types::ThinkingLevel::Minimal => Some(ReasoningEffort::Minimal),
        crate::types::ThinkingLevel::Low => Some(ReasoningEffort::Low),
        crate::types::ThinkingLevel::Medium => Some(ReasoningEffort::Medium),
        crate::types::ThinkingLevel::High => Some(ReasoningEffort::High),
        crate::types::ThinkingLevel::Xhigh => Some(ReasoningEffort::Xhigh),
    }
}

fn alchemy_stop_reason_string(reason: AlchemyStopReason) -> String {
    match reason {
        AlchemyStopReason::Stop => "stop",
        AlchemyStopReason::Length => "length",
        AlchemyStopReason::ToolUse => "tool_use",
        AlchemyStopReason::Error => "error",
        AlchemyStopReason::Aborted => "aborted",
    }
    .to_string()
}

fn parse_data_url(url: &str, mime_type: Option<&str>) -> Result<(Vec<u8>, String), AlchemyContractError> {
    let Some(rest) = url.strip_prefix("data:") else {
        return Err(AlchemyContractError::UnsupportedImageUrl(url.to_string()));
    };
    let Some((metadata, payload)) = rest.split_once(',') else {
        return Err(AlchemyContractError::InvalidDataUrl);
    };
    let Some((mime_from_url, encoding)) = metadata.split_once(';') else {
        return Err(AlchemyContractError::InvalidDataUrl);
    };
    if encoding != "base64" {
        return Err(AlchemyContractError::InvalidDataUrl);
    }

    let bytes = base64::engine::general_purpose::STANDARD
        .decode(payload)
        .map_err(|error| AlchemyContractError::InvalidBase64Image(error.to_string()))?;
    let mime = mime_type.unwrap_or(mime_from_url).to_string();
    Ok((bytes, mime))
}

fn build_data_url(image: &AlchemyImageContent) -> String {
    let encoded = base64::engine::general_purpose::STANDARD.encode(&image.data);
    format!("data:{};base64,{encoded}", image.mime_type)
}

impl TryIntoAlchemy<AlchemyCost> for CostPayload {
    fn try_into_alchemy(&self) -> Result<AlchemyCost, AlchemyContractError> {
        Ok(AlchemyCost {
            input: self.input,
            output: self.output,
            cache_read: self.cache_read,
            cache_write: self.cache_write,
            total: self.total,
        })
    }
}

impl TryFromAlchemy<AlchemyCost> for CostPayload {
    fn try_from_alchemy(value: &AlchemyCost) -> Result<Self, AlchemyContractError> {
        Ok(Self {
            input: value.input,
            output: value.output,
            cache_read: value.cache_read,
            cache_write: value.cache_write,
            total: value.total,
        })
    }
}

impl TryIntoAlchemy<AlchemyUsage> for UsagePayload {
    fn try_into_alchemy(&self) -> Result<AlchemyUsage, AlchemyContractError> {
        Ok(AlchemyUsage {
            input: self.input,
            output: self.output,
            cache_read: self.cache_read,
            cache_write: self.cache_write,
            total_tokens: self.total_tokens,
            cost: self.cost.try_into_alchemy()?,
        })
    }
}

impl TryFromAlchemy<AlchemyUsage> for UsagePayload {
    fn try_from_alchemy(value: &AlchemyUsage) -> Result<Self, AlchemyContractError> {
        Ok(Self {
            input: value.input,
            output: value.output,
            cache_read: value.cache_read,
            cache_write: value.cache_write,
            total_tokens: value.total_tokens,
            cost: CostPayload::try_from_alchemy(&value.cost)?,
        })
    }
}

impl TryIntoAlchemy<AlchemyStopReason> for StopReason {
    fn try_into_alchemy(&self) -> Result<AlchemyStopReason, AlchemyContractError> {
        Ok(match self {
            StopReason::Stop => AlchemyStopReason::Stop,
            StopReason::Length => AlchemyStopReason::Length,
            StopReason::ToolUse => AlchemyStopReason::ToolUse,
            StopReason::Error => AlchemyStopReason::Error,
            StopReason::Aborted => AlchemyStopReason::Aborted,
        })
    }
}

impl TryFromAlchemy<AlchemyStopReason> for StopReason {
    fn try_from_alchemy(value: &AlchemyStopReason) -> Result<Self, AlchemyContractError> {
        Ok(match value {
            AlchemyStopReason::Stop => StopReason::Stop,
            AlchemyStopReason::Length => StopReason::Length,
            AlchemyStopReason::ToolUse => StopReason::ToolUse,
            AlchemyStopReason::Error => StopReason::Error,
            AlchemyStopReason::Aborted => StopReason::Aborted,
        })
    }
}

impl TryIntoAlchemy<alchemy_types::TextContent> for TextContent {
    fn try_into_alchemy(&self) -> Result<alchemy_types::TextContent, AlchemyContractError> {
        Ok(alchemy_types::TextContent {
            text: self.text.clone().unwrap_or_default(),
            text_signature: self.text_signature.clone(),
        })
    }
}

impl TryFromAlchemy<alchemy_types::TextContent> for TextContent {
    fn try_from_alchemy(value: &alchemy_types::TextContent) -> Result<Self, AlchemyContractError> {
        Ok(Self {
            text: Some(value.text.clone()),
            text_signature: value.text_signature.clone(),
            ..Default::default()
        })
    }
}

impl TryIntoAlchemy<alchemy_types::ThinkingContent> for ThinkingContent {
    fn try_into_alchemy(&self) -> Result<alchemy_types::ThinkingContent, AlchemyContractError> {
        Ok(alchemy_types::ThinkingContent {
            thinking: self.thinking.clone().unwrap_or_default(),
            thinking_signature: self.thinking_signature.clone(),
        })
    }
}

impl TryFromAlchemy<alchemy_types::ThinkingContent> for ThinkingContent {
    fn try_from_alchemy(
        value: &alchemy_types::ThinkingContent,
    ) -> Result<Self, AlchemyContractError> {
        Ok(Self {
            thinking: Some(value.thinking.clone()),
            thinking_signature: value.thinking_signature.clone(),
            ..Default::default()
        })
    }
}

impl TryIntoAlchemy<AlchemyImageContent> for ImageContent {
    fn try_into_alchemy(&self) -> Result<AlchemyImageContent, AlchemyContractError> {
        let url = self
            .url
            .as_deref()
            .ok_or(AlchemyContractError::MissingField("image.url"))?;
        let (data, mime_type) = parse_data_url(url, self.mime_type.as_deref())?;
        Ok(AlchemyImageContent { data, mime_type })
    }
}

impl TryFromAlchemy<AlchemyImageContent> for ImageContent {
    fn try_from_alchemy(value: &AlchemyImageContent) -> Result<Self, AlchemyContractError> {
        Ok(Self {
            url: Some(build_data_url(value)),
            mime_type: Some(value.mime_type.clone()),
            ..Default::default()
        })
    }
}

impl TryIntoAlchemy<AlchemyToolCall> for ToolCallContent {
    fn try_into_alchemy(&self) -> Result<AlchemyToolCall, AlchemyContractError> {
        let id = self
            .id
            .clone()
            .ok_or(AlchemyContractError::MissingField("tool_call.id"))?;
        let name = self
            .name
            .clone()
            .ok_or(AlchemyContractError::MissingField("tool_call.name"))?;
        Ok(AlchemyToolCall {
            id: id.into(),
            name,
            arguments: serde_json::Value::Object(self.arguments.clone()),
            thought_signature: None,
        })
    }
}

impl TryFromAlchemy<AlchemyToolCall> for ToolCallContent {
    fn try_from_alchemy(value: &AlchemyToolCall) -> Result<Self, AlchemyContractError> {
        let arguments = match &value.arguments {
            serde_json::Value::Object(arguments) => arguments.clone(),
            _ => return Err(AlchemyContractError::ToolCallArgumentsMustBeObject),
        };
        Ok(Self {
            id: Some(value.id.to_string()),
            name: Some(value.name.clone()),
            arguments,
            partial_json: None,
            ..Default::default()
        })
    }
}

impl TryIntoAlchemy<AlchemyContent> for AssistantContent {
    fn try_into_alchemy(&self) -> Result<AlchemyContent, AlchemyContractError> {
        match self {
            Self::Text(content) => Ok(AlchemyContent::Text {
                inner: content.try_into_alchemy()?,
            }),
            Self::Thinking(content) => Ok(AlchemyContent::Thinking {
                inner: content.try_into_alchemy()?,
            }),
            Self::ToolCall(content) => Ok(AlchemyContent::ToolCall {
                inner: content.try_into_alchemy()?,
            }),
        }
    }
}

impl TryFromAlchemy<AlchemyContent> for AssistantContent {
    fn try_from_alchemy(value: &AlchemyContent) -> Result<Self, AlchemyContractError> {
        Ok(match value {
            AlchemyContent::Text { inner } => Self::Text(TextContent::try_from_alchemy(inner)?),
            AlchemyContent::Thinking { inner } => {
                Self::Thinking(ThinkingContent::try_from_alchemy(inner)?)
            }
            AlchemyContent::ToolCall { inner } => {
                Self::ToolCall(ToolCallContent::try_from_alchemy(inner)?)
            }
            AlchemyContent::Image { .. } => {
                return Err(AlchemyContractError::UnsupportedAssistantContent("image"))
            }
        })
    }
}

impl TryIntoAlchemy<AlchemyUserContentBlock> for UserContent {
    fn try_into_alchemy(&self) -> Result<AlchemyUserContentBlock, AlchemyContractError> {
        Ok(match self {
            Self::Text(content) => {
                AlchemyUserContentBlock::Text(content.try_into_alchemy()?)
            }
            Self::Image(content) => {
                AlchemyUserContentBlock::Image(content.try_into_alchemy()?)
            }
        })
    }
}

impl TryFromAlchemy<AlchemyUserContentBlock> for UserContent {
    fn try_from_alchemy(value: &AlchemyUserContentBlock) -> Result<Self, AlchemyContractError> {
        Ok(match value {
            AlchemyUserContentBlock::Text(content) => {
                Self::Text(TextContent::try_from_alchemy(content)?)
            }
            AlchemyUserContentBlock::Image(content) => {
                Self::Image(ImageContent::try_from_alchemy(content)?)
            }
        })
    }
}

impl TryIntoAlchemy<AlchemyToolResultContent> for ToolResultContent {
    fn try_into_alchemy(&self) -> Result<AlchemyToolResultContent, AlchemyContractError> {
        Ok(match self {
            Self::Text(content) => AlchemyToolResultContent::Text(content.try_into_alchemy()?),
            Self::Image(content) => AlchemyToolResultContent::Image(content.try_into_alchemy()?),
        })
    }
}

impl TryFromAlchemy<AlchemyToolResultContent> for ToolResultContent {
    fn try_from_alchemy(value: &AlchemyToolResultContent) -> Result<Self, AlchemyContractError> {
        Ok(match value {
            AlchemyToolResultContent::Text(content) => {
                Self::Text(TextContent::try_from_alchemy(content)?)
            }
            AlchemyToolResultContent::Image(content) => {
                Self::Image(ImageContent::try_from_alchemy(content)?)
            }
        })
    }
}

impl TryIntoAlchemy<AlchemyUserMessage> for UserMessage {
    fn try_into_alchemy(&self) -> Result<AlchemyUserMessage, AlchemyContractError> {
        let content = if self.content.len() == 1 {
            match &self.content[0] {
                UserContent::Text(text) => AlchemyUserContent::Text(text.text.clone().unwrap_or_default()),
                _ => AlchemyUserContent::Multi(
                    self.content
                        .iter()
                        .map(TryIntoAlchemy::try_into_alchemy)
                        .collect::<Result<Vec<_>, _>>()?,
                ),
            }
        } else {
            AlchemyUserContent::Multi(
                self.content
                    .iter()
                    .map(TryIntoAlchemy::try_into_alchemy)
                    .collect::<Result<Vec<_>, _>>()?,
            )
        };

        Ok(AlchemyUserMessage {
            content,
            timestamp: self
                .timestamp
                .ok_or(AlchemyContractError::MissingField("user_message.timestamp"))?,
        })
    }
}

impl TryFromAlchemy<AlchemyUserMessage> for UserMessage {
    fn try_from_alchemy(value: &AlchemyUserMessage) -> Result<Self, AlchemyContractError> {
        let content = match &value.content {
            AlchemyUserContent::Text(text) => vec![UserContent::Text(TextContent {
                text: Some(text.clone()),
                ..Default::default()
            })],
            AlchemyUserContent::Multi(blocks) => blocks
                .iter()
                .map(UserContent::try_from_alchemy)
                .collect::<Result<Vec<_>, _>>()?,
        };

        Ok(Self {
            role: Default::default(),
            content,
            timestamp: Some(value.timestamp),
        })
    }
}

impl TryIntoAlchemy<AlchemyAssistantMessage> for AssistantMessage {
    fn try_into_alchemy(&self) -> Result<AlchemyAssistantMessage, AlchemyContractError> {
        let api = self
            .api
            .as_deref()
            .ok_or(AlchemyContractError::MissingField("assistant_message.api"))?;
        let provider = self
            .provider
            .as_deref()
            .ok_or(AlchemyContractError::MissingField("assistant_message.provider"))?;
        let model = self
            .model
            .clone()
            .ok_or(AlchemyContractError::MissingField("assistant_message.model"))?;
        let usage = self
            .usage
            .as_ref()
            .ok_or(AlchemyContractError::MissingField("assistant_message.usage"))?;
        let stop_reason = self
            .stop_reason
            .ok_or(AlchemyContractError::MissingField("assistant_message.stop_reason"))?;
        let timestamp = self
            .timestamp
            .ok_or(AlchemyContractError::MissingField("assistant_message.timestamp"))?;

        let api = AlchemyApi::from_str(api)
            .map_err(|_| AlchemyContractError::UnknownApi(api.to_string()))?;
        let provider = AlchemyProvider::from_str(provider)
            .map_err(|_| AlchemyContractError::ProviderMismatch {
                runtime: provider.to_string(),
                typed: provider.to_string(),
            })?;
        let content = self
            .content
            .iter()
            .map(|item| match item {
                Some(item) => item.try_into_alchemy(),
                None => Err(AlchemyContractError::UnsupportedAssistantContent("null")),
            })
            .collect::<Result<Vec<_>, _>>()?;

        Ok(AlchemyAssistantMessage {
            content,
            api,
            provider,
            model,
            usage: usage.try_into_alchemy()?,
            stop_reason: stop_reason.try_into_alchemy()?,
            error_message: self.error_message.clone(),
            timestamp,
        })
    }
}

impl TryFromAlchemy<AlchemyAssistantMessage> for AssistantMessage {
    fn try_from_alchemy(value: &AlchemyAssistantMessage) -> Result<Self, AlchemyContractError> {
        Ok(Self {
            role: Default::default(),
            content: value
                .content
                .iter()
                .map(|item| AssistantContent::try_from_alchemy(item).map(Some))
                .collect::<Result<Vec<_>, _>>()?,
            stop_reason: Some(StopReason::try_from_alchemy(&value.stop_reason)?),
            timestamp: Some(value.timestamp),
            api: Some(value.api.as_str().to_string()),
            provider: Some(value.provider.as_str().to_string()),
            model: Some(value.model.clone()),
            usage: Some(UsagePayload::try_from_alchemy(&value.usage)?),
            error_message: value.error_message.clone(),
        })
    }
}

impl TryIntoAlchemy<AlchemyToolResultMessage> for ToolResultMessage {
    fn try_into_alchemy(&self) -> Result<AlchemyToolResultMessage, AlchemyContractError> {
        let tool_call_id = self
            .tool_call_id
            .clone()
            .ok_or(AlchemyContractError::MissingField("tool_result.tool_call_id"))?;
        let tool_name = self
            .tool_name
            .clone()
            .ok_or(AlchemyContractError::MissingField("tool_result.tool_name"))?;
        let timestamp = self
            .timestamp
            .ok_or(AlchemyContractError::MissingField("tool_result.timestamp"))?;

        Ok(AlchemyToolResultMessage {
            tool_call_id: tool_call_id.into(),
            tool_name,
            content: self
                .content
                .iter()
                .map(TryIntoAlchemy::try_into_alchemy)
                .collect::<Result<Vec<_>, _>>()?,
            details: if self.details.is_empty() {
                None
            } else {
                Some(serde_json::Value::Object(self.details.clone()))
            },
            is_error: self.is_error,
            timestamp,
        })
    }
}

impl TryFromAlchemy<AlchemyToolResultMessage> for ToolResultMessage {
    fn try_from_alchemy(value: &AlchemyToolResultMessage) -> Result<Self, AlchemyContractError> {
        let details = match &value.details {
            Some(serde_json::Value::Object(details)) => details.clone(),
            Some(_) => return Err(AlchemyContractError::ToolResultDetailsMustBeObject),
            None => Default::default(),
        };

        Ok(Self {
            role: Default::default(),
            tool_call_id: Some(value.tool_call_id.to_string()),
            tool_name: Some(value.tool_name.clone()),
            content: value
                .content
                .iter()
                .map(ToolResultContent::try_from_alchemy)
                .collect::<Result<Vec<_>, _>>()?,
            details,
            is_error: value.is_error,
            timestamp: Some(value.timestamp),
        })
    }
}

impl TryIntoAlchemy<AlchemyMessage> for types::Message {
    fn try_into_alchemy(&self) -> Result<AlchemyMessage, AlchemyContractError> {
        Ok(match self {
            types::Message::User(message) => AlchemyMessage::User(message.try_into_alchemy()?),
            types::Message::Assistant(message) => {
                AlchemyMessage::Assistant(message.try_into_alchemy()?)
            }
            types::Message::ToolResult(message) => {
                AlchemyMessage::ToolResult(message.try_into_alchemy()?)
            }
        })
    }
}

impl TryFromAlchemy<AlchemyMessage> for types::Message {
    fn try_from_alchemy(value: &AlchemyMessage) -> Result<Self, AlchemyContractError> {
        Ok(match value {
            AlchemyMessage::User(message) => Self::User(UserMessage::try_from_alchemy(message)?),
            AlchemyMessage::Assistant(message) => {
                Self::Assistant(AssistantMessage::try_from_alchemy(message)?)
            }
            AlchemyMessage::ToolResult(message) => {
                Self::ToolResult(ToolResultMessage::try_from_alchemy(message)?)
            }
        })
    }
}

impl TryIntoAlchemy<AlchemyTool> for AgentTool {
    fn try_into_alchemy(&self) -> Result<AlchemyTool, AlchemyContractError> {
        Ok(AlchemyTool {
            name: self.name.clone(),
            description: self.description.clone(),
            parameters: serde_json::Value::Object(self.parameters.clone()),
        })
    }
}

impl TryFromAlchemy<AlchemyTool> for AgentTool {
    fn try_from_alchemy(value: &AlchemyTool) -> Result<Self, AlchemyContractError> {
        let parameters = match &value.parameters {
            serde_json::Value::Object(parameters) => parameters.clone(),
            _ => return Err(AlchemyContractError::ToolCallArgumentsMustBeObject),
        };
        Ok(Self {
            name: value.name.clone(),
            description: value.description.clone(),
            parameters,
            label: String::new(),
            execute: None,
        })
    }
}

impl TryIntoAlchemy<AlchemyContext> for Context {
    fn try_into_alchemy(&self) -> Result<AlchemyContext, AlchemyContractError> {
        Ok(AlchemyContext {
            system_prompt: if self.system_prompt.is_empty() {
                None
            } else {
                Some(self.system_prompt.clone())
            },
            messages: self
                .messages
                .iter()
                .map(TryIntoAlchemy::try_into_alchemy)
                .collect::<Result<Vec<_>, _>>()?,
            tools: self
                .tools
                .as_ref()
                .map(|tools| {
                    tools
                        .iter()
                        .map(TryIntoAlchemy::try_into_alchemy)
                        .collect::<Result<Vec<_>, _>>()
                })
                .transpose()?,
        })
    }
}

impl TryFromAlchemy<AlchemyContext> for Context {
    fn try_from_alchemy(value: &AlchemyContext) -> Result<Self, AlchemyContractError> {
        Ok(Self {
            system_prompt: value.system_prompt.clone().unwrap_or_default(),
            messages: value
                .messages
                .iter()
                .map(types::Message::try_from_alchemy)
                .collect::<Result<Vec<_>, _>>()?,
            tools: value
                .tools
                .as_ref()
                .map(|tools| {
                    tools
                        .iter()
                        .map(AgentTool::try_from_alchemy)
                        .collect::<Result<Vec<_>, _>>()
                })
                .transpose()?,
        })
    }
}

impl TryFromAlchemy<AlchemyAssistantMessageEvent> for AssistantMessageEvent {
    fn try_from_alchemy(
        value: &AlchemyAssistantMessageEvent,
    ) -> Result<Self, AlchemyContractError> {
        Ok(match value {
            AlchemyAssistantMessageEvent::Start { partial } => Self {
                event_type: Some(AssistantMessageEventType::Start),
                partial: Some(AssistantMessage::try_from_alchemy(partial)?),
                ..Default::default()
            },
            AlchemyAssistantMessageEvent::TextStart {
                content_index,
                partial,
            } => Self {
                event_type: Some(AssistantMessageEventType::TextStart),
                content_index: Some(*content_index),
                partial: Some(AssistantMessage::try_from_alchemy(partial)?),
                ..Default::default()
            },
            AlchemyAssistantMessageEvent::TextDelta {
                content_index,
                delta,
                partial,
            } => Self {
                event_type: Some(AssistantMessageEventType::TextDelta),
                content_index: Some(*content_index),
                delta: Some(delta.clone()),
                partial: Some(AssistantMessage::try_from_alchemy(partial)?),
                ..Default::default()
            },
            AlchemyAssistantMessageEvent::TextEnd {
                content_index,
                content,
                partial,
            } => Self {
                event_type: Some(AssistantMessageEventType::TextEnd),
                content_index: Some(*content_index),
                content: Some(AssistantEventContent::Text(content.clone())),
                partial: Some(AssistantMessage::try_from_alchemy(partial)?),
                ..Default::default()
            },
            AlchemyAssistantMessageEvent::ThinkingStart {
                content_index,
                partial,
            } => Self {
                event_type: Some(AssistantMessageEventType::ThinkingStart),
                content_index: Some(*content_index),
                partial: Some(AssistantMessage::try_from_alchemy(partial)?),
                ..Default::default()
            },
            AlchemyAssistantMessageEvent::ThinkingDelta {
                content_index,
                delta,
                partial,
            } => Self {
                event_type: Some(AssistantMessageEventType::ThinkingDelta),
                content_index: Some(*content_index),
                delta: Some(delta.clone()),
                partial: Some(AssistantMessage::try_from_alchemy(partial)?),
                ..Default::default()
            },
            AlchemyAssistantMessageEvent::ThinkingEnd {
                content_index,
                content,
                partial,
            } => Self {
                event_type: Some(AssistantMessageEventType::ThinkingEnd),
                content_index: Some(*content_index),
                content: Some(AssistantEventContent::ThinkingBlock(ThinkingContent {
                    thinking: Some(content.clone()),
                    ..Default::default()
                })),
                partial: Some(AssistantMessage::try_from_alchemy(partial)?),
                ..Default::default()
            },
            AlchemyAssistantMessageEvent::ToolCallStart {
                content_index,
                partial,
            } => Self {
                event_type: Some(AssistantMessageEventType::ToolCallStart),
                content_index: Some(*content_index),
                partial: Some(AssistantMessage::try_from_alchemy(partial)?),
                ..Default::default()
            },
            AlchemyAssistantMessageEvent::ToolCallDelta {
                content_index,
                delta,
                partial,
            } => Self {
                event_type: Some(AssistantMessageEventType::ToolCallDelta),
                content_index: Some(*content_index),
                delta: Some(delta.clone()),
                partial: Some(AssistantMessage::try_from_alchemy(partial)?),
                ..Default::default()
            },
            AlchemyAssistantMessageEvent::ToolCallEnd {
                content_index,
                tool_call,
                partial,
            } => Self {
                event_type: Some(AssistantMessageEventType::ToolCallEnd),
                content_index: Some(*content_index),
                tool_call: Some(ToolCallContent::try_from_alchemy(tool_call)?),
                partial: Some(AssistantMessage::try_from_alchemy(partial)?),
                ..Default::default()
            },
            AlchemyAssistantMessageEvent::Done { reason, message } => Self {
                event_type: Some(AssistantMessageEventType::Done),
                reason: Some(alchemy_stop_reason_string((*reason).into())),
                message: Some(AssistantMessage::try_from_alchemy(message)?),
                ..Default::default()
            },
            AlchemyAssistantMessageEvent::Error { reason, error } => Self {
                event_type: Some(AssistantMessageEventType::Error),
                reason: Some(alchemy_stop_reason_string((*reason).into())),
                error: Some(AssistantEventError::Message(AssistantMessage::try_from_alchemy(
                    error,
                )?)),
                ..Default::default()
            },
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{AssistantRole, ThinkingLevel, UserRole};
    use serde_json::json;

    fn runtime_model() -> Model {
        Model {
            provider: "openai".to_string(),
            id: "gpt-5".to_string(),
            api: "openai-completions".to_string(),
            thinking_level: ThinkingLevel::High,
        }
    }

    #[test]
    fn usage_round_trip_matches_alchemy_shape() {
        let usage = UsagePayload {
            input: 10,
            output: 20,
            cache_read: 3,
            cache_write: 4,
            total_tokens: 30,
            cost: CostPayload {
                input: 0.1,
                output: 0.2,
                cache_read: 0.01,
                cache_write: 0.02,
                total: 0.33,
            },
        };

        let alchemy = usage.try_into_alchemy().expect("to alchemy");
        let round_trip = UsagePayload::try_from_alchemy(&alchemy).expect("from alchemy");
        assert_eq!(round_trip, usage);
    }

    #[test]
    fn stop_reason_round_trip_matches_alchemy_variants() {
        for reason in [
            StopReason::Stop,
            StopReason::Length,
            StopReason::ToolUse,
            StopReason::Error,
            StopReason::Aborted,
        ] {
            let alchemy = reason.try_into_alchemy().expect("to alchemy");
            let round_trip = StopReason::try_from_alchemy(&alchemy).expect("from alchemy");
            assert_eq!(round_trip, reason);
        }
    }

    #[test]
    fn build_model_requires_typed_match() {
        let model = build_alchemy_model(
            &runtime_model(),
            AlchemyModelSpec {
                api: alchemy_types::OpenAICompletions,
                provider: alchemy_types::KnownProvider::OpenAI.into(),
                base_url: "https://api.openai.com/v1".to_string(),
                name: "GPT-5".to_string(),
                input: vec![InputType::Text],
                cost: ModelCost {
                    input: 0.0,
                    output: 0.0,
                    cache_read: 0.0,
                    cache_write: 0.0,
                },
                context_window: 200_000,
                max_tokens: 16_384,
                headers: None,
                compat: None,
            },
        )
        .expect("model should build");

        assert_eq!(model.api.api(), AlchemyApi::OpenAICompletions);
        assert_eq!(model.provider.as_str(), "openai");
        assert!(model.reasoning);
    }

    #[test]
    fn build_model_rejects_provider_mismatch() {
        let error = build_alchemy_model(
            &runtime_model(),
            AlchemyModelSpec {
                api: alchemy_types::OpenAICompletions,
                provider: alchemy_types::KnownProvider::Anthropic.into(),
                base_url: "https://api.anthropic.com".to_string(),
                name: "Claude".to_string(),
                input: vec![InputType::Text],
                cost: ModelCost {
                    input: 0.0,
                    output: 0.0,
                    cache_read: 0.0,
                    cache_write: 0.0,
                },
                context_window: 200_000,
                max_tokens: 64_000,
                headers: None,
                compat: None,
            },
        )
        .expect_err("provider mismatch should fail");

        assert!(matches!(error, AlchemyContractError::ProviderMismatch { .. }));
    }

    #[test]
    fn openai_options_derive_reasoning_effort_from_runtime_model() {
        let options = build_openai_options(
            &runtime_model(),
            &SimpleStreamOptions {
                api_key: Some("sk-test".to_string()),
                temperature: Some(0.2),
                max_tokens: Some(512),
                signal: None,
            },
            OpenAIOptionsSpec::default(),
        );

        assert_eq!(options.api_key.as_deref(), Some("sk-test"));
        assert_eq!(options.temperature, Some(0.2));
        assert_eq!(options.max_tokens, Some(512));
        assert!(matches!(options.reasoning_effort, Some(ReasoningEffort::High)));
    }

    #[test]
    fn user_message_image_round_trip_uses_data_urls() {
        let message = UserMessage {
            role: UserRole::Value,
            content: vec![UserContent::Image(ImageContent {
                url: Some("data:image/png;base64,aGVsbG8=".to_string()),
                mime_type: Some("image/png".to_string()),
                ..Default::default()
            })],
            timestamp: Some(123),
        };

        let alchemy = message.try_into_alchemy().expect("user message to alchemy");
        let round_trip = UserMessage::try_from_alchemy(&alchemy).expect("back to runtime");
        assert_eq!(round_trip.timestamp, Some(123));
        match &round_trip.content[0] {
            UserContent::Image(image) => {
                assert!(
                    image.url
                        .as_deref()
                        .is_some_and(|url| url.starts_with("data:image/png;base64,"))
                );
            }
            _ => panic!("expected image"),
        }
    }

    #[test]
    fn assistant_message_requires_hydrated_metadata() {
        let message = AssistantMessage {
            role: AssistantRole::Value,
            content: vec![Some(AssistantContent::Text(TextContent {
                text: Some("hello".to_string()),
                ..Default::default()
            }))],
            ..Default::default()
        };

        let error = message
            .try_into_alchemy()
            .expect_err("missing metadata should fail");
        assert!(matches!(
            error,
            AlchemyContractError::MissingField("assistant_message.api")
        ));
    }

    #[test]
    fn assistant_message_event_done_maps_to_runtime_event() {
        let alchemy_message = AlchemyAssistantMessage {
            content: vec![AlchemyContent::Text {
                inner: alchemy_types::TextContent {
                    text: "done".to_string(),
                    text_signature: None,
                },
            }],
            api: AlchemyApi::OpenAICompletions,
            provider: alchemy_types::KnownProvider::OpenAI.into(),
            model: "gpt-5".to_string(),
            usage: AlchemyUsage::default(),
            stop_reason: AlchemyStopReason::Stop,
            error_message: None,
            timestamp: 123,
        };

        let event = AssistantMessageEvent::try_from_alchemy(&AlchemyAssistantMessageEvent::Done {
            reason: alchemy_types::StopReasonSuccess::Stop,
            message: alchemy_message,
        })
        .expect("event conversion");

        assert_eq!(event.event_type, Some(AssistantMessageEventType::Done));
        assert_eq!(event.reason.as_deref(), Some("stop"));
        assert_eq!(
            event
                .message
                .as_ref()
                .and_then(|message| message.model.as_deref()),
            Some("gpt-5")
        );
    }

    #[test]
    fn build_request_converts_context_tools_and_messages() {
        let context = Context {
            system_prompt: "You are terse".to_string(),
            messages: vec![types::Message::User(UserMessage {
                role: UserRole::Value,
                content: vec![UserContent::Text(TextContent {
                    text: Some("hi".to_string()),
                    ..Default::default()
                })],
                timestamp: Some(1),
            })],
            tools: Some(vec![AgentTool {
                name: "lookup_weather".to_string(),
                description: "Look up weather".to_string(),
                parameters: json!({
                    "type": "object"
                })
                .as_object()
                .cloned()
                .expect("json object"),
                label: "Lookup Weather".to_string(),
                execute: None,
            }]),
        };

        let request = build_alchemy_request(
            &runtime_model(),
            &context,
            &SimpleStreamOptions::default(),
            AlchemyModelSpec {
                api: alchemy_types::OpenAICompletions,
                provider: alchemy_types::KnownProvider::OpenAI.into(),
                base_url: "https://api.openai.com/v1".to_string(),
                name: "GPT-5".to_string(),
                input: vec![InputType::Text],
                cost: ModelCost {
                    input: 0.0,
                    output: 0.0,
                    cache_read: 0.0,
                    cache_write: 0.0,
                },
                context_window: 200_000,
                max_tokens: 16_384,
                headers: None,
                compat: None,
            },
            OpenAIOptionsSpec::default(),
        )
        .expect("request should build");

        assert_eq!(request.context.system_prompt.as_deref(), Some("You are terse"));
        assert_eq!(request.context.messages.len(), 1);
        assert_eq!(request.context.tools.as_ref().map(Vec::len), Some(1));
    }

    #[test]
    fn tool_call_arguments_must_be_objects() {
        let error = ToolCallContent::try_from_alchemy(&AlchemyToolCall {
            id: "call_1".into(),
            name: "lookup".to_string(),
            arguments: json!("bad"),
            thought_signature: None,
        })
        .expect_err("non-object arguments should fail");

        assert!(matches!(
            error,
            AlchemyContractError::ToolCallArgumentsMustBeObject
        ));
    }
}
