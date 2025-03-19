"""
Agent implementation for the tinyAgent framework.

This module provides the Agent class, which is the central component of the
tinyAgent framework. The Agent uses a language model to select and execute
tools based on user queries.
"""

from openai import OpenAI

import os
import re
import json
import time
from typing import List, Dict, Any, Optional, Union, Callable, TypeVar, cast

from openai import OpenAI

from .exceptions import AgentRetryExceeded, ConfigurationError, ParsingError
from .tool import Tool
from .logging import get_logger

# Set up logger
logger = get_logger(__name__)

# Type definitions
class ToolCallResult(Dict[str, Any]):
    """Type definition for a tool call result entry in history."""
    tool: str
    args: Dict[str, Any]
    result: Any
    success: bool
    timestamp: float


class ToolCallError(Dict[str, Any]):
    """Type definition for a tool call error entry in history."""
    tool: str
    args: Dict[str, Any]
    error: str
    success: bool
    timestamp: float


class Agent:
    """
    An agent that uses LLMs to select and execute tools based on user queries.
    
    This class is the central component of the tinyAgent framework. It connects
    to a language model, formats available tools as a prompt, and uses the model's
    response to decide which tool to execute.
    
    Attributes:
        tools: Dictionary of available tools, indexed by name
        model: Name of the language model to use
        max_retries: Maximum number of retries for LLM calls
        api_key: API key for the language model provider
        config: Optional configuration dictionary
        parser: Optional response parser
        history: List of tool call results and errors
    """
    
    # Constants
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    ENV_API_KEY = "OPENROUTER_API_KEY"
    
    def __init__(
        self,
        factory: Optional['AgentFactory'] = None,
        model: Optional[str] = None,
        max_retries: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an Agent with tools, model, and configuration.
        
        Args:
            tools: List of Tool objects or decorated functions to register
            model: Language model identifier (e.g., "deepseek/deepseek-chat")
            max_retries: Maximum number of retries for failed LLM calls
            config: Optional configuration dictionary
            
        Raises:
            ConfigurationError: If required configuration is missing
        """
        # Store configuration
        self.config = config
        
        # Try to load environment variables from project root
        try:
            from dotenv import load_dotenv
            # Get project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            env_path = os.path.join(project_root, '.env')
            load_dotenv(env_path)
            logger.debug(f"Loaded environment variables from {env_path}")
        except ImportError:
            logger.warning("python-dotenv not available, skipping .env loading")
        
        # Get API key
        self.api_key = os.getenv(self.ENV_API_KEY)
        if not self.api_key:
            raise ConfigurationError(
                f"API key not found. The {self.ENV_API_KEY} environment variable must be set in .env file."
            )
            
        # Set model and max_retries from config or defaults
        self.model = model or self._get_config_value('model.default', "deepseek/deepseek-chat")
        self.max_retries = max_retries or self._get_config_value('retries.max_attempts', 3)
        
        # Store factory reference
        self.factory = factory
        if not factory:
            # Create factory if not provided
            from .factory.agent_factory import AgentFactory
            self.factory = AgentFactory.get_instance()
            
        # Add built-in chat tool to factory
        self.factory.create_tool(
            name="chat",
            description="Respond to general queries and conversation",
            func=lambda message: message
        )
        
        # Initialize parser
        self.parser = None
        if config and "parsing" in config:
            try:
                from utility.parser_factory import create_parser
                self.parser = create_parser(config, self.tools)
                logger.debug("Parser initialized from configuration")
            except ImportError:
                logger.warning("Parser factory not available, using default parsing")
        
        # Initialize history
        self.history: List[Union[ToolCallResult, ToolCallError]] = []
    
    def _get_config_value(self, key_path: str, default: Any) -> Any:
        """
        Get a value from the configuration by dot-separated key path.
        
        Args:
            key_path: Dot-separated path to the configuration value
            default: Default value if not found in configuration
            
        Returns:
            Configuration value or default
        """
        if not self.config:
            return default
            
        try:
            from utility.config_loader import get_config_value
            return get_config_value(self.config, key_path, default)
        except ImportError:
            # Manual implementation if config_loader is not available
            parts = key_path.split('.')
            value = self.config
            
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
                    
            return value
    
    def get_available_tools(self) -> List[Tool]:
        """Get list of available tools from factory."""
        return list(self.factory._tools.values())
    
    def format_tools_for_prompt(self) -> str:
        """Format tools into documentation for the LLM prompt."""
        tools_desc = []
        for tool in self.get_available_tools():
            params = [f"{k}: {v}" for k, v in tool.parameters.items()]
            param_desc = ", ".join(params)
            json_example = {
                "tool": tool.name,
                "arguments": {k: f"<{v}_value>" for k, v in tool.parameters.items()}
            }
            tools_desc.append(
                f"- {tool.name}({param_desc})\n"
                f"  Description: {tool.description}\n"
                f"  JSON Example: {json.dumps(json_example, indent=2)}"
            )
        return "\n\n".join(tools_desc)
    
    def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool with error handling and history tracking."""
        try:
            # Execute tool through factory
            result = self.factory.execute_tool(tool_name, **arguments)
            
            # Log successful tool call
            self.history.append(cast(ToolCallResult, {
                "tool": tool_name,
                "args": arguments,
                "result": result,
                "success": True,
                "timestamp": time.time()
            }))
            
            return result
            
        except Exception as e:
            # Log failed tool call
            self.history.append(cast(ToolCallError, {
                "tool": tool_name,
                "args": arguments,
                "error": str(e),
                "success": False,
                "timestamp": time.time()
            }))
            raise
    
    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the LLM based on configuration.
        
        Returns:
            System prompt to send to the LLM
        """
        # Check if we're in strict JSON mode
        # need to improve this 
        strict_json = self._get_config_value('parsing.strict_json', False)
        
        if strict_json:
            # Strict JSON prompt
            return f"""You are a helpful AI assistant that uses tools to accomplish tasks.

Available tools:
{self.format_tools_for_prompt()}

For any query, respond with a JSON object:
{{
    "tool": "tool_name",
    "arguments": {{
        "param1": value1,
        "param2": "string_value"
    }}
}}

Rules:
1. Response MUST be a single valid JSON object.
2. Include ONLY the JSON object, no additional text or markdown.
3. Use "chat" tool with a "message" argument for general responses.
4. String values must be in quotes; numbers must not.
"""
        else:
            # Flexible parsing prompt
            return f"""You are a helpful AI assistant that uses tools to accomplish tasks.

Available tools:
{self.format_tools_for_prompt()}

For tool-related queries, you MUST respond with a JSON object:
{{
    "tool": "tool_name",
    "arguments": {{
        "param1": value1,
        "param2": "string_value"
    }}
}}

For general queries or when no tool is appropriate, respond with:
{{"tool": "chat", "arguments": {{"message": "Your helpful response here"}}}}

RESPONSE RULES:
1. Response MUST be valid JSON
2. String values must be in quotes
3. Numbers should be raw (no quotes)
4. All required parameters must be included
5. No additional text outside the JSON structure

FALLBACK FORMAT (only if you can't use JSON):
tool_name(param1="value", param2=42)

Examples:
Query: "Add 5 and 3"
Response: {{"tool": "calculator", "arguments": {{"a": 5, "b": 3}}}}

Query: "Hello, how are you?"
Response: {{"tool": "chat", "arguments": {{"message": "Hello! I'm here to assist you."}}}}
"""

    def _build_retry_prompt(self) -> str:
        """
        Build a stricter system prompt for retry attempts.
        
        Returns:
            System prompt to send to the LLM on retry
        """
        return f"""Your previous response was invalid. Respond with ONLY a valid JSON object:
{{
    "tool": "tool_name",
    "arguments": {{
        "param1": value1,
        "param2": "string_value"
    }}
}}

Available tools:
{self.format_tools_for_prompt()}

CRITICAL:
- Include ONLY the JSON object.
- No explanations, markdown, or extra text.
- Use "chat" tool with "message" if no specific tool applies.
"""

    def _parse_response(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Parse LLM response to extract JSON object.
        
        If the parser is available, this uses the configured parser.
        Otherwise, uses the robust_json_parse utility with fallback strategies.
        
        Args:
            content: LLM response content
            
        Returns:
            Dict containing parsed JSON or None if parsing fails
        """
        # Use the configured parser if available
        if self.parser:
            return self.parser.parse(content)
        
        # Use the robust JSON parser with fallback strategies
        try:
            # Import here to avoid circular imports
            from .utils.json_parser import robust_json_parse, extract_json_debug_info
            
            # Define expected keys for validation
            expected_keys = ["tool", "arguments"]
            
            # Enable verbose mode based on configuration
            verbose = self._get_config_value('parsing.verbose', False)
            
            # Use the robust parser with all strategies
            result = robust_json_parse(content, expected_keys, verbose)
            
            # Validate structure if we got a result
            if result and self._validate_parsed_data(result):
                return result
                
            # If parsing failed, log debug information
            if verbose and not result:
                debug_info = extract_json_debug_info(content)
                logger.warning(f"JSON parsing failed: {debug_info['identified_issues']}")
                
            return None
            
        except ImportError:
            # Fall back to basic parsing if the json_parser module is unavailable
            logger.warning("Robust JSON parser not available, using basic parsing")
            
            # Fix common syntax errors in JSON (missing commas between fields)
            fixed_content = content
            if '{' in content and '}' in content:
                # Extract the JSON-like part
                json_match = re.search(r'({[\s\S]*})', content)
                if json_match:
                    json_part = json_match.group(1)
                    # Add missing commas between fields
                    fixed_json = re.sub(r'"\s+"', '", "', json_part)
                    fixed_content = content.replace(json_part, fixed_json)
            
            # Basic regex extraction
            json_match = re.search(r'({[\s\S]*})', fixed_content)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    if self._validate_parsed_data(data):
                        return data
                except json.JSONDecodeError:
                    # Try again with more aggressive fixing
                    try:
                        extracted_json = json_match.group(1)
                        # Add missing commas between key-value pairs
                        fixed_json = re.sub(r'"\s+("?\w+"\s*:)', '", \1', extracted_json)
                        data = json.loads(fixed_json)
                        if self._validate_parsed_data(data):
                            return data
                    except (json.JSONDecodeError, Exception):
                        pass
            
            # Try parsing entire content as JSON
            try:
                data = json.loads(fixed_content)
                if self._validate_parsed_data(data):
                    return data
            except json.JSONDecodeError:
                pass
                
            # Last resort: Try to extract fields directly with regex
            try:
                if "assessment" in content:
                    # Extract fields with regex for orchestrator format
                    assessment_match = re.search(r'"assessment"\s*:\s*"([^"]+)"', content)
                    requires_new_agent_match = re.search(r'"requires_new_agent"\s*:\s*(true|false)', content)
                    agent_id_match = re.search(r'"agent_id"\s*:\s*([^,}\s]+)', content)
                    
                    if assessment_match and requires_new_agent_match:
                        # Construct a minimal valid dict
                        data = {
                            "assessment": assessment_match.group(1),
                            "requires_new_agent": requires_new_agent_match.group(1).lower() == "true"
                        }
                        
                        if agent_id_match:
                            agent_id = agent_id_match.group(1)
                            if agent_id.lower() == "null":
                                data["agent_id"] = None
                            else:
                                data["agent_id"] = agent_id.strip('"')
                        
                        return data
            except Exception as e:
                logger.warning(f"Failed to extract fields from malformed JSON: {str(e)}")
            
            return None

    def _validate_parsed_data(self, data: Any) -> bool:
        """
        Validate that parsed data matches expected structure.
        
        Args:
            data: Data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        if not isinstance(data, dict):
            return False
        
        # Accept orchestrator assessment format
        if "assessment" in data and "requires_new_agent" in data:
            return True
        
        # Original tool execution format validation
        if "tool" not in data or "arguments" not in data:
            return False
        
        if not isinstance(data["tool"], str) or not isinstance(data["arguments"], dict):
            return False
        
        return True
    
    def run(self, query: str, template_path: Optional[str] = None, variables: Optional[Dict[str, Any]] = None) -> Any:
        """
        Run the Agent with a query and robust parsing.
        
        Args:
            query: The user query to process
            template_path: Optional path to a prompt template file
            variables: Optional variables to substitute in the template
            
        Returns:
            Any: The result from the executed tool
            
        Raises:
            AgentRetryExceeded: If the maximum number of retries is exceeded
        """
        if not self.get_available_tools():
            logger.warning("No tools available for execution")
            return "No tools available"
        
        system_prompt = self._build_system_prompt()
        retry_history = []
        
        # Process template if provided
        user_prompt = query
        if template_path:
            template_content = self._load_prompt_template(template_path)
            if template_content:
                # Combine variables from the arguments with a special "query" variable
                all_vars = variables.copy() if variables else {}
                all_vars["query"] = query  # Allow referencing the original query in the template
                
                # Add tools list if the template contains {{tools}} placeholder
                if "{{tools}}" in template_content:
                    all_vars["tools"] = self.format_tools_for_prompt()
                
                # Process the template with variables
                processed_template = self._process_prompt_template(template_content, all_vars)
                
                # Simply use the processed template as the system prompt
                system_prompt = processed_template
                
                # Add debug info to verify template is being used
                print(f"DEBUG: Using template: {template_path}")
                print(f"DEBUG: System prompt from template (first 100 chars): {system_prompt[:100]}...")
        
        # Initialize OpenAI client with OpenRouter configuration
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1}: Calling LLM with {self.model}")
                completion = client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": "https://tinyagent.dev",
                    },
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                )
                
                if not completion.choices:
                    error_msg = f"Attempt {attempt + 1}: Invalid response format - no choices returned"
                    logger.error(error_msg)
                    retry_history.append({"attempt": attempt + 1, "error": error_msg})
                    continue
                
                content = completion.choices[0].message.content
                parsed = self._parse_response(content)
                
                if parsed and self._validate_parsed_data(parsed):
                    tool_name, tool_args = parsed['tool'], parsed['arguments']
                    logger.info(f"Selected tool: {tool_name}")
                    try:
                        return self.execute_tool_call(tool_name, tool_args)
                    except Exception as e:
                        error_msg = f"Error executing tool: {str(e)}"
                        logger.error(error_msg)
                        retry_history.append({"attempt": attempt + 1, "error": error_msg})
                        
                        if attempt == self.max_retries - 1:
                            # If this is the last attempt and tool execution failed,
                            # track the error but don't stop retrying yet
                            pass
                else:
                    error_msg = f"Attempt {attempt + 1}: Invalid response format - {content[:100]}..."
                    logger.error(error_msg)
                    retry_history.append({
                        "attempt": attempt + 1,
                        "error": error_msg,
                        "raw_content": content[:200]  # Store first 200 chars of content for debugging
                    })
                
                if attempt < self.max_retries - 1:
                    system_prompt = self._build_retry_prompt()
                    
            except Exception as e:
                error_msg = f"Attempt {attempt + 1} failed: {str(e)}"
                logger.error(error_msg)
                retry_history.append({"attempt": attempt + 1, "error": error_msg})
                
                if attempt == self.max_retries - 1:
                    # Track the error but continue to our final error handling
                    pass
        
        # If we've exhausted all retries, create a fallback result and raise exception
        fallback_result = self.execute_tool_call("chat", {
            "message": "I couldn't understand how to process your request. Could you please rephrase it?"
        })
        
        # Raise exception with retry history
        raise AgentRetryExceeded(
            f"Failed to get valid response after {self.max_retries} attempts",
            history=retry_history
        )
        
        # This return is unreachable but keeps old behavior for backward compatibility if exception is caught
        return fallback_result
        
    def _load_prompt_template(self, template_path: str) -> str:
        """
        Load a prompt template from a file or template name.
        
        Args:
            template_path: Path to the template file or template name in format {{name}}
            
        Returns:
            str: The template content
        """
        try:
            # Check if the template path is in the format {{template_name}}
            import re
            template_match = re.match(r'{{(\w+)}}', template_path)
            
            if template_match:
                # Extract the template name and resolve to a file path
                template_name = template_match.group(1)
                # Get project root directory
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                resolved_path = os.path.join(project_root, 'core', 'prompts', f'{template_name}.md')
                print(f"DEBUG: Resolving template '{template_name}' to path: {resolved_path}")
                logger.debug(f"Resolved template name '{template_name}' to path: {resolved_path}")
                
                # Verify the template file exists
                if os.path.exists(resolved_path):
                    template_path = resolved_path
                    print(f"DEBUG: Template file exists at: {template_path}")
                else:
                    print(f"WARNING: Template file not found at: {resolved_path}")
                    logger.warning(f"Template file not found at: {resolved_path}")
            
            # Continue with existing file loading logic
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt template: {str(e)}")
            # Return an empty template in case of errors
            return ""

    def _process_prompt_template(self, template: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """
        Process a prompt template by replacing variables with their values.
        
        Variables in the template should be in the format {{variable_name}}.
        
        Args:
            template: The template string
            variables: Dictionary of variable names and their values
            
        Returns:
            str: The processed template with variables replaced
        """
        if not variables:
            return template
            
        import string
        
        # Create a template with Python's string.Template
        template_obj = string.Template(template.replace("{{", "${").replace("}}", "}"))
        
        # Replace variables using safe_substitute to avoid KeyError for missing variables
        return template_obj.safe_substitute(variables)


def get_llm(model: Optional[str] = None) -> Callable[[str], str]:
    """
    Get a callable LLM instance that can be used by other modules.
    
    Args:
        model: Optional model name to use
        
    Returns:
        A callable function that takes a prompt string and returns a response string
        
    Raises:
        ConfigurationError: If API key is missing
    """
    # Try to load environment variables from project root
    try:
        from dotenv import load_dotenv
        # Get project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(project_root, '.env')
        load_dotenv(env_path)
        logger.debug(f"Loaded environment variables from {env_path}")
    except ImportError:
        logger.warning("python-dotenv not available, skipping .env loading")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ConfigurationError("OPENROUTER_API_KEY must be set in .env")
    
    # Get model from config or use default
    if model is None:
        try:
            from core.config import load_config, get_config_value
            config = load_config()
            if config:
                model = get_config_value(config, 'model.default', "deepseek/deepseek-chat")
            else:
                model = "deepseek/deepseek-chat"
        except ImportError:
            model = "deepseek/deepseek-chat"
    
    # Initialize OpenAI client with OpenRouter configuration
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    def llm_call(prompt: str) -> str:
        """Call the LLM with a prompt and return the response."""
        try:
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://tinyagent.dev",
                },
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling LLM: {str(e)}")
            return f"Error: {str(e)}"
    
    return llm_call
