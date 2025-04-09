from tinyagent.config.config import load_config


def get_api_config():
    """Get API-specific configuration using existing config loader"""
    config = load_config()
    return {
        "app_name": "AI Agent API",
        "enable_docs": config.get("api", {}).get("enable_docs", True),
        "cors_origins": config.get("api", {}).get("cors_origins", ["*"]),
        "port": config.get("api", {}).get("port", 9000)
    }
