use std::collections::HashMap;
use std::str::FromStr;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Mutex, OnceLock};
use std::thread;
use std::time::{Instant, SystemTime, UNIX_EPOCH};

use alchemy_llm::providers::openai_completions::ReasoningEffort;
use alchemy_llm::types::{
    AnthropicMessages, AssistantMessage as AlchemyAssistantMessage,
    AssistantMessageEvent as AlchemyEvent, Content, Context as AlchemyContext, InputType,
    Message as AlchemyMessage, MinimaxCompletions, Model, ModelCost, OpenAICompletions, Provider,
    StopReason, StopReasonError, StopReasonSuccess, Tool, ToolCallId, ToolResultContent,
    ToolResultMessage as AlchemyToolResultMessage, Usage, UserContent, UserContentBlock,
    UserMessage as AlchemyUserMessage,
};
use alchemy_llm::{OpenAICompletionsOptions, stream};
use futures::StreamExt;
use pyo3::exceptions::{PyRuntimeError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use serde::Deserialize;
use serde_json::{Value, json};
use tokio::runtime::Builder;

type BindingResult<T> = Result<T, String>;
type EventItem = BindingResult<Option<Value>>;
type ResultItem = BindingResult<Value>;

static STREAM_ID_COUNTER: AtomicU64 = AtomicU64::new(1);
static BINDING_DEBUG_ENABLED: OnceLock<bool> = OnceLock::new();

fn binding_debug_enabled() -> bool {
    *BINDING_DEBUG_ENABLED.get_or_init(|| {
        std::env::var("TINYAGENT_ALCHEMY_DEBUG")
            .map(|value| {
                matches!(
                    value.to_ascii_lowercase().as_str(),
                    "1" | "true" | "yes" | "on"
                )
            })
            .unwrap_or(false)
    })
}

fn binding_debug_log(stream_id: u64, args: std::fmt::Arguments<'_>) {
    if binding_debug_enabled() {
        eprintln!("tinyagent._alchemy stream={stream_id} {args}");
    }
}

macro_rules! binding_debug {
    ($stream_id:expr, $($arg:tt)*) => {
        binding_debug_log($stream_id, format_args!($($arg)*))
    };
}

fn elapsed_ms(started_at: Instant) -> f64 {
    started_at.elapsed().as_secs_f64() * 1000.0
}

fn event_name(event: &AlchemyEvent) -> &'static str {
    match event {
        AlchemyEvent::Start { .. } => "start",
        AlchemyEvent::TextStart { .. } => "text_start",
        AlchemyEvent::TextDelta { .. } => "text_delta",
        AlchemyEvent::TextEnd { .. } => "text_end",
        AlchemyEvent::ThinkingStart { .. } => "thinking_start",
        AlchemyEvent::ThinkingDelta { .. } => "thinking_delta",
        AlchemyEvent::ThinkingEnd { .. } => "thinking_end",
        AlchemyEvent::ToolCallStart { .. } => "tool_call_start",
        AlchemyEvent::ToolCallDelta { .. } => "tool_call_delta",
        AlchemyEvent::ToolCallEnd { .. } => "tool_call_end",
        AlchemyEvent::Done { .. } => "done",
        AlchemyEvent::Error { .. } => "error",
    }
}

fn event_item_name<'a>(item: &'a EventItem) -> &'a str {
    match item {
        Ok(Some(value)) => value
            .get("type")
            .and_then(Value::as_str)
            .unwrap_or("unknown"),
        Ok(None) => "end_of_stream",
        Err(_) => "error",
    }
}

#[derive(Debug, Deserialize)]
struct PyModelInput {
    id: String,
    provider: String,
    api: String,
    base_url: String,
    #[serde(default)]
    name: Option<String>,
    #[serde(default)]
    headers: Option<HashMap<String, String>>,
    #[serde(default)]
    reasoning: ReasoningMode,
    #[serde(default)]
    context_window: Option<u32>,
    #[serde(default)]
    max_tokens: Option<u32>,
}

#[derive(Debug, Default, Deserialize)]
#[serde(untagged)]
enum ReasoningMode {
    Bool(bool),
    Level(String),
    #[default]
    Missing,
}

#[derive(Debug, Default, Deserialize)]
struct PyContextInput {
    #[serde(default)]
    system_prompt: String,
    #[serde(default)]
    messages: Vec<PyMessageInput>,
    #[serde(default)]
    tools: Option<Vec<PyToolInput>>,
}

