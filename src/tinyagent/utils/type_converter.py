import re
import json
import logging
from typing import Optional, Any, Type

# Pre-compile regex for efficiency
FLOAT_REGEX = re.compile(r'-?(\d+\.?\d*|\.\d+)')
INT_REGEX = re.compile(r'-?\d+')

# Define common boolean string representations (lowercase)
TRUE_STRS = {"true", "yes", "1", "on", "t", "y"}
FALSE_STRS = {"false", "no", "0", "off", "f", "n"}

def convert_to_expected_type(result: Any, expected_type: Optional[Type], logger: Optional[logging.Logger] = None) -> Any:
    """Attempts to convert the result to the expected type if specified.

    Supports common types: str, int, float, bool, list, dict.
    Uses regex for numeric extraction from strings and json.loads for list/dict.

    Args:
        result: The result value to potentially convert.
        expected_type: The desired type (e.g., int, float, bool, list, dict, str).
        logger: Optional logger instance for warnings.

    Returns:
        The converted result.

    Raises:
        ValueError: If the result cannot be converted to the expected type.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    if expected_type is None or isinstance(result, expected_type):
        # No conversion needed if type matches or no type specified
        return result

    original_result = result # Keep original for logging/fallback
    converted_result = None

    try:
        # --- String Conversion --- (Often a base case)
        if expected_type is str:
            converted_result = str(original_result)
            logger.info(f"Converted result to str: '{converted_result[:100]}...'")

        # --- Integer Conversion --- (Handles existing int/float or extracts from string)
        elif expected_type is int:
            if isinstance(original_result, (int, float)):
                converted_result = int(original_result)
                logger.info(f"Converted numeric result to int: {converted_result}")
            elif isinstance(original_result, str):
                numbers = INT_REGEX.findall(original_result)
                if numbers:
                    converted_result = int(numbers[-1]) # Take last integer found
                    logger.info(f"Extracted and converted result to int: {converted_result}")
                else:
                    raise ValueError(f"No integer found in string: '{original_result[:100]}...'")
            else:
                raise ValueError(f"Cannot convert type {type(original_result)} to int")

        # --- Float Conversion --- (Handles existing int/float or extracts from string)
        elif expected_type is float:
            if isinstance(original_result, (int, float)):
                converted_result = float(original_result)
                logger.info(f"Converted numeric result to float: {converted_result}")
            elif isinstance(original_result, str):
                numbers = FLOAT_REGEX.findall(original_result)
                if numbers:
                    converted_result = float(numbers[-1]) # Take last float/int found
                    logger.info(f"Extracted and converted result to float: {converted_result}")
                else:
                    raise ValueError(f"No number found in string: '{original_result[:100]}...'")
            else:
                raise ValueError(f"Cannot convert type {type(original_result)} to float")

        # --- Boolean Conversion --- (Handles existing bool/numeric or common strings)
        elif expected_type is bool:
            if isinstance(original_result, bool):
                converted_result = original_result # Already bool
            elif isinstance(original_result, (int, float)):
                converted_result = bool(original_result)
                logger.info(f"Converted numeric result to bool: {converted_result}")
            elif isinstance(original_result, str):
                val_lower = original_result.strip().lower()
                if val_lower in TRUE_STRS:
                    converted_result = True
                    logger.info(f"Converted string '{original_result}' to bool: True")
                elif val_lower in FALSE_STRS:
                    converted_result = False
                    logger.info(f"Converted string '{original_result}' to bool: False")
                else:
                    raise ValueError(f"String '{original_result[:100]}...' is not a recognized boolean value")
            else:
                raise ValueError(f"Cannot convert type {type(original_result)} to bool")

        # --- List/Dict Conversion (JSON) --- (Handles existing list/dict or parses from string)
        elif expected_type in (list, dict):
            if isinstance(original_result, (list, dict)):
                # Already correct type, check if it matches expected list vs dict
                if isinstance(original_result, expected_type):
                    converted_result = original_result # Correct type
                else:
                    raise ValueError(f"Input is {type(original_result).__name__} but expected {expected_type.__name__}")
            elif isinstance(original_result, str):
                try:
                    parsed_json = json.loads(original_result)
                    if isinstance(parsed_json, expected_type):
                        converted_result = parsed_json
                        logger.info(f"Parsed string and converted to {expected_type.__name__}.")
                    else:
                        raise ValueError(f"Parsed JSON is type {type(parsed_json).__name__}, but expected {expected_type.__name__}")
                except json.JSONDecodeError:
                    raise ValueError(f"Failed to parse string as JSON: '{original_result[:100]}...'")
            else:
                raise ValueError(f"Cannot convert type {type(original_result)} to {expected_type.__name__}")

        else:
            # If expected_type is not one we handle, raise error
            raise ValueError(f"Unsupported expected_type: {expected_type}")

    except Exception as e:
        logger.error(f"Error during type conversion to {expected_type}: {e}")
        raise ValueError(f"Failed to convert result to {expected_type.__name__}: {str(e)}")

    return converted_result 