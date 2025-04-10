"""
Orchestrator module for coordinating multiple agents.

This module provides an orchestrator that manages and coordinates multiple agents
to accomplish complex tasks, handling task delegation, agent coordination, and
result integration.
"""
#this file is over 1000 lines, it is only this long for debugging purposes
import json
import pprint
import time
import re
import os
import threading
from typing import Dict, List, Any, Optional, Union, TypeVar, Type, cast
from dataclasses import dataclass, field

from ..logging import get_logger
from tinyagent.prompts.prompt_manager import PromptManager
from ..agent import Agent, get_llm
from ..config import load_config, get_config_value
from ..exceptions import OrchestratorError, AgentNotFoundError
from .dynamic_agent_factory import DynamicAgentFactory

# Set up logger with more detailed formatting
logger = get_logger(__name__)

from tinyagent.utils.logging_utils import (
    log_task_event,
    log_decision,
    log_section_header,
    log_step,
)


@dataclass
class TaskStatus:
    """
    Status information for a task being orchestrated.
    
    Attributes:
        task_id: Unique identifier for the task
        description: Text description of the task
        status: Current status (pending, in_progress, completed, failed, needs_permission)
        assigned_agent: ID of the agent assigned to the task (optional)
        created_at: Timestamp when the task was created
        started_at: Timestamp when the task was started (optional)
        completed_at: Timestamp when the task was completed (optional)
        result: The result of the task (optional)
        error: Error message if the task failed (optional)
    """
    task_id: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed, needs_permission
    assigned_agent: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None


# Type variable for the singleton pattern
T = TypeVar('T')


