"""
OpenRouter API Request Builder for TinyAgent

This module provides a utility function to build the API request payload,
including schema-enforced structured outputs if enabled in config.
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def build_openrouter_payload(
    messages: List[Dict[str, str]],
    config: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    extra_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build the OpenRouter API request payload.

    Args:
        messages: List of chat messages.
        config: Configuration dictionary.
        context: Optional task context for schema building.
        model: Optional model name override.
        temperature: Optional temperature override.
        extra_params: Optional additional parameters to include.

    Returns:
        Payload dictionary ready to send to OpenRouter API.
    """
    payload = {
        "messages": messages
    }

    # Add model if provided or from config
    if model:
        payload["model"] = model
    elif "model" in config:
        payload["model"] = config["model"]

    # Add temperature if provided or from config
    if temperature is not None:
        payload["temperature"] = temperature
    elif "temperature" in config:
        payload["temperature"] = config["temperature"]

    # Add any extra params
    if extra_params:
        payload.update(extra_params)

    # Inject response_format with schema if enabled
    if config.get("structured_outputs", False):
        logger.info("\n[OpenRouterRequest] Structured outputs ENABLED. Adding response_format schema to payload.")
        schema = {
            "type": "object",
            "properties": {
                "tool": {"type": "string", "description": "Tool name"},
                "arguments": {"type": "object", "description": "Tool parameters"}
            },
            "required": ["tool", "arguments"],
            "additionalProperties": False
        }
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "tool_call",
                "strict": True,
                "schema": schema
            }
        }
        payload["provider"] = {"require_parameters": True}
    else:
        logger.info("\n[OpenRouterRequest] Structured outputs DISABLED. Building standard payload without schema.")

    return payload


def make_openrouter_request(
    config: dict,
    api_key: str,
    payload: dict
) -> dict:
    """
    Conditionally call OpenRouter using either:
    1) direct requests.post (if structured_outputs is True), or
    2) the openai library style client
    """
    import requests
    from openai import OpenAI

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://tinyagent.xyz",
    }

    if config.get("structured_outputs", False):
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data
    else:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        completion = client.chat.completions.create(
            **payload,
            extra_headers={
                "HTTP-Referer": "https://tinyagent.xyz",
            }
        )
        # Convert SDK response to dict-like for uniform handling
        if hasattr(completion, "model_dump"):
            return completion.model_dump()
        else:
            # fallback: treat as dict
            return completion