#[derive(Debug, Deserialize)]
#[serde(tag = "role", rename_all = "snake_case")]
enum PyMessageInput {
    User {
        #[serde(default)]
        content: Vec<PyUserContentInput>,
        #[serde(default)]
        timestamp: Option<i64>,
    },
    Assistant {
        #[serde(default)]
        content: Vec<Option<PyAssistantContentInput>>,
        #[serde(default)]
        stop_reason: Option<String>,
        #[serde(default)]
        timestamp: Option<i64>,
        #[serde(default)]
        api: Option<String>,
        #[serde(default)]
        provider: Option<String>,
        #[serde(default)]
        model: Option<String>,
        #[serde(default)]
        usage: Option<Usage>,
        #[serde(default)]
        error_message: Option<String>,
    },
    ToolResult {
        #[serde(default)]
        tool_call_id: Option<String>,
        #[serde(default)]
        tool_name: Option<String>,
        #[serde(default)]
        content: Vec<PyToolResultContentInput>,
        #[serde(default)]
        details: Option<Value>,
        #[serde(default)]
        is_error: Option<bool>,
        #[serde(default)]
        timestamp: Option<i64>,
    },
}

#[derive(Debug, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
enum PyUserContentInput {
    Text {
        #[serde(default)]
        text: Option<String>,
    },
    Image {
        #[serde(default)]
        url: Option<String>,
        #[serde(default)]
        mime_type: Option<String>,
    },
}

#[derive(Debug, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
enum PyAssistantContentInput {
    Text {
        #[serde(default)]
        text: Option<String>,
        #[serde(default)]
        text_signature: Option<String>,
    },
    Thinking {
        #[serde(default)]
        thinking: Option<String>,
        #[serde(default)]
        thinking_signature: Option<String>,
    },
    ToolCall {
        #[serde(default)]
        id: Option<String>,
        #[serde(default)]
        name: Option<String>,
        #[serde(default)]
        arguments: Option<Value>,
        #[serde(default)]
        partial_json: Option<String>,
    },
    Image {
        #[serde(default)]
        url: Option<String>,
        #[serde(default)]
        mime_type: Option<String>,
    },
}

#[derive(Debug, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
enum PyToolResultContentInput {
    Text {
        #[serde(default)]
        text: Option<String>,
    },
    Image {
        #[serde(default)]
        url: Option<String>,
        #[serde(default)]
        mime_type: Option<String>,
    },
}

#[derive(Debug, Deserialize)]
struct PyToolInput {
    name: String,
    description: String,
    parameters: Value,
}

#[pyclass]
struct StreamHandle {
    stream_id: u64,
    opened_at: Instant,
    event_rx: Mutex<std::sync::mpsc::Receiver<EventItem>>,
    result_rx: Mutex<Option<std::sync::mpsc::Receiver<ResultItem>>>,
    cached_result: Mutex<Option<Value>>,
}

#[pymethods]
impl StreamHandle {
    fn next_event(&self, py: Python<'_>) -> PyResult<Option<Py<PyAny>>> {
        let wait_started_at = Instant::now();
        binding_debug!(
            self.stream_id,
            "next_event_wait_start thread={:?} since_open={:.1}ms",
            thread::current().id(),
            elapsed_ms(self.opened_at),
        );

        let next = py
            .detach(|| {
                let receiver = self
                    .event_rx
                    .lock()
                    .map_err(|_| "event stream lock poisoned".to_string())?;
                receiver
                    .recv()
                    .map_err(|_| "event stream closed unexpectedly".to_string())
            })
            .map_err(PyRuntimeError::new_err)?;

        binding_debug!(
            self.stream_id,
            "next_event_wait_end thread={:?} waited={:.1}ms since_open={:.1}ms outcome={}",
            thread::current().id(),
            wait_started_at.elapsed().as_secs_f64() * 1000.0,
            elapsed_ms(self.opened_at),
            event_item_name(&next),
        );

        match next {
            Ok(Some(value)) => Ok(Some(json_value_to_py(py, &value)?)),
            Ok(None) => Ok(None),
            Err(error) => Err(PyRuntimeError::new_err(error)),
        }
    }

