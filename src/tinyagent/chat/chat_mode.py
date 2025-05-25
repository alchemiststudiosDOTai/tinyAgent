"""
Chat mode functionality for the tinyAgent framework.

This module provides a direct conversation interface with language models without
requiring tool selection. It handles conversation history, API communication,
and provides a simple CLI interface.
"""

from __future__ import annotations

import sys
import os
import time
import threading
import itertools
from typing import Optional, Final, Dict, Any, List
from datetime import datetime

from openai import OpenAI

from ..logging import get_logger
from ..config import load_config, get_config_value
from ..cli.colors import Colors
from ..exceptions import ConfigurationError

# Set up logger
logger = get_logger(__name__)

# Constants
ENV_API_KEY: Final[str] = "OPENROUTER_API_KEY"
DEFAULT_MODEL: Final[str] = "anthropic/claude-3.5-sonnet"
DEFAULT_SYSTEM_PROMPT: Final[str] = "You are a helpful AI assistant. Respond concisely and accurately to questions."
DEFAULT_BASE_URL: Final[str] = "https://openrouter.ai/v1"

class ChatSession:
    """
    Manages a conversation session with a language model.
    
    This class handles the conversation history, API communication,
    and message formatting for a chat session.
    
    Attributes:
        model: Name of the language model to use
        api_key: API key for authentication
        conversation: List of conversation messages with timestamps
    """
    
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        """
        Initialize a chat session with the specified model.
        
        Args:
            model: Name of the language model to use
            api_key: API key for authentication (if None, uses environment)
            
        Raises:
            ConfigurationError: If the API key is not set
        """
        # Try to load from config if available
        config_model = None
        try:
            config = load_config()
            if config:
                config_model = get_config_value(config, "model.default")
        except Exception as e:
            logger.warning(f"Error loading config: {e}")
        
        # Priority: 1. Explicitly provided model, 2. Config model, 3. Default
        self.model = model or config_model or DEFAULT_MODEL
        self.api_key = api_key or os.getenv(ENV_API_KEY)
        self.base_url = base_url or get_config_value(config, "base_url", DEFAULT_BASE_URL)
        
        if not self.api_key:
            raise ConfigurationError(f"{ENV_API_KEY} must be set in .env")
            
        self.conversation: list[dict[str, str]] = []  # Store conversation history
        logger.debug(f"Initialized chat session with model: {self.model}")
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            role: Message role ("system", "user", or "assistant")
            content: Message content
        """
        self.conversation.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        logger.debug(f"Added {role} message: {content[:50]}...")
    
    def get_response(self, prompt: str) -> str:
        """
        Get a response from the language model for the given prompt.
        
        This method sends the conversation history and the new prompt to the
        language model and retrieves a response.
        
        Args:
            prompt: User prompt to send to the model
            
        Returns:
            The model's response
            
        Raises:
            Exception: If there's an error communicating with the API
        """
        # Add user message to conversation
        self.add_message("user", prompt)
        
        # Log debug info about the model and conversation length
        logger.debug(
            f"Using model: {self.model} | History: {len(self.conversation)} messages"
        )
        print(
            f"\r{Colors.OFF_WHITE}Using model: {self.model} | "
            f"History: {len(self.conversation)} messages{Colors.RESET}",
            flush=True,
        )
        
        # Initialize spinner for loading feedback
        spinner = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
        
        # Create an event for stopping the spinner thread
        stop_event = threading.Event()
        
        def spin_animation() -> None:
            """Display a spinning animation while waiting for response."""
            while not stop_event.is_set():
                for frame in spinner:
                    sys.stdout.write(
                        f"\r{Colors.LIGHT_RED}{frame}{Colors.OFF_WHITE} "
                        f"Thinking...{Colors.RESET}"
                    )
                    sys.stdout.flush()
                    # Short sleep with frequent checks for the stop event
                    for _ in range(10):  # 10 * 0.01 = 0.1 seconds per frame
                        if stop_event.is_set():
                            break
                        time.sleep(0.01)
                    if stop_event.is_set():
                        break
            # Clear the line when stopped
            sys.stdout.write("\r" + " " * 50 + "\r")
            sys.stdout.flush()
        
        try:
            # Initialize OpenAI client with OpenRouter configuration
            client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
            )
            
            # Start spinner thread
            spinner_thread = threading.Thread(target=spin_animation)
            spinner_thread.daemon = True
            spinner_thread.start()
            
            try:
                # Make the API request with explicit timeout
                logger.debug(f"Sending request to {API_URL}")
                
                completion = client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": "https://tinyagent.dev",
                    },
                    model=self.model,
                    messages=self.conversation,
                    temperature=0.7,
                    max_tokens=2000,
                    timeout=60,
                )
                
                logger.debug("Received response from API")
                
                # Stop the spinner
                stop_event.set()
                spinner_thread.join(timeout=0.5)  # Wait for spinner to clean up
                
                # Extract assistant's response
                if completion.choices and len(completion.choices) > 0:
                    assistant_message = completion.choices[0].message.content
                    
                    # Check for empty response and provide fallback
                    if not assistant_message or assistant_message.strip() == "":
                        fallback_msg = (
                            "Sorry, I couldn't generate a response. "
                            "Let's try again with a different question."
                        )
                        logger.warning("Empty response received - using fallback")
                        # Add fallback message to conversation history
                        self.add_message("assistant", fallback_msg)
                        return fallback_msg
                    
                    # Add assistant response to conversation history
                    self.add_message("assistant", assistant_message)
                    return assistant_message or ""
                else:
                    # Extended debug output for troubleshooting
                    debug_msg = "Unexpected API response format: no valid choices found"
                    logger.warning(debug_msg)
                    # Create a fallback response that will be more useful than blank
                    fallback = "I'm having trouble processing your request. Please try asking a different question."
                    self.add_message("assistant", fallback)
                    return fallback
                    
            except Exception as e:
                # Make sure to stop the spinner on error
                stop_event.set()
                spinner_thread.join(timeout=0.5)
                raise e
            
        except Exception as e:
            # Enhanced error handling with more details and fallback response
            logger.error(f"Error in get_response: {type(e).__name__}: {str(e)}")
            if hasattr(e, "response") and hasattr(e.response, "text"):
                logger.error(f"API response: {e.response.text[:500]}...")
            
            # Provide a useful fallback response for the user
            fallback = "I'm experiencing technical difficulties. Please try again in a moment."
            # Add fallback to conversation history
            self.add_message("assistant", fallback)
            return fallback


def run_chat_mode(
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    base_url: Optional[str] = None,
) -> None:
    """
    Run the chat mode interface with the specified model.
    
    This function provides a simple CLI interface for chatting directly with
    a language model without using tools.
    
    Args:
        model: Name of the language model to use
        system_prompt: Optional system prompt to set the behavior of the model
    """
    # Print welcome message
    print(f"\n{Colors.OFF_WHITE}Welcome to tinyAgent Chat Mode!{Colors.RESET}")
    print(
        f"{Colors.OFF_WHITE}Type 'exit' or 'quit' to return to the main interface."
        f"{Colors.RESET}"
    )
    
    try:
        # Create chat session
        session = ChatSession(model=model, base_url=base_url)
        
        # Print the model being used (which could be from config)
        print(
            f"{Colors.OFF_WHITE}Using model: {session.model} "
            f"(from config.yml or default){Colors.RESET}"
        )
        
        # Add system prompt if provided
        if system_prompt:
            session.add_message("system", system_prompt)
        else:
            # Default system prompt
            session.add_message("system", DEFAULT_SYSTEM_PROMPT)
        
        # Main chat loop
        while True:
            # Get user input
            user_input = input(f"\n{Colors.LIGHT_RED}❯{Colors.OFF_WHITE} ")
            
            # Check for exit command
            if user_input.lower() in ["exit", "quit"]:
                print(f"\n{Colors.LIGHT_RED}Exiting chat mode.{Colors.RESET}")
                break
                
            # Get response from LLM
            response = session.get_response(user_input)
            
            # Print response
            print(f"\n{Colors.OFF_WHITE}{response}{Colors.RESET}")
            
    except KeyboardInterrupt:
        print(f"\n{Colors.LIGHT_RED}Chat mode interrupted. Exiting.{Colors.RESET}")
        logger.info("Chat mode interrupted by user")
    except Exception as e:
        error_msg = f"Error in chat mode: {str(e)}"
        print(f"\n{Colors.error(error_msg)}")
        logger.error(error_msg)
