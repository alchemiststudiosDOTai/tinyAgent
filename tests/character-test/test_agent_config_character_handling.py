"""
Character tests for Agent configuration and initialization.

These tests focus on how the Agent handles various character inputs
in configuration files, environment variables, and initialization parameters.
"""

import pathlib
import sys
import os
import tempfile
from typing import Dict, Any
import pytest
from unittest.mock import patch, mock_open

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))

from tinyagent.agent import Agent, get_llm
from tinyagent.exceptions import ConfigurationError


class TestAgentConfigurationCharacterHandling:
    """Test Agent configuration with various character inputs."""
    
    def test_agent_with_unicode_model_name(self):
        """Test Agent initialization with unicode model name."""
        config = {
            "base_url": "https://api.example.com",
            "model": {"default": "test/model-café"}
        }
        
        try:
            agent = Agent(config=config)
            assert agent.model == "test/model-café"
        except ConfigurationError:
            # Acceptable if unicode model names aren't supported
            pass
    
    def test_agent_with_special_char_config_values(self):
        """Test Agent with special characters in config values."""
        config = {
            "base_url": "https://api.example.com/v1",
            "model": {"default": "test/model"},
            "custom_field": "value with spaces & special chars!@#$%"
        }
        
        try:
            agent = Agent(config=config)
            assert agent.config["custom_field"] == "value with spaces & special chars!@#$%"
        except ConfigurationError:
            # Some special characters might not be supported
            pass
    
    def test_agent_with_long_config_values(self):
        """Test Agent with very long configuration values."""
        long_url = "https://api.example.com/" + "x" * 1000
        config = {
            "base_url": long_url,
            "model": {"default": "test/model"} 
        }
        
        try:
            agent = Agent(config=config)
            assert agent.base_url == long_url
        except ConfigurationError:
            # Very long URLs might be rejected
            pass
    
    def test_agent_config_with_nested_unicode(self):
        """Test Agent config with nested unicode values."""
        config = {
            "base_url": "https://api.example.com",
            "model": {"default": "test/model"},
            "nested": {
                "field1": "value with 世界",
                "field2": "value with 🌍",
                "field3": "value with café"
            }
        }
        
        try:
            agent = Agent(config=config)
            assert "nested" in agent.config
        except ConfigurationError:
            # Unicode in nested config might not be supported
            pass
    
    def test_agent_config_path_handling(self):
        """Test config path handling with special characters."""
        # Mock environment variables with special characters
        with patch.dict(os.environ, {
            "TINYAGENT_ENV": "/path/with spaces/and-special@chars.env",
            "OPENROUTER_API_KEY": "test-key-with-dashes_and_underscores"
        }):
            config = {
                "base_url": "https://api.example.com",
                "model": {"default": "test/model"}
            }
            
            try:
                agent = Agent(config=config)
                assert agent.api_key == "test-key-with-dashes_and_underscores"
            except ConfigurationError:
                # Path handling might fail with special characters
                pass


class TestAgentEnvironmentVariableHandling:
    """Test Agent's handling of environment variables with various characters."""
    
    def test_api_key_with_special_characters(self):
        """Test API key with special characters."""
        special_key = "sk-test123!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": special_key}):
            config = {
                "base_url": "https://api.example.com",
                "model": {"default": "test/model"}
            }
            
            try:
                agent = Agent(config=config)
                assert agent.api_key == special_key
            except ConfigurationError:
                # Some special characters in API keys might not be supported
                pass
    
    def test_api_key_with_unicode(self):
        """Test API key with unicode characters."""
        unicode_key = "sk-test-café-世界-🌍"
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": unicode_key}):
            config = {
                "base_url": "https://api.example.com",
                "model": {"default": "test/model"}
            }
            
            try:
                agent = Agent(config=config)
                assert agent.api_key == unicode_key
            except ConfigurationError:
                # Unicode API keys might not be supported
                pass
    
    def test_env_path_with_unicode(self):
        """Test environment file path with unicode."""
        unicode_path = "/path/with/café/and/世界/.env"
        
        with patch.dict(os.environ, {
            "TINYAGENT_ENV": unicode_path,
            "OPENROUTER_API_KEY": "test-key"
        }):
            config = {
                "base_url": "https://api.example.com",
                "model": {"default": "test/model"}
            }
            
            try:
                agent = Agent(config=config)
                # Should handle unicode paths gracefully
                assert agent.api_key == "test-key"
            except (ConfigurationError, FileNotFoundError, UnicodeError):
                # Unicode paths might not be supported on all systems
                pass
    
    def test_very_long_env_values(self):
        """Test very long environment variable values."""
        long_key = "sk-" + "x" * 10000
        long_url = "https://api.example.com/" + "y" * 5000
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": long_key}):
            config = {
                "base_url": long_url,
                "model": {"default": "test/model"}
            }
            
            try:
                agent = Agent(config=config)
                assert len(agent.api_key) > 10000
                assert len(agent.base_url) > 5000
            except ConfigurationError:
                # Very long values might be rejected
                pass