    fn result(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        if let Some(value) = self
            .cached_result
            .lock()
            .map_err(|_| PyRuntimeError::new_err("result cache lock poisoned"))?
            .clone()
        {
            binding_debug!(
                self.stream_id,
                "result_cached thread={:?} since_open={:.1}ms",
                thread::current().id(),
                elapsed_ms(self.opened_at),
            );
            return json_value_to_py(py, &value);
        }

        let receiver = self
            .result_rx
            .lock()
            .map_err(|_| PyRuntimeError::new_err("result receiver lock poisoned"))?
            .take()
            .ok_or_else(|| PyRuntimeError::new_err("result() already called"))?;

        let wait_started_at = Instant::now();
        binding_debug!(
            self.stream_id,
            "result_wait_start thread={:?} since_open={:.1}ms",
            thread::current().id(),
            elapsed_ms(self.opened_at),
        );

        let value = py
            .detach(move || {
                receiver
                    .recv()
                    .map_err(|_| "result channel closed unexpectedly".to_string())
            })
            .map_err(PyRuntimeError::new_err)?
            .map_err(PyRuntimeError::new_err)?;

        binding_debug!(
            self.stream_id,
            "result_wait_end thread={:?} waited={:.1}ms since_open={:.1}ms",
            thread::current().id(),
            wait_started_at.elapsed().as_secs_f64() * 1000.0,
            elapsed_ms(self.opened_at),
        );

        *self
            .cached_result
            .lock()
            .map_err(|_| PyRuntimeError::new_err("result cache lock poisoned"))? =
            Some(value.clone());

        json_value_to_py(py, &value)
    }
}

#[pyfunction]
fn openai_completions_stream(
    py: Python<'_>,
    model: &Bound<'_, PyAny>,
    context: &Bound<'_, PyAny>,
    options: &Bound<'_, PyAny>,
) -> PyResult<StreamHandle> {
    let model_input: PyModelInput = py_json_arg(py, model, "model")?;
    let context_input: PyContextInput = py_json_arg(py, context, "context")?;
    let options_input: Value = py_json_arg(py, options, "options")?;
    let stream_id = STREAM_ID_COUNTER.fetch_add(1, Ordering::Relaxed);
    let opened_at = Instant::now();

    let (event_tx, event_rx) = std::sync::mpsc::channel();
    let (result_tx, result_rx) = std::sync::mpsc::channel();

    binding_debug!(
        stream_id,
        "open provider={} api={} model={} thread={:?}",
        model_input.provider,
        model_input.api,
        model_input.id,
        thread::current().id(),
    );

    thread::spawn(move || {
        run_stream_thread(
            stream_id,
            opened_at,
            model_input,
            context_input,
            options_input,
            event_tx,
            result_tx,
        );
    });

    Ok(StreamHandle {
        stream_id,
        opened_at,
        event_rx: Mutex::new(event_rx),
        result_rx: Mutex::new(Some(result_rx)),
        cached_result: Mutex::new(None),
    })
}

fn run_stream_thread(
    stream_id: u64,
    opened_at: Instant,
    model_input: PyModelInput,
    context_input: PyContextInput,
    options_input: Value,
    event_tx: std::sync::mpsc::Sender<EventItem>,
    result_tx: std::sync::mpsc::Sender<ResultItem>,
) {
    binding_debug!(
        stream_id,
        "worker_start thread={:?} since_open={:.1}ms",
        thread::current().id(),
        elapsed_ms(opened_at),
    );
    let outcome = run_stream_thread_inner(
        stream_id,
        opened_at,
        model_input,
        context_input,
        options_input,
        &event_tx,
    );

    match outcome {
        Ok(message) => {
            binding_debug!(
                stream_id,
                "worker_result_ready since_open={:.1}ms",
                elapsed_ms(opened_at),
            );
            let _ = result_tx.send(Ok(message));
        }
        Err(error) => {
            binding_debug!(
                stream_id,
                "worker_error since_open={:.1}ms error={}",
                elapsed_ms(opened_at),
                error,
            );
            let _ = event_tx.send(Err(error.clone()));
            let _ = result_tx.send(Err(error));
        }
    }
}

