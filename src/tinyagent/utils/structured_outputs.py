"""
Structured Outputs Handler for TinyAgent

This module provides schema-enforced JSON parsing using OpenRouter's structured outputs feature.
If schema parsing fails or is disabled, it falls back to the robust parser.
"""

import json
import logging
from typing import Dict, Any, Optional, Union

def _forbid_extra(node: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively ensure every JSON-schema object contains
    `"additionalProperties": False` (required by Mistral/OpenAI).
    """
    if node.get("type") == "object":
        node.setdefault("additionalProperties", False)
        for prop in node.get("properties", {}).values():
            _forbid_extra(prop)
    elif node.get("type") == "array" and "items" in node:
        _forbid_extra(node["items"])
    return node

try:
    from .json_parser import parse_json_with_strategies
except ImportError:
    from tinyagent.utils.json_parser import parse_json_with_strategies

logger = logging.getLogger(__name__)

def build_schema_for_task() -> Dict[str, Any]:
    """Build a JSON schema for the task response."""
    # Define the schema with all required properties
    schema = {
        "type": "object",
        "properties": {
            "tool": {
                "type": "string",
                "description": "Tool name"
            },
            "arguments": {
                "type": "object",
                "description": "Tool parameters",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["a", "b"],
                "additionalProperties": False
            }
        },
        "required": ["tool", "arguments"],
        "additionalProperties": False
    }
    
    # Log the final schema being used
    schema_str = json.dumps(schema, indent=2)
    logger.info("\n[StructuredOutputs] Built schema for task:")
    logger.info(schema_str)
    
    # Verify the schema is valid JSON
    try:
        json.loads(schema_str)
        logger.debug("[StructuredOutputs] Schema is valid JSON")
    except json.JSONDecodeError as e:
        logger.error(f"[StructuredOutputs] Invalid JSON schema: {e}")
        raise
        
    return schema

def inject_schema_in_request(messages: list, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Prepare the LLM API request payload, injecting the response_format schema if enabled.
    """
    payload = {
        "messages": messages
    }
    logger.info(json.dumps(payload, indent=2))
    logger.info("\n[StructuredOutputs] Injecting schema into LLM request payload...")
    if config.get("structured_outputs", False):
        schema = build_schema_for_task(context)
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "tool_call",
                "strict": True,
                "schema": schema
            }
        }
    return payload

def parse_strict_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Attempt to parse the LLM response assuming strict schema compliance.
    Returns parsed dict on success, or None on failure.
    """
    logger.info("\n[StructuredOutputs] Attempting strict schema-enforced JSON parse...")
    try:
        parsed = json.loads(response_text)
        logger.info(f"[StructuredOutputs] Raw parsed content: {parsed}")
        
        if not isinstance(parsed, dict):
            logger.info("[StructuredOutputs] Strict parse failed: Root element is not a dictionary")
            return None
            
        logger.info("[StructuredOutputs] Checking required fields...")
        if "tool" not in parsed:
            logger.info("[StructuredOutputs] Strict parse failed: Missing 'tool' field")
            return None
            
        if "arguments" not in parsed:
            logger.info("[StructuredOutputs] Strict parse failed: Missing 'arguments' field")
            return None
            
        logger.info("[StructuredOutputs] Validating field types...")
        if not isinstance(parsed["tool"], str):
            logger.info(f"[StructuredOutputs] Invalid tool type: {type(parsed['tool'])}")
            return None
            json_parser
        if not isinstance(parsed["arguments"], dict):
            logger.info(f"[StructuredOutputs] Invalid arguments type: {type(parsed['arguments'])}")
            return None
            
        logger.info("[StructuredOutputs] All schema validations passed")
        return parsed
        
    except json.JSONDecodeError as e:
        logger.info(f"[StructuredOutputs] JSON decode error: {str(e)}")
        return None

from typing import Tuple

def try_structured_parse(llm_call_func, messages: list, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[Dict[str, Any]], bool]:
    """
    Attempt to get and parse a schema-enforced response from the LLM.
    Falls back to robust parsing if schema parsing fails or is disabled.
    
    Args:
        llm_call_func: Function to call the LLM, accepting the request payload dict.
        messages: List of chat messages.
        config: Configuration dict.
        context: Optional task context for schema building.
    
    Returns:
        Tuple of (parsed JSON dict or None, used_structured_outputs: bool)
    """
    if not config.get("structured_outputs", False):
        logger.info("[StructuredOutputs] Structured outputs disabled in config.")
        return None, False

    payload = inject_schema_in_request(messages, config, context)
    response_text = llm_call_func(payload)
    logger.info(response_text[:1000])

    parsed = parse_strict_response(response_text)
    if parsed is not None:
        logger.info("[StructuredOutputs] Successfully parsed schema-enforced JSON response.")
        return parsed, True

    logger.info("[StructuredOutputs] Schema-enforced parsing failed, falling back to robust parser.")
    parsed, _ = parse_json_with_strategies(response_text)
    logger.info("[StructuredOutputs] Fallback robust parser result:")
    logger.info(parsed)
    return parsed, False