"""
Dynamic agent factory for creating specialized agents on-the-fly.

This module provides an enhanced factory class that extends AgentFactory with
capabilities for dynamically creating specialized agents and tools based on
natural language requirements.
"""

import json
import re
from typing import Dict, List, Any, Optional, Callable, Union, TypeVar, Type, cast

from ..logging import get_logger
from ..config import load_config, get_config_value
from ..tool import Tool, ParamType
from ..agent import Agent, get_llm
from ..exceptions import ConfigurationError
from .agent_factory import AgentFactory

# Set up logger
logger = get_logger(__name__)

# Define a generic type variable for better type hints
T = TypeVar('T')


class DynamicAgentFactory(AgentFactory):
    """
    Enhanced factory for creating agents dynamically based on NLP analysis.
    
    This class extends AgentFactory with capabilities for dynamically creating
    specialized agents and tools based on natural language requirements.
    
    Attributes:
        _dynamic_agents: Dictionary of dynamically created agents
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls: Type[T], config: Optional[Dict[str, Any]] = None) -> T:
        """
        Get or create the singleton factory instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            The singleton DynamicAgentFactory instance
        """
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize with parent class and add dynamic capabilities.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self._dynamic_agents: Dict[str, Agent] = {}
        
        # Get dynamic agent configuration
        if self.config:
            max_agents = get_config_value(self.config, 'dynamic_agents.max_agents', 10)
            allow_new_tools = get_config_value(self.config, 'dynamic_agents.allow_new_tools_by_default', False)
            model = get_config_value(self.config, 'dynamic_agents.model', None)
            
            logger.debug(f"Dynamic agent config: max_agents={max_agents}, allow_new_tools={allow_new_tools}")
            
            self._max_agents = max_agents
            self._allow_new_tools = allow_new_tools
            self._model = model
        else:
            self._max_agents = 10
            self._allow_new_tools = False
            self._model = None
        
    def create_dynamic_agent(self, task_description: str, model: Optional[str] = None) -> Agent:
        """
        Create a specialized agent based on task description using NLP analysis.
        
        This method analyzes the task description to determine which tools are
        needed, then creates a specialized agent with those tools.
        
        Args:
            task_description: Description of the task to be performed
            model: Optional model to use for the agent
            
        Returns:
            A specialized agent with appropriate tools
        """
        # Use specified model or default from config
        model = model or self._model
        
        # Get LLM to analyze the task and determine required tools
        llm = get_llm(model)
        
        # Prompt to analyze the task
        analysis_prompt = f"""
        Analyze the following task description and determine which tools are needed:
        
        Task: {task_description}
        
        Available tools: {', '.join(self._tools.keys())}
        
        Return a JSON object with the required tools and explanation:
        {{
            "required_tools": ["tool1", "tool2", ...],
            "explanation": "Why these tools are needed"
        }}
        
        Keep your response minimal and focused only on the tools needed.
        """
        
        # Get analysis result
        analysis_result = llm(analysis_prompt)
        
        try:
            # Find JSON using regex
            json_match = re.search(r'({[\s\S]*})', analysis_result)
            if json_match:
                analysis = json.loads(json_match.group(1))
                required_tools = analysis.get("required_tools", [])
            else:
                required_tools = []
                logger.warning("Could not parse analysis result, using all tools")
                # If parsing fails, use all tools
                required_tools = list(self._tools.keys())
        except Exception as e:
            logger.error(f"Error parsing analysis result: {str(e)}")
            # If parsing fails, use all tools
            required_tools = list(self._tools.keys())
            
        # Get selected tools
        selected_tools = []
        for name in required_tools:
            if name in self._tools:
                selected_tools.append(self._tools[name])
        
        # Create the agent
        agent = self.create_agent(
            tools=selected_tools,
            model=model
        )
        
        # Add metadata for tracking
        agent_id = f"agent_{len(self._dynamic_agents) + 1}"
        agent.name = f"Specialized Agent {agent_id}"
        agent.description = f"Agent specialized for: {task_description[:100]}"
        
        # Manage dynamic agents (remove oldest if exceeding limit)
        if len(self._dynamic_agents) >= self._max_agents:
            # Remove oldest agent (first item)
            if self._dynamic_agents:
                oldest_key = next(iter(self._dynamic_agents))
                del self._dynamic_agents[oldest_key]
                logger.info(f"Removed oldest dynamic agent {oldest_key} to make room for new one")
        
        # Register the agent
        self._dynamic_agents[agent_id] = agent
        
        logger.info(f"Created dynamic agent {agent_id} with {len(selected_tools)} tools")
        
        return agent

    def can_handle_with_existing_tools(self, requirement: str, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze if a requirement can be handled with existing tools.
        
        Args:
            requirement: Natural language description of requirement
            model: Optional model to use for analysis
            
        Returns:
            Dict with analysis results
        """
        # Use specified model or default from config
        model = model or self._model
        
        # Get LLM to analyze
        llm = get_llm(model)
        
        # Simple prompt to analyze if existing tools are sufficient
        tool_prompt = f"""
        Analyze the following requirement and determine if it can be handled
        with our existing tools:
        
        Requirement: {requirement}
        
        Available tools: {', '.join(self._tools.keys())}
        
        Return your analysis as JSON:
        {{
            "can_handle": true/false,
            "required_tools": ["tool1", "tool2"],
            "missing_capabilities": ["capability1", "capability2"],
            "reasoning": "Your reasoning about whether existing tools can handle this"
        }}
        """
        
        try:
            # Get analysis from LLM
            analysis_result = llm(tool_prompt)
            
            # Try to find JSON object using regex
            json_match = re.search(r'({[\s\S]*})', analysis_result)
            if json_match:
                try:
                    analysis = json.loads(json_match.group(1))
                    
                    # Validate the analysis has required fields
                    if "can_handle" not in analysis:
                        analysis["can_handle"] = False
                        
                    if "required_tools" not in analysis:
                        analysis["required_tools"] = []
                        
                    if "missing_capabilities" not in analysis:
                        analysis["missing_capabilities"] = []
                        
                    if "reasoning" not in analysis:
                        analysis["reasoning"] = "No reasoning provided"
                        
                    # Validate that required tools actually exist
                    valid_tools = [t for t in analysis.get("required_tools", []) if t in self._tools]
                    analysis["required_tools"] = valid_tools
                        
                    return {"success": True, "analysis": analysis}
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON from regex match: {json_match.group(1)[:100]}...")
            
            # Try parsing the whole response
            try:
                analysis = json.loads(analysis_result)
                
                # Validate the analysis has required fields
                if "can_handle" not in analysis:
                    analysis["can_handle"] = False
                    
                if "required_tools" not in analysis:
                    analysis["required_tools"] = []
                    
                if "missing_capabilities" not in analysis:
                    analysis["missing_capabilities"] = []
                    
                if "reasoning" not in analysis:
                    analysis["reasoning"] = "No reasoning provided"
                    
                # Validate that required tools actually exist
                valid_tools = [t for t in analysis.get("required_tools", []) if t in self._tools]
                analysis["required_tools"] = valid_tools
                    
                return {"success": True, "analysis": analysis}
            except json.JSONDecodeError:
                logger.error(f"Failed to parse full response as JSON: {analysis_result[:100]}...")
                
            # If we get here, both parsing attempts failed
            return {
                "success": False,
                "error": "Failed to parse response",
                "raw_response": analysis_result[:500] + "..." if len(analysis_result) > 500 else analysis_result
            }
                
        except Exception as e:
            logger.error(f"Error analyzing requirement: {str(e)}")
            return {"success": False, "error": str(e)}

    def create_agent_from_requirement(self, requirement: str, model: Optional[str] = None, 
                                    ask_permission: bool = True) -> Dict[str, Any]:
        """
        Create a new agent based on a natural language requirement.
        
        This method analyzes the requirement to determine which tools are needed,
        potentially creating new tools if they don't exist.
        
        Args:
            requirement: Natural language description of agent requirements
            model: Optional model to use for the agent
            ask_permission: Whether to ask permission before creating new tools
            
        Returns:
            Dict with new agent and metadata
        """
        # Use specified model or default from config
        model = model or self._model
        
        # First check if we can handle with existing tools
        existing_tools_check = self.can_handle_with_existing_tools(requirement, model)
        
        if existing_tools_check.get("success", False):
            analysis = existing_tools_check["analysis"]
            if analysis.get("can_handle", False):
                # We can handle with existing tools, create an agent with just these tools
                required_tool_names = analysis.get("required_tools", [])
                selected_tools = []
                
                for name in required_tool_names:
                    if name in self._tools:
                        selected_tools.append(self._tools[name])
                        
                # Add chat tool by default
                if "chat" in self._tools and "chat" not in required_tool_names:
                    selected_tools.append(self._tools["chat"])
                    
                # Create agent with selected tools
                agent = self.create_agent(tools=selected_tools, model=model)
                agent.name = "Specialized Agent (Existing Tools)"
                agent.description = f"Specialized agent for: {requirement}"
                
                # Register the dynamic agent
                agent_id = f"agent_{len(self._dynamic_agents) + 1}"
                
                # Manage dynamic agents (remove oldest if exceeding limit)
                if len(self._dynamic_agents) >= self._max_agents:
                    # Remove oldest agent (first item)
                    if self._dynamic_agents:
                        oldest_key = next(iter(self._dynamic_agents))
                        del self._dynamic_agents[oldest_key]
                        logger.info(f"Removed oldest dynamic agent {oldest_key} to make room for new one")
                
                self._dynamic_agents[agent_id] = agent
                
                return {
                    "success": True,
                    "agent": agent,
                    "used_existing_tools": True,
                    "tools": [t.name for t in selected_tools],
                    "agent_id": agent_id
                }
        
        # If we reach here, existing tools aren't sufficient, proceed with potential new tool creation
        # Get LLM to analyze requirements
        llm = get_llm(model)
        
        # Analyze what tools are needed
        tool_analysis_prompt = f"""
        Analyze the following requirement and determine what tools are needed:
        
        Requirement: {requirement}
        
        Available tools: {', '.join(self._tools.keys())}
        
        Return your analysis as JSON:
        {{
            "existing_tools_needed": ["tool1", "tool2"],
            "new_tools_needed": [
                {{
                    "name": "tool_name",
                    "description": "What the tool does",
                    "parameters": {{"param1": "string", "param2": "integer"}},
                    "implementation_details": "How this tool should be implemented"
                }}
            ],
            "agent_name": "descriptive_name_for_agent",
            "agent_description": "What this agent does"
        }}
        """
        
        analysis_result = llm(tool_analysis_prompt)
        
        # Parse response
        try:
            # Try to find JSON object using regex
            json_match = re.search(r'({[\s\S]*})', analysis_result)
            if json_match:
                try:
                    analysis = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    # Try the whole string if regex failed
                    analysis = json.loads(analysis_result)
            else:
                # Try the whole string
                analysis = json.loads(analysis_result)
        except json.JSONDecodeError:
            logger.error(f"Could not parse LLM response as JSON: {analysis_result[:200]}...")
            return {
                "success": False,
                "error": "Could not parse LLM response",
                "raw_response": analysis_result[:500] if len(analysis_result) > 500 else analysis_result,
                "agent": self.create_agent(tools=list(self._tools.values()), model=model)
            }
        
        # Check if we need to create new tools
        new_tools_needed = analysis.get("new_tools_needed", [])
        if new_tools_needed and ask_permission and not self._allow_new_tools:
            # Return the analysis for the caller to handle permission
            return {
                "success": True,
                "requires_permission": True,
                "analysis": analysis,
                "model": model
            }
        
        # Get existing tools
        existing_tools = []
        for tool_name in analysis.get("existing_tools_needed", []):
            if tool_name in self._tools:
                existing_tools.append(self._tools[tool_name])
        
        # Always include chat tool
        if "chat" in self._tools and "chat" not in analysis.get("existing_tools_needed", []):
            existing_tools.append(self._tools["chat"])
        
        # If we're allowed to create new tools
        created_tools = []
        if new_tools_needed and (not ask_permission or ask_permission is False or self._allow_new_tools):
            for tool_spec in new_tools_needed:
                # Create dynamic tool implementation
                tool_impl = self._create_dynamic_tool_implementation(
                    tool_spec["name"],
                    tool_spec["description"],
                    tool_spec["parameters"],
                    tool_spec.get("implementation_details", ""),
                    model
                )
                
                # Convert parameter types
                params = {}
                for param_name, param_type in tool_spec["parameters"].items():
                    if isinstance(param_type, str):
                        if param_type.lower() == "string":
                            params[param_name] = ParamType.STRING
                        elif param_type.lower() == "integer":
                            params[param_name] = ParamType.INTEGER
                        elif param_type.lower() == "float":
                            params[param_name] = ParamType.FLOAT
                        else:
                            params[param_name] = ParamType.ANY
                    else:
                        params[param_name] = ParamType.ANY
                
                # Create the tool
                new_tool = Tool(
                    name=tool_spec["name"],
                    description=tool_spec["description"],
                    parameters=params,
                    func=tool_impl
                )
                
                # Register the tool
                self.register_tool(new_tool)
                created_tools.append(new_tool)
                logger.info(f"Created new dynamic tool: {new_tool.name}")
        
        # Combine existing and created tools
        all_tools = existing_tools + created_tools
        
        # Create the agent
        agent = self.create_agent(tools=all_tools, model=model)
        
        # Store the agent's name and description
        agent.name = analysis.get("agent_name", "Specialized Agent")
        agent.description = analysis.get("agent_description", "A specialized agent")
        
        # Register the dynamic agent
        agent_id = f"agent_{len(self._dynamic_agents) + 1}"
        
        # Manage dynamic agents (remove oldest if exceeding limit)
        if len(self._dynamic_agents) >= self._max_agents:
            # Remove oldest agent (first item)
            if self._dynamic_agents:
                oldest_key = next(iter(self._dynamic_agents))
                del self._dynamic_agents[oldest_key]
                logger.info(f"Removed oldest dynamic agent {oldest_key} to make room for new one")
        
        self._dynamic_agents[agent_id] = agent
        
        return {
            "success": True,
            "agent": agent,
            "created_tools": created_tools,
            "existing_tools": existing_tools,
            "agent_id": agent_id
        }

    def _create_dynamic_tool_implementation(
        self, 
        name: str, 
        description: str, 
        parameters: Dict[str, str], 
        implementation_details: str, 
        model: Optional[str] = None
    ) -> Callable:
        """
        Create a dynamic implementation for a tool using the LLM.
        
        This method creates a function that uses an LLM to implement the tool's
        functionality based on a natural language description.
        
        Args:
            name: Tool name
            description: Tool description
            parameters: Dictionary of parameter names to types
            implementation_details: Natural language description of how to implement
            model: Model to use
            
        Returns:
            A function that implements the tool
        """
        # Create LLM client
        llm = get_llm(model)
        
        def dynamic_tool_implementation(**kwargs):
            """Dynamically implements a tool using LLM."""
            # Format the kwargs as string for LLM prompt
            kwargs_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
            
            # Prompt the LLM to implement the tool
            prompt = f"""
            You are implementing the '{name}' tool with the following description:
            {description}
            
            Implementation details:
            {implementation_details}
            
            This tool has been called with these parameters:
            {kwargs_str}
            
            Implement the tool's functionality and return the result. Be direct and return only what is needed.
            """
            
            # Get the implementation from LLM
            result = llm(prompt)
            return result
        
        # Set the metadata
        dynamic_tool_implementation.__name__ = name
        dynamic_tool_implementation.__doc__ = description
        
        return dynamic_tool_implementation
        
    def get_dynamic_agent(self, agent_id: str) -> Optional[Agent]:
        """
        Get a dynamically created agent by ID.
        
        Args:
            agent_id: ID of the agent to retrieve
            
        Returns:
            The Agent instance or None if not found
        """
        return self._dynamic_agents.get(agent_id)
        
    def list_dynamic_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        List all dynamically created agents.
        
        Returns:
            Dictionary of agent IDs to metadata
        """
        return {
            agent_id: {
                "name": agent.name,
                "description": agent.description,
                "tools": [t.name for t in agent.tools.values()] if hasattr(agent, 'tools') else []
            }
            for agent_id, agent in self._dynamic_agents.items()
        }