fn run_stream_thread_inner(
    stream_id: u64,
    opened_at: Instant,
    model_input: PyModelInput,
    context_input: PyContextInput,
    options_input: Value,
    event_tx: &std::sync::mpsc::Sender<EventItem>,
) -> BindingResult<Value> {
    let runtime = Builder::new_current_thread()
        .enable_all()
        .build()
        .map_err(|error| format!("failed to build tokio runtime: {error}"))?;

    runtime.block_on(async {
        let mut stream = build_stream(model_input, context_input, options_input)?;
        let mut event_count: usize = 0;
        let mut last_event_at = opened_at;

        binding_debug!(
            stream_id,
            "provider_stream_ready since_open={:.1}ms",
            elapsed_ms(opened_at),
        );

        while let Some(event) = stream.next().await {
            let now = Instant::now();
            let gap_ms = now.duration_since(last_event_at).as_secs_f64() * 1000.0;
            event_count += 1;
            binding_debug!(
                stream_id,
                "provider_event type={} count={} gap={:.1}ms since_open={:.1}ms",
                event_name(&event),
                event_count,
                gap_ms,
                elapsed_ms(opened_at),
            );

            let payload = event_to_json(&event)?;
            if event_tx.send(Ok(Some(payload))).is_err() {
                return Err("event stream receiver dropped".to_string());
            }
            last_event_at = now;
        }

        binding_debug!(
            stream_id,
            "provider_stream_end events={} since_open={:.1}ms",
            event_count,
            elapsed_ms(opened_at),
        );

        let message = stream
            .result()
            .await
            .map_err(|error| format!("stream result failed: {error}"))?;

        let payload = assistant_message_to_json(&message)?;
        let _ = event_tx.send(Ok(None));
        binding_debug!(
            stream_id,
            "provider_result_sent since_open={:.1}ms",
            elapsed_ms(opened_at),
        );
        Ok(payload)
    })
}

fn build_stream(
    model_input: PyModelInput,
    context_input: PyContextInput,
    options_input: Value,
) -> BindingResult<alchemy_llm::AssistantMessageEventStream> {
    let context = convert_context(context_input)?;
    let options = convert_options(&options_input, &model_input.reasoning)?;

    match model_input.api.as_str() {
        "anthropic-messages" => {
            let model = convert_model::<AnthropicMessages>(&model_input, AnthropicMessages)?;
            stream(&model, &context, Some(options))
                .map_err(|error| format!("failed to start anthropic-messages stream: {error}"))
        }
        "openai-completions" => {
            let model = convert_model::<OpenAICompletions>(&model_input, OpenAICompletions)?;
            stream(&model, &context, Some(options))
                .map_err(|error| format!("failed to start openai-completions stream: {error}"))
        }
        "minimax-completions" => {
            let model = convert_model::<MinimaxCompletions>(&model_input, MinimaxCompletions)?;
            stream(&model, &context, Some(options))
                .map_err(|error| format!("failed to start minimax-completions stream: {error}"))
        }
        other => Err(format!("unsupported api `{other}`")),
    }
}

fn convert_model<TApi>(input: &PyModelInput, api: TApi) -> BindingResult<Model<TApi>>
where
    TApi: alchemy_llm::types::ApiType,
{
    let provider = Provider::from_str(&input.provider)
        .map_err(|error| format!("invalid provider `{}`: {error}", input.provider))?;
    let reasoning_enabled = reasoning_enabled(&input.reasoning);

    Ok(Model {
        id: input.id.clone(),
        name: input.name.clone().unwrap_or_else(|| input.id.clone()),
        api,
        provider,
        base_url: input.base_url.clone(),
        reasoning: reasoning_enabled,
        input: vec![InputType::Text],
        cost: ModelCost {
            input: 0.0,
            output: 0.0,
            cache_read: 0.0,
            cache_write: 0.0,
        },
        context_window: input.context_window.unwrap_or(128_000),
        max_tokens: input.max_tokens.unwrap_or(4_096),
        headers: input.headers.clone(),
        compat: None,
    })
}

fn convert_context(input: PyContextInput) -> BindingResult<AlchemyContext> {
    let messages = input
        .messages
        .into_iter()
        .map(convert_message)
        .collect::<BindingResult<Vec<_>>>()?;
    let tools = input.tools.map(|items| {
        items
            .into_iter()
            .map(|tool| Tool::new(tool.name, tool.description, tool.parameters))
            .collect::<Vec<_>>()
    });

    Ok(AlchemyContext {
        system_prompt: if input.system_prompt.trim().is_empty() {
            None
        } else {
            Some(input.system_prompt)
        },
        messages,
        tools,
    })
}

