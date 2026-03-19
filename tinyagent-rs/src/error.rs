use thiserror::Error;

#[derive(Debug, Error)]
pub enum AgentError {
    #[error("agent is already processing a prompt")]
    AlreadyStreaming,

    #[error("no model configured")]
    NoModelConfigured,

    #[error("cannot continue: no messages in context")]
    CannotContinueWithoutMessages,

    #[error("cannot continue from message role: assistant")]
    CannotContinueFromAssistant,

    #[error("max turns exceeded ({max_turns})")]
    MaxTurnsExceeded { max_turns: usize },

    #[error("unsupported API `{0}`")]
    UnsupportedApi(String),

    #[error("unsupported model `{id}` for provider `{provider}` and api `{api}`")]
    UnsupportedModel {
        provider: String,
        api: String,
        id: String,
    },

    #[error("internal error: {0}")]
    Internal(String),

    #[error("aborted")]
    Aborted,

    #[error(transparent)]
    SerdeJson(#[from] serde_json::Error),

    #[error(transparent)]
    Alchemy(#[from] alchemy_llm::Error),
}

pub type Result<T> = core::result::Result<T, AgentError>;
