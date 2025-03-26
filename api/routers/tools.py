from fastapi import APIRouter, HTTPException
from typing import Annotated
from core.factory.agent_factory import AgentFactory
from api.dependencies import AgentFactoryDep
from ..schemas.models import ToolResult
from core.exceptions import (
    ToolNotFoundError,
    ToolExecutionError,
    RateLimitExceeded,
    ParsingError,
    AgentRetryExceeded
)
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/chat", response_model=ToolResult)
async def chat_endpoint(
    message: str,
    session_id: int,
    factory: AgentFactoryDep
):
    try:
        agent = factory.create_agent(tools=['chat'])
        response = agent.run(
            query=message,
            template_path="chat_template.jinja2"
        )
        return ToolResult(
            tool_name="chat",
            result=response,
            success=True
        )
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(500, "Internal server error")