fn convert_message(input: PyMessageInput) -> BindingResult<AlchemyMessage> {
    match input {
        PyMessageInput::User { content, timestamp } => {
            Ok(AlchemyMessage::User(AlchemyUserMessage {
                content: UserContent::Multi(
                    content
                        .into_iter()
                        .map(convert_user_content)
                        .collect::<BindingResult<Vec<_>>>()?,
                ),
                timestamp: timestamp.unwrap_or_else(current_timestamp_ms),
            }))
        }
        PyMessageInput::Assistant {
            content,
            stop_reason,
            timestamp,
            api,
            provider,
            model,
            usage,
            error_message,
        } => Ok(AlchemyMessage::Assistant(AlchemyAssistantMessage {
            content: content
                .into_iter()
                .flatten()
                .map(convert_assistant_content)
                .collect::<BindingResult<Vec<_>>>()?,
            api: parse_api(api.as_deref().unwrap_or("openai-completions"))?,
            provider: parse_provider(provider.as_deref().unwrap_or("openai"))?,
            model: model.unwrap_or_default(),
            usage: usage.unwrap_or_default(),
            stop_reason: parse_stop_reason(stop_reason.as_deref()),
            error_message,
            timestamp: timestamp.unwrap_or_else(current_timestamp_ms),
        })),
        PyMessageInput::ToolResult {
            tool_call_id,
            tool_name,
            content,
            details,
            is_error,
            timestamp,
        } => Ok(AlchemyMessage::ToolResult(AlchemyToolResultMessage {
            tool_call_id: ToolCallId::from(tool_call_id.unwrap_or_default()),
            tool_name: tool_name.unwrap_or_default(),
            content: content
                .into_iter()
                .map(convert_tool_result_content)
                .collect::<BindingResult<Vec<_>>>()?,
            details,
            is_error: is_error.unwrap_or(false),
            timestamp: timestamp.unwrap_or_else(current_timestamp_ms),
        })),
    }
}

fn convert_user_content(input: PyUserContentInput) -> BindingResult<UserContentBlock> {
    match input {
        PyUserContentInput::Text { text } => {
            Ok(UserContentBlock::Text(alchemy_llm::types::TextContent {
                text: text.unwrap_or_default(),
                text_signature: None,
            }))
        }
        PyUserContentInput::Image { url, mime_type } => Err(format!(
            "image input is not supported yet (url={:?}, mime_type={:?})",
            url, mime_type
        )),
    }
}

fn convert_assistant_content(input: PyAssistantContentInput) -> BindingResult<Content> {
    match input {
        PyAssistantContentInput::Text {
            text,
            text_signature,
        } => Ok(Content::Text {
            inner: alchemy_llm::types::TextContent {
                text: text.unwrap_or_default(),
                text_signature,
            },
        }),
        PyAssistantContentInput::Thinking {
            thinking,
            thinking_signature,
        } => Ok(Content::Thinking {
            inner: alchemy_llm::types::ThinkingContent {
                thinking: thinking.unwrap_or_default(),
                thinking_signature,
            },
        }),
        PyAssistantContentInput::ToolCall {
            id,
            name,
            arguments,
            partial_json,
        } => Ok(Content::ToolCall {
            inner: alchemy_llm::types::ToolCall {
                id: ToolCallId::from(id.unwrap_or_default()),
                name: name.unwrap_or_default(),
                arguments: resolve_tool_arguments(arguments, partial_json)?,
                thought_signature: None,
            },
        }),
        PyAssistantContentInput::Image { url, mime_type } => Err(format!(
            "assistant image content is not supported yet (url={:?}, mime_type={:?})",
            url, mime_type
        )),
    }
}

fn convert_tool_result_content(
    input: PyToolResultContentInput,
) -> BindingResult<ToolResultContent> {
    match input {
        PyToolResultContentInput::Text { text } => {
            Ok(ToolResultContent::Text(alchemy_llm::types::TextContent {
                text: text.unwrap_or_default(),
                text_signature: None,
            }))
        }
        PyToolResultContentInput::Image { url, mime_type } => Err(format!(
            "tool result image content is not supported yet (url={:?}, mime_type={:?})",
            url, mime_type
        )),
    }
}

fn convert_options(
    options: &Value,
    reasoning_mode: &ReasoningMode,
) -> BindingResult<OpenAICompletionsOptions> {
    let object = options
        .as_object()
        .ok_or_else(|| "options must be a JSON object".to_string())?;

    Ok(OpenAICompletionsOptions {
        api_key: optional_string(object.get("api_key"))?,
        temperature: optional_f64(object.get("temperature"))?,
        max_tokens: optional_u32(object.get("max_tokens"))?,
        tool_choice: None,
        reasoning_effort: parse_reasoning_effort(reasoning_mode)?,
        headers: None,
        zai: None,
    })
}

