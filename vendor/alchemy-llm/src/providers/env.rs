use crate::types::{KnownProvider, Provider};
use std::env;
use std::path::PathBuf;
use std::sync::OnceLock;

static VERTEX_ADC_EXISTS: OnceLock<bool> = OnceLock::new();

/// Get API key for provider from known environment variables.
///
/// Returns `None` for:
/// - OAuth-only providers (github-copilot)
/// - Custom providers (no known env var mapping)
/// - Providers where credentials are missing
///
/// For Vertex AI and Bedrock, returns `Some("<authenticated>")` when
/// ADC/IAM credentials are properly configured.
pub fn get_env_api_key(provider: &Provider) -> Option<String> {
    match provider {
        Provider::Known(known) => get_env_api_key_for_known(known),
        Provider::Custom(_) => None,
    }
}

fn get_env_api_key_for_known(provider: &KnownProvider) -> Option<String> {
    match provider {
        // Anthropic: OAuth token takes precedence over API key
        KnownProvider::Anthropic => env::var("ANTHROPIC_OAUTH_TOKEN")
            .or_else(|_| env::var("ANTHROPIC_API_KEY"))
            .ok(),

        // Standard API key providers
        KnownProvider::OpenAI => env::var("OPENAI_API_KEY").ok(),
        KnownProvider::Featherless => env::var("FEATHERLESS_API_KEY").ok(),
        KnownProvider::Google => env::var("GEMINI_API_KEY").ok(),
        KnownProvider::Kimi => env::var("KIMI_API_KEY").ok(),
        KnownProvider::Groq => env::var("GROQ_API_KEY").ok(),
        KnownProvider::Cerebras => env::var("CEREBRAS_API_KEY").ok(),
        KnownProvider::Xai => env::var("XAI_API_KEY").ok(),
        KnownProvider::OpenRouter => env::var("OPENROUTER_API_KEY").ok(),
        KnownProvider::VercelAiGateway => env::var("AI_GATEWAY_API_KEY").ok(),
        KnownProvider::Zai => env::var("ZAI_API_KEY").ok(),
        KnownProvider::Mistral => env::var("MISTRAL_API_KEY").ok(),
        KnownProvider::Minimax => env::var("MINIMAX_API_KEY").ok(),
        KnownProvider::MinimaxCn => env::var("MINIMAX_CN_API_KEY").ok(),

        // Vertex AI uses Application Default Credentials
        KnownProvider::GoogleVertex => {
            if has_vertex_adc_credentials() {
                Some("<authenticated>".to_string())
            } else {
                None
            }
        }

        // Bedrock uses AWS IAM credentials
        KnownProvider::AmazonBedrock => {
            if has_bedrock_credentials() {
                Some("<authenticated>".to_string())
            } else {
                None
            }
        }
    }
}

/// Check if Vertex AI Application Default Credentials exist.
///
/// Checks in order:
/// 1. GOOGLE_APPLICATION_CREDENTIALS env var pointing to a credentials file
/// 2. Default ADC path (~/.config/gcloud/application_default_credentials.json)
///    plus required project and location env vars
fn has_vertex_adc_credentials() -> bool {
    *VERTEX_ADC_EXISTS.get_or_init(|| {
        // Check GOOGLE_APPLICATION_CREDENTIALS first
        if let Ok(path) = env::var("GOOGLE_APPLICATION_CREDENTIALS") {
            return PathBuf::from(path).exists();
        }

        // Fall back to default ADC path
        if let Some(home) = dirs::home_dir() {
            let adc_path = home
                .join(".config")
                .join("gcloud")
                .join("application_default_credentials.json");

            if adc_path.exists() {
                // Also need project and location for Vertex
                let has_project =
                    env::var("GOOGLE_CLOUD_PROJECT").is_ok() || env::var("GCLOUD_PROJECT").is_ok();
                let has_location = env::var("GOOGLE_CLOUD_LOCATION").is_ok();
                return has_project && has_location;
            }
        }
        false
    })
}

