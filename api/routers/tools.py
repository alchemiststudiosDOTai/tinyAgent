from fastapi import APIRouter, HTTPException
from core.agent import Agent
from ..schemas.models import ToolResult
from core.tools import (
    brave_web_search_tool,
    duckduckgo_web_search,
    anon_coder_tool,
    llm_serializer_tool,
    ripgrep_tool,
    aider_tool,
    file_manipulator_tool,
    custom_text_browser_tool,
    final_answer_extractor
)
from core.mcp import ensure_mcp_server
import logging
import os
from core import tool

@tool
def clean_response_tool(messy_response: str) -> str:
    """Clean and format a messy response using LLM to make it human-readable.
    
    Args:
        messy_response: The raw, messy response that needs cleaning
        
    Returns:
        A clean, formatted response suitable for human reading
    """
    # Create an agent for cleaning
    agent = Agent()
    
    # Use the agent's run method with a specific prompt
    prompt = f"""Please clean up and format this response to make it human-readable. 
    Remove any technical metadata, debug information, or formatting characters.
    Keep only the meaningful content and present it in a clear, organized way.
    
    Messy response:
    {messy_response}
    
    Clean response:"""
    
    # Use the agent's run method instead of accessing llm directly
    return agent.run(query=prompt, template_path="workflows/triage.md")

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/chat", response_model=ToolResult)
async def chat_endpoint(message: str, session_id: str = None):
    try:
        # Create triage agent
        agent = Agent()
        
        # Ensure MCP server is running
        mcp_available = ensure_mcp_server()
        if not mcp_available:
            logger.warning("MCP server is not available, some tools may not work")
        
        # Register all available tools that have the correct interface
        tools_to_register = [
            anon_coder_tool,
            llm_serializer_tool,
            ripgrep_tool,
            aider_tool,
            file_manipulator_tool,
            custom_text_browser_tool,
            final_answer_extractor,
            clean_response_tool  # Add the new response cleaner tool
        ]
        
        # Only add MCP-dependent tools if MCP server is available
        if mcp_available:
            tools_to_register.extend([brave_web_search_tool, duckduckgo_web_search])
            logger.info("MCP server is available, MCP-dependent tools loaded")
        
        for tool in tools_to_register:
            if hasattr(tool, 'name') and hasattr(tool, 'description') and hasattr(tool, 'func') and hasattr(tool, 'parameters'):
                agent.create_tool(tool.name, tool.description, tool.func, tool.parameters)
            else:
                logger.warning(f"Skipping tool registration for {tool.__class__.__name__} - missing required attributes")
        
        # Send message to triage agent using the triage template
        raw_response = agent.run(
            query=message,
            template_path="workflows/triage.md"
        )
        
        # Clean the response using the clean_response_tool
        cleaned_response = clean_response_tool(raw_response)
        
        # Return cleaned response
        return ToolResult(
            tool_name="chat",
            result=cleaned_response,
            success=True
        )
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(500, "Internal server error")
