use std::sync::Arc;

use anyhow::{Result, anyhow};
use tokio::sync::Mutex;

use crate::{
    engine::run_loop,
    providers::ProviderAdapter,
    tools::{AgentTool, ToolRegistry},
    types::{
        AgentEvent, AgentLoopConfig, AgentMessage, AgentRunResult, AgentState, AssistantMessage,
        AssistantMessageEventType, EventStream, event_stream, extract_text,
    },
};

use super::builder::AgentBuilder;

pub struct Agent {
    provider: Arc<Mutex<Box<dyn ProviderAdapter>>>,
    tools: ToolRegistry,
    config: AgentLoopConfig,
    state: Arc<Mutex<AgentState>>,
}

impl Agent {
    pub(crate) fn new(
        provider: Box<dyn ProviderAdapter>,
        tools: ToolRegistry,
        config: AgentLoopConfig,
        state: AgentState,
    ) -> Self {
        Self {
            provider: Arc::new(Mutex::new(provider)),
            tools,
            config,
            state: Arc::new(Mutex::new(state)),
        }
    }

    pub fn builder(provider: Box<dyn ProviderAdapter>) -> AgentBuilder {
        AgentBuilder::new(provider)
    }

    pub async fn register_tool(&self, tool: Arc<dyn AgentTool>) {
        self.tools.register(tool).await;
    }

    pub async fn state(&self) -> AgentState {
        self.state.lock().await.clone()
    }

    pub async fn prompt(&mut self, prompt: impl Into<String>) -> Result<Option<String>> {
        let mut stream = self.stream(prompt).await?;
        while stream.next().await.is_some() {}
        Ok(stream.result().await?.final_text)
    }

    pub async fn stream(
        &mut self,
        prompt: impl Into<String>,
    ) -> Result<EventStream<AgentEvent, AgentRunResult>> {
        let message = AgentMessage::user_text(prompt);
        self.start_stream(vec![message]).await
    }

    pub async fn continue_from_context(
        &mut self,
    ) -> Result<EventStream<AgentEvent, AgentRunResult>> {
        let snapshot = self.state.lock().await.clone();
        if snapshot.messages.is_empty() {
            return Err(anyhow!("cannot continue: no messages in state"));
        }
        if matches!(snapshot.messages.last(), Some(AgentMessage::Assistant(_))) {
            return Err(anyhow!("cannot continue from an assistant message"));
        }
        drop(snapshot);

        self.start_stream(Vec::new()).await
    }

    pub async fn stream_text(
        &mut self,
        prompt: impl Into<String>,
    ) -> Result<EventStream<String, AgentRunResult>> {
        let mut agent_events = self.stream(prompt).await?;
        let (emitter, text_stream) = event_stream::<String, AgentRunResult>();

        tokio::spawn(async move {
            while let Some(event) = agent_events.next().await {
                if let AgentEvent::MessageUpdate {
                    assistant_message_event: Some(assistant_event),
                    ..
                } = event
                {
                    if assistant_event.event_type == AssistantMessageEventType::TextDelta {
                        if let Some(delta) = assistant_event.delta {
                            let _ = emitter.push(delta);
                        }
                    }
                }
            }

            match agent_events.result().await {
                Ok(result) => {
                    let _ = emitter.finish(result);
                }
                Err(error) => {
                    let _ = emitter.fail(error);
                }
            }
        });

        Ok(text_stream)
    }

    async fn start_stream(
        &mut self,
        initial_messages: Vec<AgentMessage>,
    ) -> Result<EventStream<AgentEvent, AgentRunResult>> {
        let mut state = self.state.lock().await;
        if state.is_streaming {
            return Err(anyhow!("agent is already streaming"));
        }
        state.is_streaming = true;
        state.error = None;

        let snapshot = state.clone();
        drop(state);

        let provider = self.provider.clone();
        let tools = self.tools.clone();
        let config = self.config.clone();
        let state_handle = self.state.clone();
        let (emitter, stream) = event_stream::<AgentEvent, AgentRunResult>();

        tokio::spawn(async move {
            let result = run_loop(
                provider,
                tools,
                config,
                snapshot.system_prompt,
                snapshot.messages,
                initial_messages,
                snapshot.provider_state,
                emitter.clone(),
            )
            .await;

            let mut state = state_handle.lock().await;
            match result {
                Ok(run_result) => {
                    state.messages.extend(run_result.messages.clone());
                    state.provider_state = run_result.provider_state.clone();
                    state.error = None;
                    state.is_streaming = false;
                    let _ = emitter.finish(run_result);
                }
                Err(error) => {
                    state.error = Some(error.to_string());
                    state.is_streaming = false;
                    let _ = emitter.fail(error);
                }
            }
        });

        Ok(stream)
    }
}

#[allow(dead_code)]
fn _assistant_text(message: &AssistantMessage) -> String {
    extract_text(&AgentMessage::Assistant(message.clone()))
}
