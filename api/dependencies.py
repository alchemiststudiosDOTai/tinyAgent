from fastapi import Depends, HTTPException
from typing import Annotated
from core.factory.agent_factory import AgentFactory
from core.config.config import load_config, get_config_value
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent

def get_agent_factory():
    factory = AgentFactory.get_instance()
    if not factory.config:  # Initialize once
        factory.config = load_config()
        # Ensure chat tool is registered
        if not factory.get_tool_metadata(get_config_value(factory.config, "api.chat_tool")):
            from core.tools import chat_tool
            factory.register_tool(chat_tool)
    return factory

AgentFactoryDep = Annotated[AgentFactory, Depends(get_agent_factory)]

def get_api_config():
    """Get API-specific configuration"""
    config = load_config()
    return {
        "app_name": get_config_value(config, "api.app_name", "tinyAgent API"),
        "enable_docs": get_config_value(config, "api.enable_docs", True),
        "cors_origins": get_config_value(config, "api.cors_origins", ["*"]),
        "port": get_config_value(config, "api.port", 9000),
        "chat_tool": get_config_value(config, "api.chat_tool", "default_chat"),
        "static_dir": str(PROJECT_ROOT / "static")
    }

def mount_static_files(app):
    """Mount static files for FastAPI app"""
    app.mount("/static", StaticFiles(directory=PROJECT_ROOT/"static"), name="static")
    app.mount("/", StaticFiles(directory=PROJECT_ROOT/"static", html=True), name="static")
