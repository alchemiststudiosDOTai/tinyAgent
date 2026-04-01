use super::content::ToolCall;
use super::message::AssistantMessage;
use super::usage::StopReason;

#[derive(Debug, Clone)]
pub enum AssistantMessageEvent {
    Start {
        partial: AssistantMessage,
    },
    TextStart {
        content_index: usize,
        partial: AssistantMessage,
    },
    TextDelta {
        content_index: usize,
        delta: String,
        partial: AssistantMessage,
    },
    TextEnd {
        content_index: usize,
        content: String,
        partial: AssistantMessage,
    },
    ThinkingStart {
        content_index: usize,
        partial: AssistantMessage,
    },
    ThinkingDelta {
        content_index: usize,
        delta: String,
        partial: AssistantMessage,
    },
    ThinkingEnd {
        content_index: usize,
        content: String,
        partial: AssistantMessage,
    },
    ToolCallStart {
        content_index: usize,
        partial: AssistantMessage,
    },
    ToolCallDelta {
        content_index: usize,
        delta: String,
        partial: AssistantMessage,
    },
    ToolCallEnd {
        content_index: usize,
        tool_call: ToolCall,
        partial: AssistantMessage,
    },
    Done {
        reason: StopReasonSuccess,
        message: AssistantMessage,
    },
    Error {
        reason: StopReasonError,
        error: AssistantMessage,
    },
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StopReasonSuccess {
    Stop,
    Length,
    ToolUse,
}

impl From<StopReasonSuccess> for StopReason {
    fn from(value: StopReasonSuccess) -> Self {
        match value {
            StopReasonSuccess::Stop => Self::Stop,
            StopReasonSuccess::Length => Self::Length,
            StopReasonSuccess::ToolUse => Self::ToolUse,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum StopReasonError {
    Error,
    Aborted,
}

impl From<StopReasonError> for StopReason {
    fn from(value: StopReasonError) -> Self {
        match value {
            StopReasonError::Error => Self::Error,
            StopReasonError::Aborted => Self::Aborted,
        }
    }
}