/// Check if AWS credentials are available for Bedrock.
///
/// Supports multiple credential sources:
/// 1. AWS_PROFILE - named profile from ~/.aws/credentials
/// 2. AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY - standard IAM keys
/// 3. AWS_BEARER_TOKEN_BEDROCK - Bedrock API keys (bearer token)
/// 4. AWS_CONTAINER_CREDENTIALS_RELATIVE_URI - ECS task roles
/// 5. AWS_CONTAINER_CREDENTIALS_FULL_URI - ECS task roles (full URI)
/// 6. AWS_WEB_IDENTITY_TOKEN_FILE - IRSA (IAM Roles for Service Accounts)
fn has_bedrock_credentials() -> bool {
    env::var("AWS_PROFILE").is_ok()
        || (env::var("AWS_ACCESS_KEY_ID").is_ok() && env::var("AWS_SECRET_ACCESS_KEY").is_ok())
        || env::var("AWS_BEARER_TOKEN_BEDROCK").is_ok()
        || env::var("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI").is_ok()
        || env::var("AWS_CONTAINER_CREDENTIALS_FULL_URI").is_ok()
        || env::var("AWS_WEB_IDENTITY_TOKEN_FILE").is_ok()
}

#[cfg(test)]
mod tests {
    use super::*;
    use serial_test::serial;
    use std::env;

    // Note: Tests that modify env vars should use serial test execution
    // or unique env var names to avoid interference

    #[test]
    #[serial]
    fn test_get_env_api_key_openai() {
        let key = "fake_openai_test_key";
        env::set_var("OPENAI_API_KEY", key);
        let result = get_env_api_key(&Provider::Known(KnownProvider::OpenAI));
        assert_eq!(result, Some(key.to_string()));
        env::remove_var("OPENAI_API_KEY");
    }

    #[test]
    #[serial]
    fn test_get_env_api_key_featherless() {
        let key = "fake_featherless_test_key";
        env::set_var("FEATHERLESS_API_KEY", key);
        let result = get_env_api_key(&Provider::Known(KnownProvider::Featherless));
        assert_eq!(result, Some(key.to_string()));
        env::remove_var("FEATHERLESS_API_KEY");
    }

    #[test]
    #[serial]
    fn test_get_env_api_key_kimi() {
        let key = "fake_kimi_test_key";
        env::set_var("KIMI_API_KEY", key);
        let result = get_env_api_key(&Provider::Known(KnownProvider::Kimi));
        assert_eq!(result, Some(key.to_string()));
        env::remove_var("KIMI_API_KEY");
    }

    #[test]
    #[serial]
    fn test_get_env_api_key_anthropic_api_key() {
        // Clean up any env vars from other tests
        env::remove_var("ANTHROPIC_OAUTH_TOKEN");
        env::remove_var("ANTHROPIC_API_KEY");

        let key = "fake_anthropic_test_key";
        env::set_var("ANTHROPIC_API_KEY", key);
        let result = get_env_api_key(&Provider::Known(KnownProvider::Anthropic));
        assert_eq!(result, Some(key.to_string()));

        // Clean up
        env::remove_var("ANTHROPIC_API_KEY");
        env::remove_var("ANTHROPIC_OAUTH_TOKEN");
    }

    #[test]
    #[serial]
    fn test_get_env_api_key_anthropic_oauth_takes_precedence() {
        let api_key = "fake_api_key";
        let oauth_token = "fake_oauth_token";
        env::set_var("ANTHROPIC_API_KEY", api_key);
        env::set_var("ANTHROPIC_OAUTH_TOKEN", oauth_token);
        let result = get_env_api_key(&Provider::Known(KnownProvider::Anthropic));
        assert_eq!(result, Some(oauth_token.to_string()));
        env::remove_var("ANTHROPIC_API_KEY");
        env::remove_var("ANTHROPIC_OAUTH_TOKEN");
    }

    #[test]
    #[serial]
    fn test_get_env_api_key_custom_provider_returns_none() {
        let result = get_env_api_key(&Provider::Custom("my-custom-provider".to_string()));
        assert_eq!(result, None);
    }

    #[test]
    #[serial]
    fn test_get_env_api_key_missing_returns_none() {
        env::remove_var("GROQ_API_KEY");
        let result = get_env_api_key(&Provider::Known(KnownProvider::Groq));
        assert_eq!(result, None);
    }
}
