use serde::{Deserialize, Serialize};
use std::fmt::{self, Display, Formatter};
use std::str::FromStr;

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
#[serde(rename_all = "kebab-case")]
pub enum Api {
    AnthropicMessages,
    BedrockConverseStream,
    OpenAICompletions,
    OpenAIResponses,
    MinimaxCompletions,
    ZaiCompletions,
    GoogleGenerativeAi,
    GoogleVertex,
}

macro_rules! impl_str_mapping {
    ($enum_type:ty, $unknown_error:ident, { $($variant:ident => $value:literal),+ $(,)? }) => {
        impl $enum_type {
            pub const fn as_str(&self) -> &'static str {
                match self {
                    $(Self::$variant => $value,)+
                }
            }
        }

        impl Display for $enum_type {
            fn fmt(&self, f: &mut Formatter<'_>) -> fmt::Result {
                f.write_str(self.as_str())
            }
        }

        impl FromStr for $enum_type {
            type Err = crate::Error;

            fn from_str(value: &str) -> Result<Self, Self::Err> {
                match value {
                    $($value => Ok(Self::$variant),)+
                    _ => Err(crate::Error::$unknown_error(value.to_string())),
                }
            }
        }
    };
}

impl_str_mapping!(
    Api,
    UnknownApi,
    {
        AnthropicMessages => "anthropic-messages",
        BedrockConverseStream => "bedrock-converse-stream",
        OpenAICompletions => "openai-completions",
        OpenAIResponses => "openai-responses",
        MinimaxCompletions => "minimax-completions",
        ZaiCompletions => "zai-completions",
        GoogleGenerativeAi => "google-generative-ai",
        GoogleVertex => "google-vertex",
    }
);

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
#[serde(rename_all = "kebab-case")]
pub enum KnownProvider {
    AmazonBedrock,
    Anthropic,
    Featherless,
    Google,
    GoogleVertex,
    Kimi,
    OpenAI,
    Xai,
    Groq,
    Cerebras,
    OpenRouter,
    VercelAiGateway,
    Zai,
    Mistral,
    Minimax,
    MinimaxCn,
}

impl_str_mapping!(
    KnownProvider,
    UnknownProvider,
    {
        AmazonBedrock => "amazon-bedrock",
        Anthropic => "anthropic",
        Featherless => "featherless",
        Google => "google",
        GoogleVertex => "google-vertex",
        Kimi => "kimi",
        OpenAI => "openai",
        Xai => "xai",
        Groq => "groq",
        Cerebras => "cerebras",
        OpenRouter => "openrouter",
        VercelAiGateway => "vercel-ai-gateway",
        Zai => "zai",
        Mistral => "mistral",
        Minimax => "minimax",
        MinimaxCn => "minimax-cn",
    }
);

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
#[serde(untagged)]
pub enum Provider {
    Known(KnownProvider),
    Custom(String),
}

impl Provider {
    pub fn as_str(&self) -> &str {
        match self {
            Self::Known(k) => k.as_str(),
            Self::Custom(s) => s,
        }
    }
}

impl Display for Provider {
    fn fmt(&self, f: &mut Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

impl FromStr for Provider {
    type Err = crate::Error;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match KnownProvider::from_str(s) {
            Ok(k) => Ok(Self::Known(k)),
            Err(_) => Ok(Self::Custom(s.to_string())),
        }
    }
}

impl From<KnownProvider> for Provider {
    fn from(value: KnownProvider) -> Self {
        Self::Known(value)
    }
}

pub trait ApiType: Send + Sync {
    type Compat: CompatibilityOptions;
    fn api(&self) -> Api;
}

pub trait CompatibilityOptions: Send + Sync + 'static {
    fn as_any(&self) -> Option<&dyn std::any::Any>;
}

#[derive(Debug, Clone, Copy)]
pub struct NoCompat;

impl CompatibilityOptions for NoCompat {
    fn as_any(&self) -> Option<&dyn std::any::Any> {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::{Api, KnownProvider};
    use std::str::FromStr;

    #[test]
    fn minimax_completions_api_round_trip() {
        let parsed = Api::from_str("minimax-completions").expect("valid minimax API variant");
        assert_eq!(parsed, Api::MinimaxCompletions);
        assert_eq!(parsed.to_string(), "minimax-completions");
    }

    #[test]
    fn zai_completions_api_round_trip() {
        let parsed = Api::from_str("zai-completions").expect("valid zai API variant");
        assert_eq!(parsed, Api::ZaiCompletions);
        assert_eq!(parsed.to_string(), "zai-completions");
    }

    #[test]
    fn featherless_provider_round_trip() {
        let parsed =
            KnownProvider::from_str("featherless").expect("valid featherless provider variant");
        assert_eq!(parsed, KnownProvider::Featherless);
        assert_eq!(parsed.to_string(), "featherless");
    }

    #[test]
    fn kimi_provider_round_trip() {
        let parsed = KnownProvider::from_str("kimi").expect("valid kimi provider variant");
        assert_eq!(parsed, KnownProvider::Kimi);
        assert_eq!(parsed.to_string(), "kimi");
    }
}
