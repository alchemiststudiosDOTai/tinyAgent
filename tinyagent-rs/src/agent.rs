use crate::error::{AgentError, Result};

#[derive(Debug, Default)]
pub struct Agent;

impl Agent {
    pub fn new() -> Self {
        Self
    }

    pub async fn healthcheck(&self) -> Result<()> {
        Ok(())
    }

    pub fn ensure_ready(&self) -> Result<()> {
        Ok(())
    }

    pub fn unsupported(&self) -> Result<()> {
        Err(AgentError::UnsupportedFeature(
            "agent runtime not implemented yet".to_string(),
        ))
    }
}