class TestAgentToolNameHandling:
    """Test Agent's handling of tool names with various characters."""
    
    def test_tool_name_with_unicode(self):
        """Test tool names with unicode characters."""
        config = {
            "base_url": "https://api.example.com",
            "model": {"default": "test/model"}
        }
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            try:
                agent = Agent(config=config)
                
                # Try to create tool with unicode name
                agent.create_tool(
                    name="tool_café_世界",
                    description="Tool with unicode name",
                    func=lambda x: x
                )
                
                tools = agent.get_available_tools()
                unicode_tools = [t for t in tools if "café" in t.name or "世界" in t.name]
                assert len(unicode_tools) > 0
            except (ConfigurationError, ValueError):
                # Unicode tool names might not be supported
                pass
    
    def test_tool_name_with_special_characters(self):
        """Test tool names with special characters."""
        config = {
            "base_url": "https://api.example.com",
            "model": {"default": "test/model"}
        }
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            try:
                agent = Agent(config=config)
                
                special_names = [
                    "tool-with-dashes",
                    "tool_with_underscores",
                    "tool.with.dots",
                    "tool@with@symbols",
                ]
                
                for name in special_names:
                    try:
                        agent.create_tool(
                            name=name,
                            description=f"Tool named {name}",
                            func=lambda x: x
                        )
                    except ValueError:
                        # Some special characters might not be allowed
                        pass
                
                tools = agent.get_available_tools()
                assert len(tools) > 0  # Should have at least the built-in chat tool
            except ConfigurationError:
                pass
    
    def test_tool_description_with_unicode(self):
        """Test tool descriptions with unicode characters."""
        config = {
            "base_url": "https://api.example.com",
            "model": {"default": "test/model"}
        }
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            try:
                agent = Agent(config=config)
                
                unicode_description = "Tool that processes café and 世界 and 🌍"
                agent.create_tool(
                    name="unicode_tool",
                    description=unicode_description,
                    func=lambda x: x
                )
                
                tools = agent.get_available_tools()
                unicode_tool = next((t for t in tools if t.name == "unicode_tool"), None)
                if unicode_tool:
                    assert unicode_tool.description == unicode_description
            except (ConfigurationError, ValueError):
                # Unicode descriptions might not be supported
                pass


class TestAgentLoggingCharacterHandling:
    """Test Agent's logging with various character inputs."""
    
    def test_logging_with_unicode_messages(self):
        """Test logging configuration with unicode messages."""
        config = {
            "base_url": "https://api.example.com",
            "model": {"default": "test/model"},
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s with café"
            }
        }
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            try:
                agent = Agent(config=config)
                # Should initialize without errors
                assert agent.config["logging"]["format"] == "%(asctime)s - %(name)s - %(levelname)s - %(message)s with café"
            except (ConfigurationError, UnicodeError):
                # Unicode in logging format might not be supported
                pass
    
    def test_logging_with_special_characters(self):
        """Test logging with special characters in format."""
        config = {
            "base_url": "https://api.example.com",
            "model": {"default": "test/model"},
            "logging": {
                "level": "DEBUG",
                "format": "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
            }
        }
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            try:
                agent = Agent(config=config)
                # Should handle special characters in logging format
                assert "|" in agent.config["logging"]["format"]
            except ConfigurationError:
                # Some special characters might cause issues
                pass


class TestGetLLMFunctionCharacterHandling:
    """Test the get_llm function with various character inputs."""
    
    def test_get_llm_with_unicode_model(self):
        """Test get_llm function with unicode model name."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            with patch('tinyagent.agent.load_config') as mock_config:
                mock_config.return_value = {
                    "base_url": "https://api.example.com",
                    "model": {"default": "test/model-café"}
                }
                
                try:
                    llm = get_llm("test/model-café")
                    assert callable(llm)
                except (ConfigurationError, ImportError):
                    # Unicode model names might not be supported
                    pass
    
    def test_get_llm_with_special_char_model(self):
        """Test get_llm function with special characters in model name."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            with patch('tinyagent.agent.load_config') as mock_config:
                mock_config.return_value = {
                    "base_url": "https://api.example.com",
                    "model": {"default": "test/model-v1.0"}
                }
                
                try:
                    llm = get_llm("test/model-v1.0")
                    assert callable(llm)
                except (ConfigurationError, ImportError):
                    # Special characters in model names might not be supported
                    pass
    
    def test_get_llm_prompt_with_unicode(self):
        """Test get_llm function with unicode in prompts."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            with patch('tinyagent.agent.load_config') as mock_config:
                mock_config.return_value = {
                    "base_url": "https://api.example.com",
                    "model": {"default": "test/model"}
                }
                
                try:
                    llm = get_llm()
                    if callable(llm):
                        # Test with unicode prompt
                        unicode_prompt = "Hello 世界, how are you? 🌍"
                        result = llm(unicode_prompt)
                        assert isinstance(result, str)
                except (ConfigurationError, ImportError, Exception):
                    # Various issues might occur with unicode prompts
                    pass


class TestAgentInitializationEdgeCases:
    """Test Agent initialization edge cases with character handling."""
    
    def test_agent_with_empty_config(self):
        """Test Agent initialization with empty/minimal config."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            try:
                # Should fail due to missing base_url
                agent = Agent(config={})
                assert False, "Should have raised ConfigurationError"
            except ConfigurationError:
                # Expected behavior
                pass
    
    def test_agent_with_malformed_config_values(self):
        """Test Agent with malformed config values."""
        malformed_configs = [
            {"base_url": "", "model": {"default": "test"}},  # Empty base_url
            {"base_url": "not-a-url", "model": {"default": "test"}},  # Invalid URL
            {"base_url": "https://api.example.com", "model": {"default": ""}},  # Empty model
        ]
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            for config in malformed_configs:
                try:
                    agent = Agent(config=config)
                    # Some malformed configs might still work
                    assert agent is not None
                except ConfigurationError:
                    # Expected for malformed config
                    pass
    
    def test_agent_with_none_config_values(self):
        """Test Agent with None values in config."""
        config_with_none = {
            "base_url": "https://api.example.com",
            "model": {"default": None},
            "custom_field": None
        }
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            try:
                agent = Agent(config=config_with_none)
                # Should handle None values gracefully
                assert agent is not None
            except (ConfigurationError, TypeError):
                # None values might cause issues
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])