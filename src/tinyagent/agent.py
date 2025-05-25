"""
Agent implementation for the tinyAgent framework.

This module provides the Agent class, which is the central component of the
tinyAgent framework. The Agent uses a language model to select and execute
tools based on user queries.
"""
import os
import json
import requests
import re
from tinyagent.utils.openrouter_request import build_openrouter_payload, make_openrouter_request
from tinyagent.utils.structured_outputs import parse_strict_response
import time
from typing import List, Dict, Any, Optional, Union, Callable, TypeVar, cast, Tuple, Type
from datetime import datetime, timedelta
import hashlib
import logging
from openai import OpenAI
from .exceptions import AgentRetryExceeded, ConfigurationError, ParsingError
from .tool import Tool
from .utils.type_converter import convert_to_expected_type

# --- ADDED IMPORTS for Tracing ---
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from .observability.tracer import get_tracer, trace_agent_run

# ----------------------------------

def get_choices(completion):
    if isinstance(completion, dict):
        return completion.get("choices", [])
    else:
        return getattr(completion, "choices", [])
from .logging import get_logger
from .prompts.prompt_manager import PromptManager


#We can move this to utils probbaly
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


class CacheEntry(Dict[str, Any]):
    """Type definition for a cache entry."""
    result: Any
    timestamp: float
    tool: str
    args: Dict[str, Any]

