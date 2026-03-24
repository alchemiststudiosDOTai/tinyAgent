use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use super::api::{Api, ApiType, NoCompat, Provider};
use super::compat::{OpenAICompletionsCompat, OpenAIResponsesCompat};
use super::usage::ModelCost;

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum InputType {
    Text,
    Image,
}

#[derive(Debug, Clone)]
pub struct Model<TApi: ApiType> {
    pub id: String,
    pub name: String,
    pub api: TApi,
    pub provider: Provider,
    pub base_url: String,
    pub reasoning: bool,
    pub input: Vec<InputType>,
    pub cost: ModelCost,
    pub context_window: u32,
    pub max_tokens: u32,
    pub headers: Option<HashMap<String, String>>,
    pub compat: Option<TApi::Compat>,
}

#[derive(Debug, Clone, Copy)]
pub struct AnthropicMessages;

impl ApiType for AnthropicMessages {
    type Compat = NoCompat;

    fn api(&self) -> Api {
        Api::AnthropicMessages
    }
}

#[derive(Debug, Clone, Copy)]
pub struct BedrockConverseStream;

impl ApiType for BedrockConverseStream {
    type Compat = NoCompat;

    fn api(&self) -> Api {
        Api::BedrockConverseStream
    }
}

#[derive(Debug, Clone, Copy)]
pub struct OpenAICompletions;

impl ApiType for OpenAICompletions {
    type Compat = OpenAICompletionsCompat;

    fn api(&self) -> Api {
        Api::OpenAICompletions
    }
}

#[derive(Debug, Clone, Copy)]
pub struct OpenAIResponses;

impl ApiType for OpenAIResponses {
    type Compat = OpenAIResponsesCompat;

    fn api(&self) -> Api {
        Api::OpenAIResponses
    }
}

#[derive(Debug, Clone, Copy)]
pub struct MinimaxCompletions;

impl ApiType for MinimaxCompletions {
    type Compat = NoCompat;

    fn api(&self) -> Api {
        Api::MinimaxCompletions
    }
}

#[derive(Debug, Clone, Copy)]
pub struct ZaiCompletions;

impl ApiType for ZaiCompletions {
    type Compat = NoCompat;

    fn api(&self) -> Api {
        Api::ZaiCompletions
    }
}

#[derive(Debug, Clone, Copy)]
pub struct GoogleGenerativeAi;

impl ApiType for GoogleGenerativeAi {
    type Compat = NoCompat;

    fn api(&self) -> Api {
        Api::GoogleGenerativeAi
    }
}

#[derive(Debug, Clone, Copy)]
pub struct GoogleVertex;

impl ApiType for GoogleVertex {
    type Compat = NoCompat;

    fn api(&self) -> Api {
        Api::GoogleVertex
    }
}

#[cfg(test)]
mod tests {
    use super::{Api, ApiType, ZaiCompletions};

    #[test]
    fn zai_completions_marker_maps_to_zai_api() {
        let marker = ZaiCompletions;
        assert_eq!(marker.api(), Api::ZaiCompletions);
    }
}
