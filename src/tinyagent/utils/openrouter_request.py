"""
OpenRouter API Request Builder for TinyAgent

This module provides a utility function to build the API request payload,
including schema-enforced structured outputs if enabled in config.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def build_openrouter_payload(
    messages: List[Dict[str, str]],
    config: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    extra_params: Optional[Dict[str, Any]] = None,
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
    payload = {"messages": messages}

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
        logger.info(
            "\n[OpenRouterRequest] Structured outputs ENABLED. Adding response_format schema to payload."
        )
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "tool_call",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "tool": {"type": "string", "description": "Tool name"},
                        "arguments": {
                            "type": "object",
                            "description": "Tool parameters",
                            "additionalProperties": False,
                        },
                    },
                    "required": ["tool", "arguments"],
                    "additionalProperties": False,
                },
            },
        }
        payload["provider"] = {"require_parameters": True}
    else:
        logger.info(
            "\n[OpenRouterRequest] Structured outputs DISABLED. Building standard payload without schema."
        )

    return payload


def make_openrouter_request(config: dict, api_key: str, payload: dict) -> dict:
    """
    Conditionally call OpenRouter using either:
    1) direct requests.post (if structured_outputs is True), or
    2) the openai library style client
    """
    import requests
    from openai import OpenAI

    logger.info("Starting OpenRouter request")
    logger.debug(f"Using structured_outputs: {config.get('structured_outputs', False)}")
    logger.debug(f"Model in payload: {payload.get('model')}")
    logger.debug(f"API Key present: {bool(api_key)}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://tinyagent.xyz",
    }

    if config.get("structured_outputs", False):
        url = "https://openrouter.ai/api/v1/chat/completions"
        logger.debug(f"Making direct request to: {url}")
        logger.debug(f"Request headers: {headers}")
        logger.debug(f"Request payload: {payload}")

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,  # Add timeout to prevent hanging
        )
        logger.debug(f"Response status: {response.status_code}")
        logger.debug(f"Response content (first 500 chars): {response.text[:500]}")

        response.raise_for_status()
        data = response.json()
        return data
    else:
        # Use the base URL from config
        base_url = config.get("base_url", "https://openrouter.ai/api/v1")
        logger.debug(f"Using base URL: {base_url}")

        client = OpenAI(base_url=base_url, api_key=api_key)
        completion = client.chat.completions.create(
            **payload,
            extra_headers={
                "HTTP-Referer": "https://tinyagent.xyz",
            },
        )
        # Convert SDK response to dict-like for uniform handling
        if hasattr(completion, "model_dump"):
            return completion.model_dump()
        else:
            # fallback: treat as dict
            return completion