fn assistant_message_to_json(message: &AlchemyAssistantMessage) -> BindingResult<Value> {
    let content = message
        .content
        .iter()
        .map(content_to_json)
        .collect::<BindingResult<Vec<_>>>()?;

    Ok(json!({
        "role": "assistant",
        "content": content,
        "stop_reason": stop_reason_to_python(message.stop_reason),
        "timestamp": message.timestamp,
        "api": message.api.to_string(),
        "provider": message.provider.to_string(),
        "model": message.model,
        "usage": message.usage,
        "error_message": message.error_message,
    }))
}

fn content_to_json(content: &Content) -> BindingResult<Value> {
    match content {
        Content::Text { inner } => Ok(json!({
            "type": "text",
            "text": inner.text,
            "text_signature": inner.text_signature,
        })),
        Content::Thinking { inner } => Ok(json!({
            "type": "thinking",
            "thinking": inner.thinking,
            "thinking_signature": inner.thinking_signature,
        })),
        Content::ToolCall { inner } => Ok(json!({
            "type": "tool_call",
            "id": inner.id.as_str(),
            "name": inner.name,
            "arguments": require_object(&inner.arguments, "tool_call.arguments")?,
        })),
        Content::Image { .. } => Err("image content is not supported by tinyagent._alchemy".into()),
    }
}

fn event_to_json(event: &AlchemyEvent) -> BindingResult<Value> {
    match event {
        AlchemyEvent::Start { partial } => Ok(json!({
            "type": "start",
            "partial": assistant_message_to_json(partial)?,
        })),
        AlchemyEvent::TextStart {
            content_index,
            partial,
        } => Ok(json!({
            "type": "text_start",
            "content_index": content_index,
            "partial": assistant_message_to_json(partial)?,
        })),
        AlchemyEvent::TextDelta {
            content_index,
            delta,
            partial,
        } => Ok(json!({
            "type": "text_delta",
            "content_index": content_index,
            "delta": delta,
            "partial": assistant_message_to_json(partial)?,
        })),
        AlchemyEvent::TextEnd {
            content_index,
            content,
            partial,
        } => Ok(json!({
            "type": "text_end",
            "content_index": content_index,
            "content": content,
            "partial": assistant_message_to_json(partial)?,
        })),
        AlchemyEvent::ThinkingStart {
            content_index,
            partial,
        } => Ok(json!({
            "type": "thinking_start",
            "content_index": content_index,
            "partial": assistant_message_to_json(partial)?,
        })),
        AlchemyEvent::ThinkingDelta {
            content_index,
            delta,
            partial,
        } => Ok(json!({
            "type": "thinking_delta",
            "content_index": content_index,
            "delta": delta,
            "partial": assistant_message_to_json(partial)?,
        })),
        AlchemyEvent::ThinkingEnd {
            content_index,
            content,
            partial,
        } => Ok(json!({
            "type": "thinking_end",
            "content_index": content_index,
            "content": content,
            "partial": assistant_message_to_json(partial)?,
        })),
        AlchemyEvent::ToolCallStart {
            content_index,
            partial,
        } => Ok(json!({
            "type": "tool_call_start",
            "content_index": content_index,
            "partial": assistant_message_to_json(partial)?,
        })),
        AlchemyEvent::ToolCallDelta {
            content_index,
            delta,
            partial,
        } => Ok(json!({
            "type": "tool_call_delta",
            "content_index": content_index,
            "delta": delta,
            "partial": assistant_message_to_json(partial)?,
        })),
        AlchemyEvent::ToolCallEnd {
            content_index,
            tool_call,
            partial,
        } => Ok(json!({
            "type": "tool_call_end",
            "content_index": content_index,
            "tool_call": {
                "type": "tool_call",
                "id": tool_call.id.as_str(),
                "name": tool_call.name,
                "arguments": require_object(&tool_call.arguments, "tool_call_end.arguments")?,
            },
            "partial": assistant_message_to_json(partial)?,
        })),
        AlchemyEvent::Done { reason, message } => Ok(json!({
            "type": "done",
            "reason": stop_reason_success_to_python(*reason),
            "message": assistant_message_to_json(message)?,
        })),
        AlchemyEvent::Error { reason, error } => Ok(json!({
            "type": "error",
            "reason": stop_reason_error_to_python(*reason),
            "error": assistant_message_to_json(error)?,
        })),
    }
}