class Orchestrator:
    """
    Orchestrates multiple agents to accomplish complex tasks.
    
    Manages task delegation, agent coordination, and result integration across 
    multiple specialized agents.
    
    Attributes:
        factory: DynamicAgentFactory instance for creating agents
        tasks: Dictionary of tasks being managed
        agents: Dictionary of registered agents
        _lock: Threading lock for concurrency control
    """
    
    _instance = None  # Singleton instance
    
    @classmethod
    def get_instance(cls: Type[T], config: Optional[Dict[str, Any]] = None) -> T:
        """
        Get or create the singleton orchestrator instance.
        
        Args:
            config: Optional configuration dictionary
            
        Returns:
            The singleton Orchestrator instance
        """
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the orchestrator with configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.factory = DynamicAgentFactory.get_instance(config)
        self.tasks: Dict[str, TaskStatus] = {}
        self.agents: Dict[str, Agent] = {}
        self.next_task_id = 1
        self.next_agent_id = 1
        self.lock = threading.Lock()
        self.prompt_manager = PromptManager()
        
        # Load configuration
        if config is None:
            self.config = load_config()
        else:
            self.config = config
        
        # Initialize the triage agent
        self._create_triage_agent()
        logger.info("Orchestrator initialized")
        
    def _create_triage_agent(self) -> None:
        """
        Create and register the triage agent.
        
        The triage agent is responsible for analyzing user queries and delegating
        to specialized agents.
        """
        # Get max_retries from config if available, otherwise use default (3)
        max_retries = get_config_value(self.config, 'retries.max_attempts', 3)
        
        # Get preferred model from config if available
        model = get_config_value(self.config, 'model.triage', None)
        
        # Make sure all tools are registered with the factory first
        try:
            from ..tools import (
                anon_coder_tool,
                llm_serializer_tool,
                brave_web_search_tool,
                ripgrep_tool,
                aider_tool,
                load_external_tools
            )
            
            # Register all tools explicitly
            self.factory.register_tool(anon_coder_tool)
            self.factory.register_tool(llm_serializer_tool)
            self.factory.register_tool(brave_web_search_tool)
            self.factory.register_tool(ripgrep_tool)
            self.factory.register_tool(aider_tool)
            
            # Add external tools
            external_tools = load_external_tools()
            for tool in external_tools:
                self.factory.register_tool(tool)
                
            logger.info(f"Registered {len(self.factory.list_tools())} tools with factory")
        except Exception as e:
            logger.error(f"Error registering tools: {str(e)}")
        
        # Create a specialized agent with all tools for triage using the factory
        triage_agent = self.factory.create_agent(
            tools=list(self.factory.list_tools().values()),
            model=model
        )
        
        # Manually set max_retries
        triage_agent.max_retries = max_retries
        
        # Register the triage agent
        triage_agent.name = "triage_agent"
        triage_agent.description = "Analyzes queries and delegates to specialized agents"
        self.agents["triage"] = triage_agent
        
        logger.info("Triage agent created")
    
    def _generate_task_id(self) -> str:
        """
        Generate a unique task ID.
        
        Returns:
            A unique task ID string
        """
        with self.lock:
            task_id = f"task_{self.next_task_id}"
            self.next_task_id += 1
        return task_id
    
    def _generate_agent_id(self) -> str:
        """
        Generate a unique agent ID.
        
        Returns:
            A unique agent ID string
        """
        with self.lock:
            agent_id = f"agent_{self.next_agent_id}"
            self.next_agent_id += 1
        return agent_id
    
    def submit_task(self, description: str, need_permission: bool = True, execution_mode: str = "standard", max_iterations: int = 5) -> str:
        """
        Submit a new task to the orchestrator.
        
        Args:
            description: Natural language description of the task
            need_permission: Whether to ask for permission to create new tools
            execution_mode: Execution mode to use ("standard", "riv")
            max_iterations: Maximum number of iterations for iterative execution modes
            
        Returns:
            Task ID for tracking
        """
        task_id = self._generate_task_id()
        self.tasks[task_id] = TaskStatus(
            task_id=task_id,
            description=description
        )
        
        log_section_header("New Task Submission")
        log_step(
            step_number=1,
            title="Task Initialization",
            details={
                "task_id": task_id,
                "description": description[:100] + "..." if len(description) > 100 else description,
                "need_permission": need_permission,
                "execution_mode": execution_mode,
                "max_iterations": max_iterations if execution_mode != "standard" else None,
                "timestamp": time.time()
            },
            reasoning="Initializing new task with provided description"
        )
        
        # Process the task based on the execution approach
        if execution_mode == "riv":
            # Use RIV (Reflect-Improve-Verify) execution approach
            try:
                threading.Thread(
                    target=self.execute_riv_task,
                    args=(task_id, max_iterations)
                ).start()
                
                log_step(
                    step_number=2,
                    title="Execution Approach",
                    details={
                        "approach": "RIV (Reflect-Improve-Verify)",
                        "max_iterations": max_iterations
                    },
                    reasoning="Starting RIV execution in background thread"
                )
            except Exception as e:
                logger.error(f"Error starting RIV execution: {str(e)}")
                # Fall back to standard execution
                self._process_task(task_id, need_permission)
        else:
            # Use standard one-pass execution approach
            self._process_task(task_id, need_permission)
        
        return task_id
    
    def _process_task(self, task_id: str, need_permission: bool) -> None:
        """
        Process a task by triaging and delegating to appropriate agents.
        
        Args:
            task_id: ID of the task to process
            need_permission: Whether to require permission for new tools
        """
        task = self.tasks[task_id]
        task.status = "in_progress"
        task.started_at = time.time()
        
        log_section_header("Task Processing")
        log_step(
            step_number=2,
            title="Task Status Update",
            details={
                "task_id": task_id,
                "status": task.status,
                "started_at": task.started_at
            },
            reasoning="Starting task processing with initial status set to in_progress"
        )
        
        try:
            # First, use the triage agent to analyze the task
            try:
                log_section_header("Task Analysis")
                log_step(
                    step_number=3,
                    title="Triage Process",
                    details={
                        "task_id": task_id,
                        "timestamp": time.time()
                    },
                    reasoning="Starting task analysis to determine best handling approach"
                )
                
                triage_result = self._triage_task(task)
                
                log_step(
                    step_number=4,
                    title="Triage Results",
                    details={
                        "assessment": triage_result.get("assessment", "unknown"),
                        "requires_new_agent": triage_result.get("requires_new_agent", False),
                        "duration": time.time() - task.started_at
                    },
                    reasoning=f"Task analysis completed with assessment: {triage_result.get('assessment', 'unknown')}"
                )
                
            except Exception as triage_error:
                log_section_header("Triage Error")
                log_step(
                    step_number=5,
                    title="Error Handling",
                    details={
                        "error": str(triage_error),
                        "error_type": type(triage_error).__name__,
                        "duration": time.time() - task.started_at
                    },
                    reasoning=f"Triage process failed due to: {str(triage_error)}"
                )
                
                # Capture detailed error information about retry attempts
                if hasattr(triage_error, 'history') and triage_error.history:
                    attempts_info = []
                    for i, entry in enumerate(triage_error.history, 1):
                        if isinstance(entry, dict):
                            attempts_info.append(f"Attempt {i}: {entry.get('error', 'Unknown error')}")
                    
                    if attempts_info:
                        task.error = "\n".join(attempts_info)
                    else:
                        task.error = f"Triage failed after multiple attempts: {str(triage_error)}"
                else:
                    task.error = f"Triage error: {str(triage_error)}"
                
                # Use a default triage result
                triage_result = {
                    "assessment": "direct",
                    "requires_new_agent": False,
                    "reasoning": f"Triage failed: {str(triage_error)}, falling back to direct handling"
                }
            
            log_step(
                step_number=6,
                title="STEP 1: Initial Triage Analysis",
                details={
                    "assessment": triage_result.get("assessment"),
                    "requires_new_agent": triage_result.get("requires_new_agent", False),
                    "has_tool": "tool" in triage_result,
                    "has_arguments": "arguments" in triage_result,
                    "has_tool_sequence": "tool_sequence" in triage_result
                },
                reasoning="Analyzing initial triage results"
            )
            
            # Check if triage_result contains a multi-step tool sequence
            if "tool_sequence" in triage_result:
                steps = triage_result["tool_sequence"]
                # Make sure it's a list of steps
                if not isinstance(steps, list):
                    raise ValueError("tool_sequence must be a list of tool-call steps.")
                
                log_section_header("Multi-Step Tool Sequence Execution")
                
                aggregated_results = []
                for i, step_info in enumerate(steps, start=1):
                    tool_name = step_info.get("tool")
                    arguments = step_info.get("arguments", {})
                    
                    if not tool_name:
                        raise ValueError(f"Missing 'tool' field in step {i} of tool_sequence.")
                    
                    log_step(
                        step_number=i + 6,
                        title=f"Tool Sequence Step {i}",
                        details={
                            "tool_name": tool_name,
                            "arguments": arguments
                        },
                        reasoning=f"Executing step {i} in the multi-tool plan."
                    )
                    
                    try:
                        # Execute the tool via the factory
                        result = self.factory.execute_tool(tool_name, **arguments)
                        aggregated_results.append({
                            "step": i,
                            "tool": tool_name,
                            "arguments": arguments,
                            "result": result
                        })
                        
                        log_step(
                            step_number=i + 6,
                            title=f"Tool Execution Result for Step {i}",
                            details={
                                "tool": tool_name,
                                "result": result
                            },
                            reasoning=f"Step {i} completed successfully"
                        )
                    except Exception as e:
                        error_msg = f"Error executing tool {tool_name} in sequence step {i}: {str(e)}"
                        log_step(
                            step_number=i + 6,
                            title=f"Tool Execution Error for Step {i}",
                            details={
                                "tool": tool_name,
                                "error": str(e),
                                "error_type": type(e).__name__
                            },
                            reasoning=f"Step {i} failed: {str(e)}"
                        )
                        # Add the error to the results and continue with the next step
                        aggregated_results.append({
                            "step": i,
                            "tool": tool_name,
                            "arguments": arguments,
                            "error": str(e)
                        })
                
                task.result = {
                    "type": "tool_sequence",
                    "steps": aggregated_results,
                    "reasoning": triage_result.get("reasoning", "Multi-step tool execution")
                }
                task.status = "completed"
                task.completed_at = time.time()
                
                log_section_header("Tool Sequence Completion")
                log_step(
                    step_number=7 + len(steps),
                    title="Sequence Completion",
                    details={
                        "total_steps": len(steps),
                        "successful_steps": sum(1 for r in aggregated_results if "error" not in r),
                        "failed_steps": sum(1 for r in aggregated_results if "error" in r),
                        "duration": time.time() - task.started_at
                    },
                    reasoning="Tool sequence execution completed"
                )
                
                return
            
            # Check if triage_result is actually a direct tool call
            if "tool" in triage_result and "arguments" in triage_result:
                log_section_header("Direct Tool Execution")
                log_step(
                    step_number=8,
                    title="Tool Selection",
                    details={
                        "tool": triage_result["tool"],
                        "arguments": triage_result["arguments"]
                    },
                    reasoning=f"Task can be handled directly with tool: {triage_result['tool']}"
                )
                
                try:
                    result = self.factory.execute_tool(triage_result["tool"], **triage_result["arguments"])
                    task.result = result
                    task.status = "completed"
                    
                    log_step(
                        step_number=9,
                        title="Tool Execution Results",
                        details={
                            "tool": triage_result["tool"],
                            "status": task.status,
                            "result": result,
                            "duration": time.time() - task.started_at
                        },
                        reasoning=f"Tool execution completed successfully with result: {result}"
                    )
                    
                    task.completed_at = time.time()
                    return
                except Exception as e:
                    log_section_header("Tool Execution Error")
                    log_step(
                        step_number=10,
                        title="Error Handling",
                        details={
                            "tool": triage_result["tool"],
                            "error": str(e),
                            "error_type": type(e).__name__
                        },
                        reasoning=f"Tool execution failed due to: {str(e)}"
                    )
                    logger.error(f"Error executing tool {triage_result['tool']} directly: {str(e)}")
            
            if triage_result.get("requires_new_agent", False):
                log_section_header("New Agent Creation")
                log_step(
                    step_number=11,
                    title="Agent Creation Decision",
                    details={"need_permission": need_permission},
                    reasoning="Task complexity requires creation of a new specialized agent"
                )
                
                if need_permission:
                    agent_result = self.factory.create_agent_from_requirement(
                        requirement=task.description,
                        ask_permission=True
                    )
                    
                    if agent_result.get("requires_permission", False):
                        log_step(
                            step_number=12,
                            title="Permission Required",
                            details={
                                "new_tools_needed": agent_result.get("analysis", {}).get("new_tools_needed", []),
                                "message": "This task requires creating new tools. Please run again with permission."
                            },
                            reasoning="Task requires new tools that need user permission to create"
                        )
                        
                        task.result = {
                            "requires_permission": True,
                            "new_tools_needed": agent_result.get("analysis", {}).get("new_tools_needed", []),
                            "message": "This task requires creating new tools. Please run again with permission."
                        }
                        task.status = "needs_permission"
                        return
                
                log_step(
                    step_number=13,
                    title="Creating New Agent",
                    details={"requirement": task.description},
                    reasoning="Creating new specialized agent to handle task requirements"
                )
                
                agent_result = self.factory.create_agent_from_requirement(
                    requirement=task.description,
                    ask_permission=False
                )
                
                if agent_result["success"]:
                    agent_id = self._generate_agent_id()
                    self.agents[agent_id] = agent_result["agent"]
                    
                    log_step(
                        step_number=14,
                        title="New Agent Created",
                        details={
                            "agent_id": agent_id,
                            "agent_type": type(agent_result["agent"]).__name__
                        },
                        reasoning=f"Successfully created new agent of type: {type(agent_result['agent']).__name__}"
                    )
                    
                    result = self._execute_with_agent(agent_id, task)
                    task.result = result
                    task.status = "completed"
                    
                    log_step(
                        step_number=15,
                        title="New Agent Task Completion",
                        details={
                            "agent_id": agent_id,
                            "status": task.status,
                            "duration": time.time() - task.started_at
                        },
                        reasoning=f"New agent successfully completed task with status: {task.status}"
                    )
                else:
                    task.error = f"Failed to create specialized agent: {agent_result.get('error', 'Unknown error')}"
                    task.status = "failed"
                    
                    log_section_header("Agent Creation Error")
                    log_step(
                        step_number=16,
                        title="Error Handling",
                        details={
                            "error": task.error,
                            "duration": time.time() - task.started_at
                        },
                        reasoning=f"Failed to create new agent due to: {task.error}"
                    )
            else:
                agent_id = triage_result.get("agent_id", "triage")
                
                log_section_header("Existing Agent Usage")
                log_step(
                    step_number=17,
                    title="Agent Selection",
                    details={"agent_id": agent_id},
                    reasoning=f"Using existing agent {agent_id} as determined by triage analysis"
                )
                
                result = self._execute_with_agent(agent_id, task)
                task.result = result
                task.status = "completed"
                
                log_step(
                    step_number=18,
                    title="Task Completion",
                    details={
                        "agent_id": agent_id,
                        "status": task.status,
                        "duration": time.time() - task.started_at
                    },
                    reasoning=f"Existing agent {agent_id} completed task with status: {task.status}"
                )
        
        except Exception as e:
            task.error = str(e)
            task.status = "failed"
            
            log_section_header("Task Failure")
            log_step(
                step_number=19,
                title="Error Handling",
                details={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration": time.time() - task.started_at
                },
                reasoning=f"Task failed due to unexpected error: {str(e)}"
            )
        
        finally:
            task.completed_at = time.time()
            
            log_section_header("Task Summary")
            log_step(
                step_number=20,
                title="Final Status",
                details={
                    "final_status": task.status,
                    "total_duration": time.time() - task.started_at,
                    "has_error": bool(task.error)
                },
                reasoning=f"Task processing completed with final status: {task.status}"
            )
    
    def _triage_task(self, task: TaskStatus) -> Dict[str, Any]:
        """
        Use the triage agent to analyze a task and determine how to handle it.
        
        Args:
            task: Task to analyze
            
        Returns:
            Dict with triage results
            
        Raises:
            OrchestratorError: If triage fails and no fallback can be used
        """
        # First, check if we can handle with existing tools
        existing_tools_check = self.factory.can_handle_with_existing_tools(task.description)
        
        if existing_tools_check.get("success", False):
            analysis = existing_tools_check["analysis"]
            if analysis.get("can_handle", False):
                # We can handle with existing tools
                logger.info(f"Task '{task.task_id}' can be handled with existing tools")
                return {
                    "assessment": "direct",
                    "requires_new_agent": False,
                    "required_tools": analysis.get("required_tools", []),
                    "reasoning": analysis.get("reasoning", "Can be handled with existing tools")
                }
        
        # If we get here, either the check failed or we need more analysis
        triage_agent = self.agents["triage"]
        
        # Get list of dynamic agents
        dynamic_agents = self.factory.list_dynamic_agents()
        dynamic_agent_ids = list(dynamic_agents.keys())
        
        # Create a prompt for the triage agent, including information from our tools check
        reasoning_from_check = ""
        if existing_tools_check.get("success", False):
            analysis = existing_tools_check["analysis"]
            missing = analysis.get("missing_capabilities", [])
            if missing:
                reasoning_from_check = f"Missing capabilities: {', '.join(missing)}"
        
        # Add special handling for capability queries like "what can you do"
        if "what can you do" in task.description.lower() or "capabilities" in task.description.lower() or "help me" in task.description.lower():
            return {
                "assessment": "direct",
                "requires_new_agent": False,
                "reasoning": "Capability query detected. Responding with system capabilities information."
            }
        
        try:
            triage_template = self.prompt_manager.load_template("workflows/triage.md")
            triage_prompt = self.prompt_manager.process_template(
                triage_template,
                {
                    "query": task.description,
                    "tools": ', '.join(self.factory.list_tools().keys()),
                    "agents": ', '.join(list(self.agents.keys()) + dynamic_agent_ids),
                    "reasoning": reasoning_from_check,
                },
            )
            logger.debug("Using PromptManager to generate triage prompt")
        except Exception as e:
            logger.error(f"Failed to load or process triage prompt template: {str(e)}")
            raise RuntimeError(
                "Critical: triage prompt template missing or invalid. "
                "Please ensure 'prompts/workflows/triage.md' exists and is correct."
            ) from e
        
            # Get triage analysis - let the Agent.run method handle retries internally
        try:
            # Wrap the entire execution in an exception handler to catch tool execution errors
            try:
                result = triage_agent.run(triage_prompt)
            except Exception as tool_error:
                # If a tool execution fails, still return a valid assessment
                logger.error(f"Tool execution failed during triage: {str(tool_error)}")
                return {
                    "assessment": "direct",
                    "requires_new_agent": False,
                    "reasoning": f"Tool execution error: {str(tool_error)}"
                }
                
            # The Agent.run method should have already tried to parse and retry
            # up to max_retries times, and returned a fallback if all failed.
            # Here we just need to do a final check and parsing.
            
            # First check if we already got a dictionary (already parsed)
            if isinstance(result, dict):
                # Special case: If we got a chat tool with empty arguments, convert to assessment format
                if "tool" in result and result.get("tool") == "chat":
                    logger.info(f"Triage returned chat tool format for task {task.task_id}, converting to assessment")
                    # If arguments.message exists, use that for reasoning
                    reasoning = "Chat tool returned by triage agent, converting to direct assessment"
                    if "arguments" in result and isinstance(result["arguments"], dict):
                        if "message" in result["arguments"] and result["arguments"]["message"]:
                            reasoning = result["arguments"]["message"]
                    
                    return {
                        "assessment": "direct",
                        "requires_new_agent": False,
                        "reasoning": reasoning
                    }
                
            # Otherwise try to parse the JSON result
            if isinstance(result, str):
                # Strategy 1: Try to find JSON object using regex
                json_match = re.search(r'({[\s\S]*})', result)
                if json_match:
                    try:
                        parsed_result = json.loads(json_match.group(1))
                        print("\n[Parsed JSON from regex extraction]:")
                        pprint.pprint(parsed_result)
                        return parsed_result
                    except json.JSONDecodeError:
                        pass
                        
                # Strategy 2: Try parsing entire content as JSON
                try:
                    parsed_result = json.loads(result)
                    print("\n[Parsed JSON from direct parse]:")
                    pprint.pprint(parsed_result)
                    return parsed_result
                except json.JSONDecodeError:
                    # Check if this looks like a chat response rather than a JSON response
                    if isinstance(result, str) and len(result.strip()) > 0 and "{" not in result and "}" not in result:
                        logger.warning(f"Triage returned chat response instead of JSON format: {result[:100]}...")
                        # Extract any assessment-like keywords to make a best guess
                        assessment = "direct"  # Default
                        if re.search(r'\b(new agent|specialized|create agent)\b', result, re.IGNORECASE):
                            assessment = "create_new"
                            
                        default_result = {
                            "assessment": assessment,
                            "requires_new_agent": assessment == "create_new",
                            "reasoning": f"Inferred from chat response: {result[:100]}...",
                            "original_response": result[:500]  # Store original for debugging
                        }
                    else:
                        # Standard JSON parsing failure
                        logger.error(f"Failed to parse triage result for task {task.task_id}: {result[:100]}...")
                        default_result = {
                            "assessment": "direct",
                            "requires_new_agent": False,
                            "reasoning": "Could not parse triage result, falling back to direct handling"
                        }
                    return default_result
            else:
                # If not a string, it's probably already a structured result
                return result
        
        except Exception as e:
            # Fallback on error
            logger.error(f"Error in triage for task {task.task_id}: {str(e)}")
            fallback_result = {
                "assessment": "direct",
                "requires_new_agent": False,
                "reasoning": f"Triage error: {str(e)}, falling back to direct handling"
            }
            return fallback_result
    
    def _execute_with_agent(self, agent_id: str, task: TaskStatus) -> Any:
        """
        Execute a task using the specified agent.
        
        Args:
            agent_id: ID of the agent to use
            task: Task to execute
            
        Returns:
            Result from the agent
            
        Raises:
            AgentNotFoundError: If the agent is not found
        """
        # First check if it's a dynamic agent
        agent = self.factory.get_dynamic_agent(agent_id)
        
        # If not found in dynamic agents, check regular agents
        if agent is None:
            agent = self.agents.get(agent_id)
        
        if agent is None:
            error_msg = f"Agent with ID '{agent_id}' not found"
            logger.error(error_msg)
            raise AgentNotFoundError(error_msg)
            
        task.assigned_agent = agent_id
        logger.info(f"Executing task {task.task_id} with agent {agent_id}")
        
        # Execute task
        result = agent.run(task.description)
        return result
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get the current status of a task.
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            TaskStatus or None if not found
        """
        return self.tasks.get(task_id)
    
    def grant_permission(self, task_id: str) -> None:
        """
        Grant permission for a task that needs it.
        
        Args:
            task_id: ID of the task that needs permission
            
        Raises:
            ValueError: If the task is not found or does not need permission
        """
        task = self.tasks.get(task_id)
        if not task:
            error_msg = f"Task {task_id} not found"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if task.status != "needs_permission":
            error_msg = f"Task {task_id} does not need permission (status: {task.status})"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Reprocess the task with permission granted
        task.status = "pending"
        logger.info(f"Permission granted for task {task_id}")
        self._process_task(task_id, need_permission=False)
    
    def list_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        List all registered agents.
        
        Returns:
            Dictionary of agent IDs to metadata
        """
        # Combine built-in agents and dynamic agents
        all_agents = {}
        
        # Add built-in agents
        for agent_id, agent in self.agents.items():
            all_agents[agent_id] = {
                "name": getattr(agent, "name", agent_id),
                "description": getattr(agent, "description", "No description"),
                "dynamic": False
            }
        
        # Add dynamic agents
        dynamic_agents = self.factory.list_dynamic_agents()
        for agent_id, agent_info in dynamic_agents.items():
            all_agents[agent_id] = {
                **agent_info,
                "dynamic": True
            }
        
        return all_agents

    def list_tools(self) -> Dict[str, Any]:
        """
        Return a dictionary of all registered tools from the factory.
        
        Returns:
            Dictionary of tool names to tool definitions/objects
        """
        return self.factory.list_tools()

    def execute_riv_task(self, task_id: str, max_iterations: int = 5) -> Dict[str, Any]:
        """
        Execute a task using the RIV (Reflect, Improve, Verify) pattern.
        
        This adaptive approach uses an iterative loop that:
        1. Reflects on the current state
        2. Improves with targeted actions
        3. Verifies if the task is complete
        
        Args:
            task_id: ID of the task to execute
            max_iterations: Maximum number of iterations to perform
            
        Returns:
            A dictionary containing the final result and execution history
        """
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = "in_progress"
        task.started_at = time.time()
        
        # Initialize execution memory
        memory = {
            "iterations": [],
            "current_result": None,
            "original_task": task.description
        }
        
        iteration = 0
        is_complete = False
        
        log_section_header("Starting RIV Task Execution")
        log_step(
            step_number=1,
            title="Task Initialization",
            details={
                "task_id": task_id,
                "description": task.description[:100] + "..." if len(task.description) > 100 else task.description,
                "max_iterations": max_iterations
            },
            reasoning="Beginning RIV execution loop (Reflect-Improve-Verify)"
        )
        
        # Main RIV execution loop
        while iteration < max_iterations and not is_complete:
            iteration += 1
            iteration_memory = {"iteration": iteration, "timestamp": time.time()}
            
            log_section_header(f"RIV Iteration {iteration}")
            
            try:
                # ------- REFLECT phase -------
                # Analyze current state and identify what's needed
                log_step(
                    step_number=iteration*3-2,
                    title=f"REFLECT (Iteration {iteration})",
                    details={"current_state": "analyzing"},
                    reasoning="Analyzing current state and planning next steps"
                )
                
                reflection_prompt = self._build_reflection_prompt(task, memory)
                triage_agent = self.agents["triage"]
                reflection_result = triage_agent.run(reflection_prompt)
                
                # Parse the reflection result
                if isinstance(reflection_result, dict):
                    reflection = reflection_result
                else:
                    # Try to parse as JSON
                    try:
                        json_match = re.search(r'({[\s\S]*})', reflection_result)
                        if json_match:
                            reflection = json.loads(json_match.group(1))
                        else:
                            reflection = json.loads(reflection_result)
                    except (json.JSONDecodeError, TypeError):
                        logger.error(f"Failed to parse reflection result: {reflection_result[:200]}...")
                        reflection = {
                            "status": "needs_improvement",
                            "action_plan": {"type": "retry", "reason": "Failed to parse previous result"}
                        }
                
                is_complete = reflection.get("status") == "complete"
                iteration_memory["reflection"] = reflection
                
                log_step(
                    step_number=iteration*3-1,
                    title=f"Reflection Analysis (Iteration {iteration})",
                    details={
                        "status": reflection.get("status", "unknown"),
                        "reasoning": reflection.get("reasoning", "No reasoning provided"),
                        "is_complete": is_complete
                    },
                    reasoning="Reflecting on current progress and determining next actions"
                )
                
                # If reflection says we're done, break the loop
                if is_complete:
                    task.status = "completed"
                    task.result = memory["current_result"]
                    iteration_memory["status"] = "complete"
                    memory["iterations"].append(iteration_memory)
                    break
                
                # ------- IMPROVE phase -------
                # Execute the planned action to improve the result
                action_plan = reflection.get("action_plan", {})
                action_type = action_plan.get("type", "unknown")
                
                log_step(
                    step_number=iteration*3,
                    title=f"IMPROVE (Iteration {iteration})",
                    details={
                        "action_type": action_type,
                        "details": action_plan
                    },
                    reasoning=f"Executing improvement action: {action_type}"
                )
                
                action_result = None
                action_error = None
                
                try:
                    if action_type == "use_tool":
                        # Execute a single tool
                        tool_name = action_plan.get("tool")
                        arguments = action_plan.get("arguments", {})
                        
                        if not tool_name:
                            raise ValueError("Missing tool name in action plan")
                        
                        action_result = self.factory.execute_tool(tool_name, **arguments)
                        
                    elif action_type == "use_tool_sequence":
                        # Execute a sequence of tools
                        steps = action_plan.get("tool_sequence", [])
                        if not steps or not isinstance(steps, list):
                            raise ValueError("Invalid or missing tool sequence")
                        
                        sequence_results = []
                        for i, step_info in enumerate(steps, start=1):
                            tool_name = step_info.get("tool")
                            arguments = step_info.get("arguments", {})
                            
                            if not tool_name:
                                raise ValueError(f"Missing tool name in sequence step {i}")
                            
                            try:
                                result = self.factory.execute_tool(tool_name, **arguments)
                                sequence_results.append({
                                    "step": i,
                                    "tool": tool_name,
                                    "arguments": arguments,
                                    "result": result
                                })
                            except Exception as e:
                                sequence_results.append({
                                    "step": i,
                                    "tool": tool_name,
                                    "arguments": arguments,
                                    "error": str(e)
                                })
                        
                        action_result = sequence_results
                        
                    elif action_type == "use_agent":
                        # Use a specific agent
                        agent_id = action_plan.get("agent_id")
                        if not agent_id:
                            raise ValueError("Missing agent_id in action plan")
                        
                        prompt = action_plan.get("prompt", task.description)
                        action_result = self._execute_with_agent(agent_id, prompt)
                        
                    elif action_type == "create_agent":
                        # Create a new specialized agent
                        requirement = action_plan.get("requirement", task.description)
                        agent_result = self.factory.create_agent_from_requirement(
                            requirement=requirement,
                            ask_permission=False
                        )
                        
                        if agent_result["success"]:
                            agent_id = self._generate_agent_id()
                            self.agents[agent_id] = agent_result["agent"]
                            prompt = action_plan.get("prompt", task.description)
                            action_result = self._execute_with_agent(agent_id, prompt)
                        else:
                            raise ValueError(f"Failed to create agent: {agent_result.get('error')}")
                            
                    elif action_type == "refine_result":
                        # Refine the current result
                        refinement_prompt = action_plan.get("prompt")
                        if not refinement_prompt:
                            raise ValueError("Missing refinement prompt in action plan")
                        
                        action_result = triage_agent.run(refinement_prompt)
                    
                    elif action_type == "retry":
                        # Simply retry with the triage agent
                        action_result = triage_agent.run(task.description)
                    
                    else:
                        raise ValueError(f"Unknown action type: {action_type}")
                        
                except Exception as e:
                    action_error = str(e)
                    logger.error(f"Error in IMPROVE phase (iteration {iteration}): {action_error}")
                
                # Store the action result
                iteration_memory["action"] = {
                    "type": action_type,
                    "details": action_plan,
                    "result": action_result,
                    "error": action_error
                }
                
                # Update the current result
                if action_error is None:
                    memory["current_result"] = action_result
                
                # ------- VERIFY phase -------
                # Check if the result is satisfactory
                log_step(
                    step_number=iteration*3+1,
                    title=f"VERIFY (Iteration {iteration})",
                    details={
                        "has_result": action_result is not None,
                        "has_error": action_error is not None
                    },
                    reasoning="Verifying result of improvement action"
                )
                
                verify_prompt = self._build_verification_prompt(task, memory, action_result, action_error)
                verification_result = triage_agent.run(verify_prompt)
                
                # Parse the verification result
                if isinstance(verification_result, dict):
                    verification = verification_result
                else:
                    try:
                        json_match = re.search(r'({[\s\S]*})', verification_result)
                        if json_match:
                            verification = json.loads(json_match.group(1))
                        else:
                            verification = json.loads(verification_result)
                    except (json.JSONDecodeError, TypeError):
                        logger.error(f"Failed to parse verification result: {verification_result[:200]}...")
                        verification = {
                            "is_complete": False,
                            "quality": "unknown",
                            "reasoning": "Failed to parse verification result"
                        }
                
                is_complete = verification.get("is_complete", False)
                iteration_memory["verification"] = verification
                
                log_step(
                    step_number=iteration*3+2,
                    title=f"Verification Results (Iteration {iteration})",
                    details={
                        "is_complete": is_complete,
                        "quality": verification.get("quality", "unknown"),
                        "reasoning": verification.get("reasoning", "No reasoning provided")
                    },
                    reasoning="Determining if task is complete based on verification"
                )
                
                # Add the iteration to memory
                memory["iterations"].append(iteration_memory)
                
                # If verification says we're done, break the loop
                if is_complete:
                    task.status = "completed"
                    task.result = memory["current_result"]
                    break
                
            except Exception as e:
                # Handle any uncaught exceptions in the iteration
                logger.error(f"Error in RIV cycle {iteration}: {str(e)}")
                iteration_memory["error"] = str(e)
                memory["iterations"].append(iteration_memory)
                
                if iteration == max_iterations:
                    task.error = f"Failed after {max_iterations} iterations: {str(e)}"
                    task.status = "failed"
        
        # If we've hit max iterations without completing
        if iteration >= max_iterations and not is_complete:
            task.status = "failed" if task.status == "in_progress" else task.status
            task.error = f"Reached maximum iterations ({max_iterations}) without completing task"
            
            log_section_header("Max Iterations Reached")
            log_step(
                step_number=iteration*3+3,
                title="Iteration Limit Reached",
                details={
                    "max_iterations": max_iterations,
                    "final_status": task.status
                },
                reasoning="Task execution stopped due to reaching maximum allowed iterations"
            )
        
        # Update task with final results
        task.completed_at = time.time()
        final_result = {
            "execution_memory": memory,
            "iterations_completed": iteration,
            "task_completed": is_complete,
            "final_result": memory["current_result"]
        }
        task.result = final_result
        
        log_section_header("RIV Execution Complete")
        log_step(
            step_number=iteration*3+4,
            title="Final Status",
            details={
                "task_id": task_id,
                "status": task.status,
                "iterations": iteration,
                "duration": task.completed_at - task.started_at
            },
            reasoning="RIV process completed with final status"
        )
        
        return final_result
    
    def _build_reflection_prompt(self, task: TaskStatus, memory: Dict[str, Any]) -> str:
        """
        Build a prompt for the REFLECT phase to analyze current state and plan next steps.
        
        Args:
            task: The task being executed
            memory: The execution memory so far
            
        Returns:
            A prompt string for the LLM to analyze
        """
        available_tools = ', '.join(self.factory.list_tools().keys())
        available_agents = ', '.join(self.agents.keys())
        
        # Create a concise summary of previous iterations
        iterations_summary = ""
        if memory["iterations"]:
            for i, iteration in enumerate(memory["iterations"], start=1):
                iterations_summary += f"\nITERATION {i} SUMMARY:\n"
                
                # Add reflection
                reflection = iteration.get("reflection", {})
                iterations_summary += f"- Status: {reflection.get('status', 'unknown')}\n"
                iterations_summary += f"- Reasoning: {reflection.get('reasoning', 'N/A')[:200]}...\n"
                
                # Add action
                action = iteration.get("action", {})
                action_type = action.get("type", "unknown")
                iterations_summary += f"- Action: {action_type}\n"
                
                if action_type == "use_tool":
                    tool_name = action.get("details", {}).get("tool", "unknown")
                    iterations_summary += f"  - Tool used: {tool_name}\n"
                    
                    # Add results summary
                    result = action.get("result")
                    if result is not None:
                        if isinstance(result, str) and len(result) > 100:
                            iterations_summary += f"  - Result: {result[:100]}...(truncated)\n"
                        elif isinstance(result, list) and len(result) > 0:
                            iterations_summary += f"  - Result: List with {len(result)} items\n"
                        else:
                            iterations_summary += f"  - Result: Result obtained\n"
                
                # Add verification
                verification = iteration.get("verification", {})
                iterations_summary += f"- Verification: {verification.get('quality', 'unknown')}\n"
                iterations_summary += f"- Complete: {verification.get('is_complete', False)}\n"
                if "missing_outputs" in verification:
                    missing = verification.get("missing_outputs", [])
                    if missing:
                        iterations_summary += f"- Missing outputs: {', '.join(missing)}\n"
        
        # Check for existing files in the current directory that might be related to the task
        cwd = os.getcwd()
        existing_files = []
        try:
            import glob
            # Look for files that might be related to the task
            for file_path in glob.glob(os.path.join(cwd, "*.md")) + glob.glob(os.path.join(cwd, "*.txt")):
                if os.path.isfile(file_path):
                    rel_path = os.path.relpath(file_path, cwd)
                    existing_files.append(rel_path)
        except Exception as e:
            logger.error(f"Error checking for existing files: {str(e)}")
            
        files_info = ""
        if existing_files:
            files_info = "Files already in workspace:\n"
            for file_path in existing_files:
                files_info += f"- {file_path}\n"
        
        current_result = memory["current_result"]
        result_summary = ""
        if current_result is not None:
            # Format and truncate the result for readability
            if isinstance(current_result, str):
                result_summary = current_result[:500] + "..." if len(current_result) > 500 else current_result
            else:
                try:
                    result_summary = json.dumps(current_result, indent=2, default=str)
                    if len(result_summary) > 500:
                        result_summary = result_summary[:500] + "...(truncated)"
                except:
                    result_summary = str(current_result)[:500] + "..." if len(str(current_result)) > 500 else str(current_result)
        
        # Add tool details to make better recommendations
        tool_details = ""
        # Get information about all available tools
        useful_tools = list(self.factory.list_tools().keys())
        for tool_name in useful_tools:
            try:
                tool_info = self._get_tool_info(tool_name)
                if tool_info:
                    tool_details += f"\n{tool_name}:\n"
                    tool_details += f"  Description: {tool_info.get('description', 'No description')}\n"
                    params = tool_info.get("parameters", {})
                    if params:
                        tool_details += f"  Parameters: {json.dumps(params, indent=2)[:200]}...\n"
            except:
                pass  # Skip if tool not found
        
        # First iteration vs subsequent iterations
        if not memory["iterations"]:
            # First iteration - no history yet
            try:
                template = self.prompt_manager.load_template("workflows/riv_reflect.md")
                prompt = self.prompt_manager.process_template(
                    template,
                    {
                        "task_description": task.description,
                        "available_tools": available_tools,
                        "available_agents": available_agents,
                        "iterations_summary": iterations_summary,
                        "result_summary": result_summary,
                        "files_info": files_info,
                        "tool_details": tool_details,
                    },
                )
                return prompt
            except Exception as e:
                logger.error(f"Failed to load or process RIV reflect prompt template: {str(e)}")
                raise RuntimeError(
                    "Critical: RIV reflect prompt template missing or invalid. "
                    "Please ensure 'prompts/workflows/riv_reflect.md' exists and is correct."
                ) from e
    
    def _get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific tool.
        
        Args:
            tool_name: Name of the tool to get information about
            
        Returns:
            Dictionary with tool information or None if the tool is not found
        """
        tools = self.factory.list_tools()
        tool = tools.get(tool_name)
        if not tool:
            return None
            
        return {
            "name": tool_name,
            "description": getattr(tool, "description", "No description available"),
            "parameters": getattr(tool, "parameters", {})
        }
    
    def _build_verification_prompt(self, task: TaskStatus, memory: Dict[str, Any], 
                                  action_result: Any, action_error: Optional[str]) -> str:
        """
        Build a prompt for the VERIFY phase to check if the task is complete.
        
        Args:
            task: The task being executed
            memory: The execution memory so far
            action_result: The result of the most recent action
            action_error: Any error that occurred during the action
            
        Returns:
            A prompt string for the LLM to verify
        """
        # Format action result for readability
        if action_result is not None:
            if isinstance(action_result, str):
                result_text = action_result[:1000] + "..." if len(action_result) > 1000 else action_result
            else:
                try:
                    result_text = json.dumps(action_result, indent=2, default=str)
                    if len(result_text) > 1000:
                        result_text = result_text[:1000] + "...(truncated)"
                except:
                    result_text = str(action_result)[:1000] + "..." if len(str(action_result)) > 1000 else str(action_result)
        else:
            result_text = "No result produced."
        
        # Add error information if present
        error_text = f"ERROR: {action_error}" if action_error else "No errors."
        
        # Create a summary of all previous iterations and results
        iteration_count = len(memory.get("iterations", []))
        history_summary = ""
        if iteration_count > 0:
            history_summary = f"This is iteration {iteration_count}. Previous steps include:\n"
            for i, iter_data in enumerate(memory.get("iterations", []), 1):
                action = iter_data.get("action", {})
                action_type = action.get("type", "unknown")
                
                # Add specific details based on action type
                if action_type == "use_tool":
                    tool_name = action.get("details", {}).get("tool", "unknown")
                    history_summary += f"- Iteration {i}: Used tool '{tool_name}'\n"
                else:
                    history_summary += f"- Iteration {i}: Performed {action_type}\n"
        
        # Check for all files created or modified in the current workspace
        cwd = os.getcwd()
        files_created = []
        try:
            import glob
            for md_file in glob.glob(os.path.join(cwd, "*.md")):
                if os.path.isfile(md_file):
                    rel_path = os.path.relpath(md_file, cwd)
                    files_created.append(rel_path)
        except Exception as e:
            logger.error(f"Error checking for created files: {str(e)}")

        files_info = ""
        if files_created:
            files_info = "Files found in workspace:\n"
            for file_path in files_created:
                files_info += f"- {file_path}\n"
                try:
                    full_path = os.path.join(cwd, file_path)
                    if os.path.getsize(full_path) < 5000:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            files_info += f"Content of {file_path}:\n```\n{content}\n```\n"
                except Exception as e:
                    files_info += f"(Error reading file: {str(e)})\n"
        else:
            files_info = "No files have been created or modified in the workspace."

        # Format action result
        if action_result is not None:
            try:
                if isinstance(action_result, str):
                    result_text = action_result[:1000] + "..." if len(action_result) > 1000 else action_result
                else:
                    result_text = json.dumps(action_result, indent=2, default=str)
                    if len(result_text) > 1000:
                        result_text = result_text[:1000] + "...(truncated)"
            except:
                result_text = str(action_result)[:1000] + "..." if len(str(action_result)) > 1000 else str(action_result)
        else:
            result_text = "No result produced."

        error_text = f"ERROR: {action_error}" if action_error else "No errors."

        # Build history summary
        iteration_count = len(memory.get("iterations", []))
        history_summary = ""
        if iteration_count > 0:
            history_summary = f"This is iteration {iteration_count}. Previous steps include:\n"
            for i, iter_data in enumerate(memory.get("iterations", []), 1):
                action = iter_data.get("action", {})
                action_type = action.get("type", "unknown")
                if action_type == "use_tool":
                    tool_name = action.get("details", {}).get("tool", "unknown")
                    history_summary += f"- Iteration {i}: Used tool '{tool_name}'\n"
                else:
                    history_summary += f"- Iteration {i}: Performed {action_type}\n"

        try:
            template = self.prompt_manager.load_template("workflows/riv_verify.md")
            prompt = self.prompt_manager.process_template(
                template,
                {
                    "task_description": task.description,
                    "history_summary": history_summary,
                    "result_text": result_text,
                    "files_info": files_info,
                    "error_text": error_text,
                },
            )
            return prompt
        except Exception as e:
            logger.error(f"Failed to load or process RIV verify prompt template: {str(e)}")
            raise RuntimeError(
                "Critical: RIV verify prompt template missing or invalid. "
                "Please ensure 'prompts/workflows/riv_verify.md' exists and is correct."
            ) from e
