use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub trait StreamOptions: Send + Sync {
    fn temperature(&self) -> Option<f64> {
        None
    }
    fn max_tokens(&self) -> Option<u32> {
        None
    }
    fn api_key(&self) -> Option<&str> {
        None
    }
    fn session_id(&self) -> Option<&str> {
        None
    }
    fn headers(&self) -> Option<&HashMap<String, String>> {
        None
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimpleStreamOptions {
    #[serde(flatten)]
    pub base: BaseStreamOptions,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reasoning: Option<ThinkingLevel>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub thinking_budgets: Option<ThinkingBudgets>,
}

impl StreamOptions for SimpleStreamOptions {
    fn temperature(&self) -> Option<f64> {
        self.base.temperature
    }
    fn max_tokens(&self) -> Option<u32> {
        self.base.max_tokens
    }
    fn api_key(&self) -> Option<&str> {
        self.base.api_key.as_deref()
    }
    fn session_id(&self) -> Option<&str> {
        self.base.session_id.as_deref()
    }
    fn headers(&self) -> Option<&HashMap<String, String>> {
        self.base.headers.as_ref()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BaseStreamOptions {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub max_tokens: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub api_key: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub session_id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub headers: Option<HashMap<String, String>>,
}

impl StreamOptions for BaseStreamOptions {}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ThinkingLevel {
    Minimal,
    Low,
    Medium,
    High,
    Xhigh,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThinkingBudgets {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub minimal: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub low: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub medium: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub high: Option<u32>,
}