fn py_json_arg<T>(py: Python<'_>, value: &Bound<'_, PyAny>, label: &str) -> PyResult<T>
where
    T: for<'de> Deserialize<'de>,
{
    let json = py.import("json")?;
    let payload: String = json.getattr("dumps")?.call1((value,))?.extract()?;
    serde_json::from_str(&payload)
        .map_err(|error| PyValueError::new_err(format!("invalid {label}: {error}")))
}

fn json_value_to_py(py: Python<'_>, value: &Value) -> PyResult<Py<PyAny>> {
    let json = py.import("json")?;
    let payload = serde_json::to_string(value).map_err(|error| {
        PyTypeError::new_err(format!("failed to serialize JSON payload: {error}"))
    })?;
    Ok(json.getattr("loads")?.call1((payload,))?.unbind())
}

fn parse_api(raw: &str) -> BindingResult<alchemy_llm::types::Api> {
    alchemy_llm::types::Api::from_str(raw).map_err(|error| format!("invalid api `{raw}`: {error}"))
}

fn parse_provider(raw: &str) -> BindingResult<Provider> {
    Provider::from_str(raw).map_err(|error| format!("invalid provider `{raw}`: {error}"))
}

fn parse_stop_reason(raw: Option<&str>) -> StopReason {
    match raw {
        Some("length") => StopReason::Length,
        Some("tool_use") | Some("tool_calls") => StopReason::ToolUse,
        Some("error") => StopReason::Error,
        Some("aborted") => StopReason::Aborted,
        _ => StopReason::Stop,
    }
}

fn stop_reason_to_python(reason: StopReason) -> &'static str {
    match reason {
        StopReason::Stop => "stop",
        StopReason::Length => "length",
        StopReason::ToolUse => "tool_calls",
        StopReason::Error => "error",
        StopReason::Aborted => "aborted",
    }
}

fn stop_reason_success_to_python(reason: StopReasonSuccess) -> &'static str {
    match reason {
        StopReasonSuccess::Stop => "stop",
        StopReasonSuccess::Length => "length",
        StopReasonSuccess::ToolUse => "tool_calls",
    }
}

fn stop_reason_error_to_python(reason: StopReasonError) -> &'static str {
    match reason {
        StopReasonError::Error => "error",
        StopReasonError::Aborted => "aborted",
    }
}

fn parse_reasoning_effort(mode: &ReasoningMode) -> BindingResult<Option<ReasoningEffort>> {
    match mode {
        ReasoningMode::Level(value) => match value.as_str() {
            "minimal" => Ok(Some(ReasoningEffort::Minimal)),
            "low" => Ok(Some(ReasoningEffort::Low)),
            "medium" => Ok(Some(ReasoningEffort::Medium)),
            "high" => Ok(Some(ReasoningEffort::High)),
            "xhigh" => Ok(Some(ReasoningEffort::Xhigh)),
            other => Err(format!("invalid reasoning effort `{other}`")),
        },
        ReasoningMode::Bool(_) | ReasoningMode::Missing => Ok(None),
    }
}

fn reasoning_enabled(mode: &ReasoningMode) -> bool {
    match mode {
        ReasoningMode::Bool(value) => *value,
        ReasoningMode::Level(_) => true,
        ReasoningMode::Missing => false,
    }
}

fn resolve_tool_arguments(
    arguments: Option<Value>,
    partial_json: Option<String>,
) -> BindingResult<Value> {
    if let Some(arguments) = arguments {
        return Ok(arguments);
    }

    if let Some(partial_json) = partial_json {
        return serde_json::from_str(&partial_json)
            .map_err(|error| format!("invalid tool_call.partial_json: {error}"));
    }

    Ok(Value::Object(Default::default()))
}

fn require_object(value: &Value, label: &str) -> BindingResult<Value> {
    match value {
        Value::Object(_) => Ok(value.clone()),
        _ => Err(format!("{label} must be a JSON object")),
    }
}

fn optional_string(value: Option<&Value>) -> BindingResult<Option<String>> {
    match value {
        None | Some(Value::Null) => Ok(None),
        Some(Value::String(inner)) => Ok(Some(inner.clone())),
        Some(other) => Err(format!("expected string, got {other}")),
    }
}

fn optional_f64(value: Option<&Value>) -> BindingResult<Option<f64>> {
    match value {
        None | Some(Value::Null) => Ok(None),
        Some(Value::Number(number)) => number
            .as_f64()
            .map(Some)
            .ok_or_else(|| "expected finite number".to_string()),
        Some(other) => Err(format!("expected number, got {other}")),
    }
}

