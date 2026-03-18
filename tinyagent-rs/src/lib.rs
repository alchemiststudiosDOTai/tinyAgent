pub mod agent;
pub mod engine;
pub mod providers;
pub mod tools;
pub mod types;

pub use agent::{Agent, AgentBuilder};
pub use providers::{
    AlchemyMinimaxProvider, ProviderAdapter, ProviderOptions, ProviderTurnRequest,
    ProviderTurnResponse,
};
pub use tools::{AgentTool, ToolExecutor, ToolRegistry, ToolUpdateCallback};
pub use types::{
    AgentContext, AgentEvent, AgentLoopConfig, AgentMessage, AgentRunResult, AgentState,
    AssistantMessage, AssistantMessageEvent, AssistantMessageEventType, Context, EventEmitter,
    EventStream, ImageContent, MessageContent, ModelConfig, TextContent, ThinkingContent,
    ThinkingLevel, ToolCallContent, ToolDefinition, ToolExecutionContext, ToolOutput,
    ToolResultMessage, UserMessage, extract_text,
};

#[cfg(test)]
mod tests {
    use anyhow::Result;
    use async_trait::async_trait;
    use futures::{StreamExt, stream};

    use crate::{
        Agent, AssistantMessage, AssistantMessageEvent, ProviderAdapter, ProviderTurnRequest,
        ProviderTurnResponse,
    };

    struct MockProvider;

    #[async_trait]
    impl ProviderAdapter for MockProvider {
        async fn stream_turn(
            &mut self,
            _request: ProviderTurnRequest,
        ) -> Result<ProviderTurnResponse> {
            let events = stream::iter(vec![
                Ok(AssistantMessageEvent::start()),
                Ok(AssistantMessageEvent::text_delta("hello from rust")),
                Ok(AssistantMessageEvent::done(AssistantMessage::from_text(
                    "hello from rust",
                ))),
            ])
            .boxed();

            Ok(ProviderTurnResponse {
                events,
                continuation: None,
            })
        }
    }

    #[tokio::test]
    async fn prompt_returns_final_assistant_text() {
        let mut agent = Agent::builder(Box::new(MockProvider))
            .build()
            .await
            .expect("agent should build");

        let result = agent
            .prompt("hi")
            .await
            .expect("prompt should complete successfully");

        assert_eq!(result.as_deref(), Some("hello from rust"));
    }
}