# this is the class that handles the retrys, gets the from the config file
class RetryManager:
    """Manages the retry strategy with temperature warming and model escalation."""
    
    def __init__(self, config: Dict[str, Any], agent_default_model: str):
        self.config = config
        self.agent_default_model = agent_default_model
        self.current_attempt = 0
        self.temperature = self._get_config_value('retries.temperature.initial', 0.2)
        self.max_temperature = self._get_config_value('retries.temperature.max', 0.8)
        self.temp_increment = self._get_config_value('retries.temperature.increment', 0.2)
        self.model_sequence = self._get_config_value('retries.model_escalation.sequence', [
            "deepseek/deepseek-chat",
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3.7-sonnet"
        ])
        self.current_model_idx = -1
        
    def _get_config_value(self, path: str, default: Any) -> Any:
        """Get a value from nested config using dot notation."""
        parts = path.split('.')
        current = self.config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current
        
    def next_attempt(self) -> Tuple[float, str]:
        """Get parameters for next retry attempt."""
        self.current_attempt += 1
        
        model_to_use = ""
        if self.current_attempt == 1:
            model_to_use = self.agent_default_model
            logger.debug(f"RetryManager: Attempt 1, using default model: {model_to_use}")
        else:
            # Only escalate if the sequence has more models
            if (self.current_attempt - 1) % 3 == 0 and self.current_attempt > 1: 
                 # Indent the following block correctly
                 self.current_model_idx = min(self.current_model_idx + 1, len(self.model_sequence) - 1)
                 # Reset temperature when escalating
                 self.temperature = self._get_config_value('retries.temperature.initial', 0.2)
                 logger.debug(f"RetryManager: Escalating model index to {self.current_model_idx}")

            # Ensure index is valid for the sequence
            effective_model_idx = max(0, self.current_model_idx) # Use index 0 if initial index was -1

            if effective_model_idx < len(self.model_sequence):
                 model_to_use = self.model_sequence[effective_model_idx]
                 logger.debug(f"RetryManager: Attempt {self.current_attempt}, using escalation sequence index {effective_model_idx}: {model_to_use}")
            else:
                 model_to_use = self.model_sequence[-1]
                 logger.warning(f"RetryManager: Attempt {self.current_attempt}, index out of bounds, using last model: {model_to_use}")

            if self.current_attempt > 1 and self.current_attempt % 2 == 0:
                 self.temperature = min(self.temperature + self.temp_increment, self.max_temperature)
                 logger.debug(f"RetryManager: Increasing temperature to {self.temperature}")
                 
        return self.temperature, model_to_use
        
    def should_retry(self) -> bool:
        """Determine if another retry attempt should be made."""
        max_attempts = self._get_config_value('retries.max_attempts', 3)
        return self.current_attempt < max_attempts


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
    ENV_API_KEY = "OPENROUTER_API_KEY"
    CACHE_TTL = 3600  # 1 hour in seconds
    MAX_CACHE_SIZE = 1000
    
    def __init__(
        self,
        model: Optional[str] = None,
        max_retries: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize an Agent with tools, model, and configuration.
        
        Args:
            model: Language model identifier (e.g., "deepseek/deepseek-chat")
            max_retries: Maximum number of retries for failed LLM calls
            config: Optional configuration dictionary
            
        Raises:
            ConfigurationError: If required configuration is missing
        """
        # Store configuration
        if config is None:
            from tinyagent.config import load_config
            self.config = load_config()
        else:
            self.config = config
        
        # Try to load environment variables from project root
        project_root = None
        try:
            from dotenv import load_dotenv
            env_path = os.getenv("TINYAGENT_ENV")
            if not env_path:
                cwd_env = os.getenv(os.path.join(os.getcwd(), '.env'))
                if cwd_env:
                    env_path = cwd_env
                else:
                    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    env_path = os.path.join(project_root, '.env')
            load_dotenv(env_path)
            logger.debug(f"Loaded environment variables from {env_path}")
        except ImportError:
            logger.warning("python-dotenv not available, skipping .env loading")
            project_root = None
        
        # Get API key
        self.api_key = os.getenv(self.ENV_API_KEY)
        if not self.api_key:
            raise ConfigurationError(
                f"API key not found. The {self.ENV_API_KEY} environment variable must be set in .env file."
            )
            
        # Set model and max_retries from config or defaults
        self.model = model or self._get_config_value('model.default', "deepseek/deepseek-chat")
        self.max_retries = max_retries or self._get_config_value('retries.max_attempts', 3)
        
        # GOOD: Explicitly check and fail if not configured
        if not self.config or 'base_url' not in self.config:
            raise ConfigurationError("base_url must be set in config.yml")
        self.base_url = self.config['base_url']
        
        # Configure logging based on config
        log_level = self._get_config_value('logging.level', 'WARNING').upper()
        log_format = self._get_config_value('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Configure root logger with formatting
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Remove existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # Add console handler with formatting
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        formatter = logging.Formatter(log_format)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Log configuration using structured logging with  formatting
        logger.info("\n" + "="*50)
        logger.info("Agent Configuration")
        logger.info("="*50)
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Model: {self.model}")
        logger.info(f"Log Level: {log_level}")
        logger.info("="*50 + "\n")
        
        # Initialize tools dictionary
        self._tools: Dict[str, Tool] = {}
        
        # Add built-in chat tool
        self.create_tool(
            name="chat",
            description="Respond to general queries and conversation. Always requires a message parameter.",
            func=lambda **kwargs: kwargs["message"] if kwargs.get("message") else "I apologize, but I need a message to respond to.",
            parameters={"message": "The message or response to be sent"}
        )
        
        # Initialize parser
        self.parser = None
        if config and "parsing" in config:
            try:
                from .utils.json_parser import create_parser
                self.parser = create_parser(config, self._tools)
                logger.debug("Parser initialized from core.utils.parser")
            except Exception as e:
                logger.warning(f"Failed to initialize parser: {str(e)}")
                logger.warning("Using default parsing behavior")
        
        # Initialize history
        self.history: List[Union[ToolCallResult, ToolCallError]] = []
        
        # Add cache initialization
        self._cache: Dict[str, CacheEntry] = {}
        
        # Initialize prompt manager with project root for development mode
        self.prompt_manager = PromptManager(project_root=project_root)
        
        # Initialize retry manager, passing the actual default model
        self.retry_manager = RetryManager(self.config, agent_default_model=self.model)
    
    # move to the utils directory    
    def create_tool(self, name: str, description: str, func: Callable, parameters: Optional[Dict[str, str]] = None) -> None:
        """Create and register a new tool."""
        if name in self._tools:
            logger.debug(f"Tool {name} already exists, updating with new function and parameters")
            # Update existing tool instead of raising error
            tool = Tool(
                name=name,
                description=description,
                func=func,
                parameters=parameters or {}
            )
            self._tools[name] = tool
            return
            
        tool = Tool(
            name=name,
            description=description,
            func=func,
            parameters=parameters or {}
        )
        self._tools[name] = tool
        
    def get_available_tools(self) -> List[Tool]:
        """Get list of available tools."""
        return list(self._tools.values())
        
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool by name with given arguments."""
        if tool_name not in self._tools:
            raise ValueError(f"Tool {tool_name} not found")
            
        tool = self._tools[tool_name]
        # Call the tool directly as a callable, not using an 'execute' method
        return tool.func(**kwargs)
    
    # move to the utils directory, check the rest of the codebase for config logic 
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
            from tinyagent.config import get_config_value
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
    
    def _generate_cache_key(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Generate a unique cache key from tool name and arguments."""
        # Create a deterministic string representation of arguments
        args_str = json.dumps(arguments, sort_keys=True)
        # Combine tool name and arguments
        key_content = f"{tool_name}:{args_str}"
        # Create a hash of the content
        return hashlib.md5(key_content.encode()).hexdigest()

    # move to the utils directory, check the rest of the codebase for cache logic 
    def _cleanup_cache(self) -> None:
        """Remove expired entries and enforce size limit."""
        current_time = time.time()
        
        # Remove expired entries
        expired_keys = [
            key for key, entry in self._cache.items()
            if current_time - entry['timestamp'] > self.CACHE_TTL
        ]
        for key in expired_keys:
            del self._cache[key]

        # If still over size limit, remove oldest entries
        if len(self._cache) > self.MAX_CACHE_SIZE:
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            excess_count = len(self._cache) - self.MAX_CACHE_SIZE
            for key, _ in sorted_entries[:excess_count]:
                del self._cache[key]

    def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool with caching, error handling and history tracking."""
        # Generate cache key
        cache_key = self._generate_cache_key(tool_name, arguments)
        
        # Clean up cache before checking
        self._cleanup_cache()
        
        # Check cache for existing result
        if cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            # Verify entry hasn't expired
            if time.time() - cache_entry['timestamp'] <= self.CACHE_TTL:
                logger.info("\n" + "="*50)
                logger.info("Cache Hit")
                logger.info("="*50)
                logger.info(f"Tool: {tool_name}")
                logger.info(f"Arguments: {arguments}")
                logger.info(f"Cached Result: {cache_entry['result']}")
                logger.info("="*50 + "\n")
                
                return cache_entry['result']
        
        try:
            logger.info("\n" + "="*50)
            logger.info("Tool Execution (Cache Miss)")
            logger.info("="*50)
            logger.info(f"Tool: {tool_name}")
            logger.info(f"Arguments: {arguments}")
            logger.info("="*50 + "\n")
            
            # Execute tool directly
            result = self.execute_tool(tool_name, **arguments)
            
            logger.info("\n" + "="*50)
            logger.info("Execution Results")
            logger.info("="*50)
            logger.info(f"Tool: {tool_name}")
            logger.info(f"Result: {result}")
            logger.info(f"Status: Success")
            logger.info("="*50 + "\n")
            
            # Cache the successful result
            self._cache[cache_key] = {
                'result': result,
                'timestamp': time.time(),
                'tool': tool_name,
                'args': arguments
            }
            
            # Log successful tool call to history
            self.history.append(cast(ToolCallResult, {
                "tool": tool_name,
                "args": arguments,
                "result": result,
                "success": True,
                "timestamp": time.time()
            }))
            
            return result
            
        except Exception as e:
            logger.error("\n" + "="*50)
            logger.error(f"Tool: {tool_name}")
            logger.error(f"Arguments: {arguments}")
            logger.error(f"Error: {str(e)}")
            logger.error("="*50 + "\n")
            
            # Log failed tool call to history
            self.history.append(cast(ToolCallError, {
                "tool": tool_name,
                "args": arguments,
                "error": str(e),
                "success": False,
                "timestamp": time.time()
            }))
            
            raise # Re-raise the exception
    
    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the LLM based on configuration.
        
        Returns:
            System prompt to send to the LLM
        """
        # Check if we're in strict JSON mode
        strict_json = self._get_config_value('parsing.strict_json', False)
        
        # Load appropriate template
        template_name = "strict_json" if strict_json else "agent"
        template = self.prompt_manager.load_template(f"system/{template_name}.md")
        
        # Process template with tools
        return self.prompt_manager.process_template(template, {
            "tools": self.format_tools_for_prompt()
        })
    
    def _build_retry_prompt(self) -> str:
        """
        Build a stricter system prompt for retry attempts.
        
        Returns:
            System prompt to send to the LLM on retry
        """
        # Load retry template
        template = self.prompt_manager.load_template("system/retry.md")
        
        # Process template with tools
        return self.prompt_manager.process_template(template, {
            "tools": self.format_tools_for_prompt()
        })
    
    # move parsing logic, to a new dir, move other parsion tools here as well 
    
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
        # First, try schema-enforced parsing if enabled
        if self.config.get("structured_outputs", False):
            parsed = parse_strict_response(content)
            if parsed is not None:
                logger.info("Successfully parsed schema-enforced JSON response.")
                return parsed
            else:
                logger.warning("Schema-enforced parsing failed, falling back to robust parser.")

        # Use the configured parser if available
        if self.parser:
            return self.parser.parse(content)
        
        # Use the robust JSON parser with fallback strategies
        from .utils.json_parser import robust_json_parse, extract_json_debug_info

        expected_keys = ["tool", "arguments"]
        verbose = self._get_config_value('parsing.verbose', False)

        result = robust_json_parse(content, expected_keys, verbose)

        if result and self._validate_parsed_data(result):
            return result

        if verbose and not result:
            debug_info = extract_json_debug_info(content)
            logger.warning(f"JSON parsing failed: {debug_info['identified_issues']}")

        return None
    # Moves this to the parsing directory  as well 
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
        
        # Accept orchestrator assessment format with more flexible validation
        if "assessment" in data:
            # For this format, only "assessment" is absolutely required
            # "requires_new_agent" can be inferred if missing
            if not isinstance(data["assessment"], str):
                return False
                
            # If requires_new_agent is present, it should be boolean
            if "requires_new_agent" in data and not isinstance(data["requires_new_agent"], bool):
                # Try to convert string "true"/"false" to boolean
                if isinstance(data["requires_new_agent"], str):
                    try:
                        data["requires_new_agent"] = data["requires_new_agent"].lower() == "true"
                    except:
                        return False
                else:
                    return False
            
            # If requires_new_agent is missing, set a default value
            if "requires_new_agent" not in data:
                data["requires_new_agent"] = data["assessment"] == "create_new"
                
            return True
        
        # Original tool execution format validation
        if "tool" in data:
            if not isinstance(data["tool"], str):
                return False
                
            # For tool format, arguments must be present and be a dict
            if "arguments" not in data:
                return False
                
            if not isinstance(data["arguments"], dict):
                # Try to convert string to dict if it looks like JSON
                if isinstance(data["arguments"], str):
                    try:
                        import json
                        data["arguments"] = json.loads(data["arguments"])
                    except:
                        return False
                else:
                    return False
                    
            return True
        
        return False
    
    def _is_tracing_enabled(self) -> bool:
        """Check if tracing is enabled."""
        return isinstance(self, TracedAgent)
    
    def run(self, query: str, template_path: Optional[str] = None, variables: Optional[Dict[str, Any]] = None, expected_type: Optional[type] = None) -> Any:
        """Run the Agent with enhanced retry mechanism and observability."""
        
        # Core agent logic without explicit tracing context
        logger.info("\n" + "="*50)
        logger.info("Agent Execution")
        logger.info("="*50 + "\n")
        
        retry_history = []
        final_result = None # Initialize final_result
        
        if not self.get_available_tools():
            logger.warning("No tools available for execution")
            raise ValueError("No tools available for execution")
        
        system_prompt = self._build_system_prompt()
        user_prompt = query
        
        self.retry_manager = RetryManager(self.config, agent_default_model=self.model)
        
        while self.retry_manager.should_retry():
            temperature, current_model = self.retry_manager.next_attempt()
            
            logger.debug(f"[Agent.run] Attempt {self.retry_manager.current_attempt} with model {current_model} and temperature {temperature}")
            client = OpenAI(base_url=self.base_url, api_key=self.api_key)
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
            payload = build_openrouter_payload(messages=messages, config=self.config, model=current_model, temperature=temperature)
            api_key = os.getenv("OPENROUTER_API_KEY")
            
            try:
                completion = make_openrouter_request(self.config, api_key, payload)
                logger.debug(f"[Agent.run] Raw completion: {repr(completion)}")
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP error occurred: {str(e)}"
                logger.warning(error_msg)
                retry_history.append({"attempt": self.retry_manager.current_attempt, "model": current_model, "temperature": temperature, "error": error_msg})
                
                # If this is the last retry attempt, raise AgentRetryExceeded instead of HTTPError
                if not self.retry_manager.should_retry():
                    raise AgentRetryExceeded(
                        f"Failed due to HTTP error after {self.retry_manager.current_attempt} attempts: {str(e)}", 
                        history=retry_history,
                        error_code=AgentRetryExceeded.ERROR_HTTP_ERROR
                    ) from e
                continue
            except Exception as e:
                error_msg = f"Error making API request: {str(e)}"
                logger.warning(error_msg)
                retry_history.append({"attempt": self.retry_manager.current_attempt, "model": current_model, "temperature": temperature, "error": error_msg})
                
                # If this is the last retry attempt, raise AgentRetryExceeded instead of the original exception
                if not self.retry_manager.should_retry():
                    raise AgentRetryExceeded(
                        f"Failed due to error after {self.retry_manager.current_attempt} attempts: {str(e)}", 
                        history=retry_history,
                        error_code=AgentRetryExceeded.ERROR_API_REQUEST
                    ) from e
                continue
            
            if not get_choices(completion):
                error_msg = f"Invalid response format - no choices returned"
                logger.debug(f"[Agent.run] {error_msg}")
                retry_history.append({"attempt": self.retry_manager.current_attempt, "model": current_model, "temperature": temperature, "error": error_msg})
                continue
            
            choices = get_choices(completion)
            content = choices[0].message.content if hasattr(choices[0], "message") else choices[0]["message"]["content"]
            logger.debug(f"[Agent.run] Raw LLM content: {repr(content)}")
            parsed = self._parse_response(content)
            logger.debug(f"[Agent.run] Parsed response: {repr(parsed)}")
            
            logger.info(f"Raw LLM response: {content[:500]}")
            if parsed: logger.info(f"Parsed response: {parsed}")
            
            if parsed and self._validate_parsed_data(parsed):
                # Prioritize checking for tool call format
                if "tool" in parsed and "arguments" in parsed:
                    logger.info(f"Successfully parsed tool execution format: {parsed}")
                    tool_name, tool_args = parsed['tool'], parsed['arguments']
                    
                    # Don't allow fallback to chat tool
                    if tool_name == "chat" and tool_name not in query.lower():
                        error_msg = "No valid tool found for query"
                        logger.warning(error_msg)
                        retry_history.append({"attempt": self.retry_manager.current_attempt, "model": current_model, "temperature": temperature, "error": error_msg})
                        continue
                    
                    # Execute the tool call
                    try:
                        result = self.execute_tool_call(tool_name, tool_args)
                        logger.info("\n" + "="*50); logger.info(f"Task completed. Final answer: {result}"); logger.info("="*50 + "\n")
                        # Convert and store the actual execution result
                        final_result = convert_to_expected_type(result, expected_type, logger)
                        break # Exit retry loop on successful tool execution
                    except Exception as e:
                        error_msg = f"Tool execution failed: {str(e)}"
                        logger.warning(error_msg)
                        retry_history.append({"attempt": self.retry_manager.current_attempt, "model": current_model, "temperature": temperature, "error": error_msg})
                        continue

                # Check for other formats like assessment *after* tool call
                elif "assessment" in parsed:
                    logger.info(f"Successfully parsed assessment format: {parsed}")
                    logger.info("\n" + "="*50); logger.info(f"Task completed. Final answer: {parsed}"); logger.info("="*50 + "\n")
                    # Store the parsed assessment dictionary as the result
                    final_result = parsed
                    break # Exit retry loop on successful assessment parsing
                else:
                    # Handle other potential valid parsed formats if necessary, or log unexpected structure
                    logger.warning(f"Parsed data has unexpected structure: {parsed}")
                    # Decide if this should be an error or fallback
                    # For now, let's treat it as needing retry
                    error_msg = f"Parsed data validated but structure not recognized: {parsed}"
                    retry_history.append({"attempt": self.retry_manager.current_attempt, "model": current_model, "temperature": temperature, "error": error_msg, "raw_content": content[:200]})
                    system_prompt = self._build_retry_prompt()
                    continue # Continue to next retry attempt
            
            else:
                error_msg = f"Invalid or empty response format - {content[:100]}..."
                logger.debug(f"[Agent.run] {error_msg}")
                retry_history.append({"attempt": self.retry_manager.current_attempt, "model": current_model, "temperature": temperature, "error": error_msg, "raw_content": content[:200]})
                system_prompt = self._build_retry_prompt()
            
        # If loop finishes without breaking (i.e., no success)
        else: # Corresponds to the while loop
            logger.error(f"Agent failed after {self.retry_manager.current_attempt} attempts.")
            # Determine most appropriate error code from history
            error_code = None
            # The error code will be automatically determined from history
            # Raise outside the loop. Decorator will catch this exception if applied.
            raise AgentRetryExceeded(
                f"Failed to get valid response after {self.retry_manager.current_attempt} attempts", 
                history=retry_history
            )

        # Return the final result obtained before loop exit
        return final_result

# --- ADDED TracedAgent Subclass ---
class TracedAgent(Agent):
    """An Agent subclass whose run method is automatically traced."""
    
    @trace_agent_run # Apply decorator ONLY to the subclass run method
    def run(self, query: str, template_path: Optional[str] = None, variables: Optional[Dict[str, Any]] = None, expected_type: Optional[type] = None) -> Any:
        """Overrides Agent.run to apply tracing via decorator and calls the parent implementation."""
        # The decorator handles the span, the actual logic is in the parent
        return super().run(query, template_path=template_path, variables=variables, expected_type=expected_type)
        
    # --- ADDED: Override execute_tool_call to add tracing for TracedAgent --- 
    def execute_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Overrides base method to add tracing specifically for tool calls in TracedAgent."""
        tracer = get_tracer(__name__) # Get tracer instance
        
        # Ensure arguments are JSON serializable for attributes
        try:
            args_json = json.dumps(arguments)
        except TypeError:
            args_json = json.dumps(str(arguments)) # Fallback

        # Start the tool execution span
        with tracer.start_as_current_span(f"tool.execute.{tool_name}") as tool_span:
            tool_span.set_attribute("tool.name", tool_name)
            tool_span.set_attribute("tool.arguments", args_json)
            
            result = None # Initialize result
            try:
                # Call the original Agent.execute_tool_call logic from the base class
                result = super().execute_tool_call(tool_name, arguments)
                
                # Record successful result and status
                tool_span.set_attribute("tool.result", str(result))
                tool_span.set_status(Status(StatusCode.OK))
                
                return result
            except Exception as e:
                # Record exception and error status
                tool_span.record_exception(e)
                tool_span.set_status(Status(StatusCode.ERROR, f"Tool execution failed: {str(e)}"))
                raise # Re-raise the exception
    # --- END OVERRIDE --- 

# --- END Subclass ---

def get_llm(model: Optional[str] = None) -> Callable[[str], str]:
    """
    Get a callable LLM instance that can be used by other modules.
    
    Args:
        model: Optional model name to use
        
    Returns:
        A callable function that takes a prompt string and returns a response string
        
    Raises:
        ConfigurationError: If API key is missing or if base_url is not configured
    """
    # Try to load environment variables from project root
    try:
        from dotenv import load_dotenv
        env_path = os.getenv("TINYAGENT_ENV")
        if not env_path:
            cwd_env = os.path.join(os.getcwd(), '.env')
            if os.path.isfile(cwd_env):
                env_path = cwd_env
            else:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                env_path = os.path.join(project_root, '.env')
        load_dotenv(env_path)
        logger.debug(f"Loaded environment variables from {env_path}")
    except ImportError:
        logger.warning("python-dotenv not available, skipping .env loading")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ConfigurationError("OPENROUTER_API_KEY must be set in .env")
    
    # Get model and base_url from config
    try:
        from tinyagent.config import load_config, get_config_value
        config = load_config()
        if not config:
            raise ConfigurationError("config.yml not found")
            
        if 'base_url' not in config:
            raise ConfigurationError("base_url must be set in config.yml")
            
        base_url = config['base_url']
        model = model or get_config_value(config, 'model.default', "deepseek/deepseek-chat")
            
    except ImportError:
        raise ConfigurationError("Failed to load configuration. Make sure config.yml exists and contains base_url")
    
    # Initialize OpenAI client with configuration
    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )
    
    def llm_call(prompt: str) -> str:
        """Call the LLM with a prompt and return the response."""
        try:
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://tinyagent.xyz",
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

def tiny_agent(tools=None, model=None, **kwargs):
    """
    Simplified alias to create an Agent using AgentFactory with given tools and optional model.
    """
    from .factory.agent_factory import AgentFactory
    return AgentFactory.get_instance().create_agent(tools=tools, model=model, **kwargs)
