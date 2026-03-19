use crate::agent_streaming::AssistantStreamResponse;
use crate::agent_types::{
    AgentContext, AgentMessage, AgentState, AgentTool, Context, Model, QueueMode, ThinkingBudgets,
};
use crate::error::Result;
use futures::future::BoxFuture;
use std::collections::HashMap;
use std::fmt;
use std::sync::Arc;

pub type MessageProvider = Arc<dyn Fn() -> BoxFuture<'static, Vec<AgentMessage>> + Send + Sync>;
pub type StreamFn =
    Arc<dyn Fn(StreamRequest) -> BoxFuture<'static, Result<AssistantStreamResponse>> + Send + Sync>;

#[derive(Debug, Clone, Default)]
pub struct StreamOptions {
    pub api_key: Option<String>,
    pub temperature: Option<f64>,
    pub max_tokens: Option<u32>,
    pub session_id: Option<String>,
    pub headers: Option<HashMap<String, String>>,
    pub thinking_budgets: Option<ThinkingBudgets>,
}

#[derive(Clone)]
pub struct StreamRequest {
    pub model: Model,
    pub context: Context,
    pub options: StreamOptions,
}

impl fmt::Debug for StreamRequest {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("StreamRequest")
            .field("model", &self.model)
            .field("context_messages", &self.context.messages.len())
            .field("tools", &self.context.tools.len())
            .field("options", &self.options)
            .finish()
    }
}

#[derive(Clone)]
pub struct AgentOptions {
    pub initial_state: Option<AgentState>,
    pub system_prompt: Option<String>,
    pub model: Option<Model>,
    pub tools: Vec<AgentTool>,
    pub messages: Vec<AgentMessage>,
    pub max_turns: usize,
    pub steering_mode: QueueMode,
    pub follow_up_mode: QueueMode,
    pub stream_fn: Option<StreamFn>,
    pub stream_options: StreamOptions,
}

impl Default for AgentOptions {
    fn default() -> Self {
        Self {
            initial_state: None,
            system_prompt: None,
            model: None,
            tools: Vec::new(),
            messages: Vec::new(),
            max_turns: 16,
            steering_mode: QueueMode::OneAtATime,
            follow_up_mode: QueueMode::OneAtATime,
            stream_fn: None,
            stream_options: StreamOptions::default(),
        }
    }
}

impl fmt::Debug for AgentOptions {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("AgentOptions")
            .field("has_initial_state", &self.initial_state.is_some())
            .field("system_prompt", &self.system_prompt)
            .field("model", &self.model)
            .field("tools", &self.tools.len())
            .field("messages", &self.messages.len())
            .field("max_turns", &self.max_turns)
            .field("steering_mode", &self.steering_mode)
            .field("follow_up_mode", &self.follow_up_mode)
            .field("has_stream_fn", &self.stream_fn.is_some())
            .field("stream_options", &self.stream_options)
            .finish()
    }
}

impl AgentOptions {
    pub fn initial_state(&self) -> AgentState {
        if let Some(state) = &self.initial_state {
            return state.clone();
        }

        AgentState {
            system_prompt: self.system_prompt.clone().unwrap_or_default(),
            model: self.model.clone(),
            tools: self.tools.clone(),
            messages: self.messages.clone(),
            ..AgentState::default()
        }
    }

    pub fn initial_context(&self) -> AgentContext {
        let state = self.initial_state();
        AgentContext {
            system_prompt: state.system_prompt,
            messages: state.messages,
            tools: state.tools,
        }
    }
}

#[derive(Clone)]
pub struct AgentLoopConfig {
    pub model: Model,
    pub stream_fn: Option<StreamFn>,
    pub stream_options: StreamOptions,
    pub max_turns: usize,
    pub get_steering_messages: Option<MessageProvider>,
    pub get_follow_up_messages: Option<MessageProvider>,
}

impl fmt::Debug for AgentLoopConfig {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.debug_struct("AgentLoopConfig")
            .field("model", &self.model)
            .field("has_stream_fn", &self.stream_fn.is_some())
            .field("stream_options", &self.stream_options)
            .field("max_turns", &self.max_turns)
            .field("has_steering_reader", &self.get_steering_messages.is_some())
            .field(
                "has_follow_up_reader",
                &self.get_follow_up_messages.is_some(),
            )
            .finish()
    }
}

impl AgentLoopConfig {
    pub fn from_options(
        model: Model,
        options: &AgentOptions,
        get_steering_messages: Option<MessageProvider>,
        get_follow_up_messages: Option<MessageProvider>,
    ) -> Self {
        Self {
            model,
            stream_fn: options.stream_fn.clone(),
            stream_options: options.stream_options.clone(),
            max_turns: options.max_turns,
            get_steering_messages,
            get_follow_up_messages,
        }
    }
}
