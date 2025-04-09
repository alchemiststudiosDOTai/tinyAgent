"""
Structured Outputs Handler for TinyAgent

This module provides schema-enforced JSON parsing using OpenRouter's structured outputs feature.
If schema parsing fails or is disabled, it falls back to the robust parser.
"""

import json
import logging
from typing import Dict, Any, Optional

from .json_parser import parse_json_with_strategies

logger = logging.getLogger(__name__)

def build_schema_for_task(context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Build or retrieve the JSON schema for the current task context.
    This can be dynamic or static based on the use case.
    """
    # For now, return a generic tool call schema
    schema = {
        "type": "object",
        "properties": {
            "tool": {"type": "string", "description": "Tool name"},
            "arguments": {"type": "object", "description": "Tool parameters"}
        },
        "required": ["tool", "arguments"],
        "additionalProperties": False
    }
    print("\n[StructuredOutputs] Built schema for task:")
    print(json.dumps(schema, indent=2))
    return schema

def inject_schema_in_request(messages: list, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Prepare the LLM API request payload, injecting the response_format schema if enabled.
    """
    payload = {
        "messages": messages
    }
    print(payload)
    print("\n[StructuredOutputs] Injecting schema into LLM request payload...")
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
    print("\n[StructuredOutputs] Attempting strict schema-enforced JSON parse...")
    try:
        parsed = json.loads(response_text)
        print(f"[StructuredOutputs] Raw parsed content: {parsed}")
        
        if not isinstance(parsed, dict):
            print("[StructuredOutputs] Strict parse failed: Root element is not a dictionary")
            return None
            
        print("[StructuredOutputs] Checking required fields...")
        if "tool" not in parsed:
            print("[StructuredOutputs] Strict parse failed: Missing 'tool' field")
            return None
            
        if "arguments" not in parsed:
            print("[StructuredOutputs] Strict parse failed: Missing 'arguments' field")
            return None
            
        print("[StructuredOutputs] Validating field types...")
        if not isinstance(parsed["tool"], str):
            print(f"[StructuredOutputs] Invalid tool type: {type(parsed['tool'])}")
            return None
            
        if not isinstance(parsed["arguments"], dict):
            print(f"[StructuredOutputs] Invalid arguments type: {type(parsed['arguments'])}")
            return None
            
        print("[StructuredOutputs] All schema validations passed")
        return parsed
        
    except json.JSONDecodeError as e:
        print(f"[StructuredOutputs] JSON decode error: {str(e)}")
        return None

def try_structured_parse(llm_call_func, messages: list, config: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> (Optional[Dict[str, Any]], bool):
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
        print("[StructuredOutputs] Structured outputs disabled in config.")
        return None, False

    payload = inject_schema_in_request(messages, config, context)
    response_text = llm_call_func(payload)
    print(response_text[:1000])  

    parsed = parse_strict_response(response_text)
    if parsed is not None:
        print("[StructuredOutputs] Successfully parsed schema-enforced JSON response.")
        return parsed, True

    print("[StructuredOutputs] Schema-enforced parsing failed, falling back to robust parser.")
    parsed, _ = parse_json_with_strategies(response_text)
    print("[StructuredOutputs] Fallback robust parser result:")
    print(parsed)
    return parsed, False