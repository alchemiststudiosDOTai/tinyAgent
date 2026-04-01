pub mod alchemy_contract;
pub mod agent;
pub mod agent_loop;
pub mod agent_tool_execution;
pub mod types;

pub use alchemy_contract::{
    AlchemyContractError, AlchemyModelSpec, AlchemyRequest, OpenAIOptionsSpec,
    TryFromAlchemy, TryIntoAlchemy, build_alchemy_model, build_alchemy_request,
    build_openai_options,
};
pub use agent::{
    AbortHandle, Agent, AgentInput, AgentListener, AgentOptions, QueueMode,
    create_error_message, default_convert_to_llm, extract_text, has_meaningful_content,
};
pub use agent_loop::{
    AgentEventStream, AgentLoopError, AgentLoopResult, agent_loop, agent_loop_continue,
    build_llm_context, create_agent_stream, resolve_api_key, run_loop, stream_assistant_response,
};
pub use agent_tool_execution::{
    ToolExecutionContractResult, ToolExecutionError, ToolExecutionResult, execute_tool_calls,
    skip_tool_call, validate_tool_arguments,
};
pub use types::*;