fn optional_u32(value: Option<&Value>) -> BindingResult<Option<u32>> {
    match value {
        None | Some(Value::Null) => Ok(None),
        Some(Value::Number(number)) => number
            .as_u64()
            .and_then(|inner| u32::try_from(inner).ok())
            .map(Some)
            .ok_or_else(|| "expected non-negative integer fitting in u32".to_string()),
        Some(other) => Err(format!("expected integer, got {other}")),
    }
}

fn current_timestamp_ms() -> i64 {
    match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(duration) => duration.as_millis() as i64,
        Err(error) => -(error.duration().as_millis() as i64),
    }
}

#[pymodule(name = "_alchemy")]
fn tinyagent_alchemy(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<StreamHandle>()?;
    module.add_function(wrap_pyfunction!(openai_completions_stream, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_model(reasoning: Value) -> PyModelInput {
        serde_json::from_value(json!({
            "id": "moonshotai/kimi-k2.5",
            "provider": "openrouter",
            "api": "openai-completions",
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
            "reasoning": reasoning,
        }))
        .expect("model should deserialize")
    }

    #[test]
    fn reasoning_string_enables_reasoning_effort() {
        let model = test_model(json!("high"));
        let options = convert_options(&json!({}), &model.reasoning).expect("options should parse");
        assert!(matches!(
            options.reasoning_effort,
            Some(ReasoningEffort::High)
        ));
        assert!(reasoning_enabled(&model.reasoning));
    }

    #[test]
    fn bool_reasoning_enables_model_without_effort() {
        let model = test_model(json!(true));
        let options = convert_options(&json!({}), &model.reasoning).expect("options should parse");
        assert!(options.reasoning_effort.is_none());
        assert!(reasoning_enabled(&model.reasoning));
    }

    #[test]
    fn tool_call_content_uses_tinyagent_shape() {
        let message = AlchemyAssistantMessage {
            content: vec![Content::ToolCall {
                inner: alchemy_llm::types::ToolCall {
                    id: ToolCallId::from("call-1"),
                    name: "lookup".to_string(),
                    arguments: json!({"query": "weather"}),
                    thought_signature: None,
                },
            }],
            api: alchemy_llm::types::Api::OpenAICompletions,
            provider: Provider::Known(alchemy_llm::types::KnownProvider::OpenRouter),
            model: "moonshotai/kimi-k2.5".to_string(),
            usage: Usage::default(),
            stop_reason: StopReason::ToolUse,
            error_message: None,
            timestamp: 123,
        };

        let payload = assistant_message_to_json(&message).expect("message should serialize");
        assert_eq!(payload["content"][0]["type"], "tool_call");
        assert_eq!(payload["content"][0]["arguments"]["query"], "weather");
        assert_eq!(payload["stop_reason"], "tool_calls");
    }

    #[test]
    fn done_event_uses_tinyagent_reason_name() {
        let message = AlchemyAssistantMessage {
            content: vec![],
            api: alchemy_llm::types::Api::OpenAICompletions,
            provider: Provider::Known(alchemy_llm::types::KnownProvider::OpenAI),
            model: "gpt-4o-mini".to_string(),
            usage: Usage::default(),
            stop_reason: StopReason::Stop,
            error_message: None,
            timestamp: 123,
        };

        let payload = event_to_json(&AlchemyEvent::Done {
            reason: StopReasonSuccess::ToolUse,
            message,
        })
        .expect("event should serialize");

        assert_eq!(payload["type"], "done");
        assert_eq!(payload["reason"], "tool_calls");
    }

    #[test]
    fn assistant_message_input_accepts_snake_case_tool_call() {
        let message: PyMessageInput = serde_json::from_value(json!({
            "role": "assistant",
            "content": [
                {
                    "type": "tool_call",
                    "id": "call-1",
                    "name": "lookup",
                    "arguments": {"query": "hi"}
                }
            ],
            "stop_reason": "tool_calls"
        }))
        .expect("assistant message should deserialize");

        let converted = convert_message(message).expect("message should convert");
        let AlchemyMessage::Assistant(message) = converted else {
            panic!("expected assistant message");
        };

        assert!(matches!(message.stop_reason, StopReason::ToolUse));
        assert_eq!(message.content.len(), 1);
    }
}
