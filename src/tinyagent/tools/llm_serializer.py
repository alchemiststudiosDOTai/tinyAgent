"""
LLM-powered serialization tool for the tinyAgent framework.

This module provides a tool for serializing complex objects to JSON-compatible formats
using language models. It's useful when standard serialization methods fail on complex
objects with circular references, custom types, or other challenging serialization scenarios.
"""

import json
import re
from typing import Any, Dict

from ..exceptions import ToolError
from ..logging import get_logger
from ..tool import ParamType, Tool

# Set up logger
logger = get_logger(__name__)


def serialize_complex_object(obj_type: str, obj_repr: str) -> Dict[str, Any]:
    """
    Use an LLM to convert complex objects to a serializable representation.

    This function leverages language models to understand and extract the
    structure of complex objects that are difficult to serialize using
    conventional methods.

    Args:
        obj_type: Type name of the object to serialize (e.g., "Agent", "CustomClass")
        obj_repr: String representation of the object (can be __str__, __repr__, or __dict__)

    Returns:
        JSON-serializable dictionary representation of the object

    Raises:
        ParsingError: If the LLM response cannot be parsed as valid JSON
    """
    # Import the LLM function here to avoid circular imports
    from ..agent import get_llm

    logger.info(f"Serializing complex object of type: {obj_type}")

    prompt = f"""
    Convert this {obj_type} object to a JSON-serializable format:

    {obj_repr}

    Return ONLY a valid JSON object representing the key attributes.
    DO NOT include any explanation or markdown formatting.
    The response must be parseable directly by json.loads().

    Extract these key attributes:
    - Any properties or fields that define the object's state
    - Skip methods, functions, and other non-serializable elements
    - Convert any nested complex objects to simpler representations

    Focus on preserving the information content, not the exact structure.
    """

    # Get LLM to parse and extract the structure
    try:
        llm = get_llm()
        result = llm(prompt)
        logger.debug("Received LLM response for serialization")
    except Exception as e:
        logger.error(f"Error getting LLM response: {str(e)}")
        raise ToolError(f"Failed to get LLM response: {str(e)}") from e

    # Try to parse as JSON to validate
    try:
        parsed = json.loads(result)
        return parsed
    except json.JSONDecodeError:
        # Find any JSON-like structure in the response
        json_match = re.search(r"({[\s\S]*})", result)
        if json_match:
            try:
                extracted_json = json_match.group(1)
                logger.debug(
                    f"Extracted JSON-like structure: {extracted_json[:100]}..."
                )
                return json.loads(extracted_json)
            except json.JSONDecodeError:
                logger.warning("Failed to parse extracted JSON-like structure")

        # Fall back to basic representation if parsing fails
        error_msg = "Failed to parse LLM response as JSON"
        logger.error(error_msg)
        return {
            "type": obj_type,
            "string_repr": obj_repr,
            "parse_error": error_msg,
            "llm_response": result[:500] if len(result) > 500 else result,
        }


# Create the tool instance
llm_serializer_tool = Tool(
    name="llm_serializer",
    description="""
    Serialize complex objects to JSON-compatible formats using LLM capabilities.

    This tool is useful when standard serialization methods fail on complex objects
    with circular references, custom types, or other serialization challenges.

    The LLM analyzes the object's structure and extracts the key attributes
    into a serializable format, preserving as much information as possible.
    """,
    parameters={"obj_type": ParamType.STRING, "obj_repr": ParamType.STRING},
    func=serialize_complex_object,
)


def get_tool() -> Tool:
    """
    Return the llm_serializer tool instance for tinyAgent integration.

    Returns:
        Tool: The llm_serializer tool object
    """
    return llm_serializer_tool
