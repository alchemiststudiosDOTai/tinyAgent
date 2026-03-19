use thiserror::Error;

#[derive(Debug, Error)]
pub enum AgentError {
    #[error("unsupported feature: {0}")]
    UnsupportedFeature(String),
}

pub type Result<T> = core::result::Result<T, AgentError>;
