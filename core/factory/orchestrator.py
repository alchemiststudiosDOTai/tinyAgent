"""
Orchestrator module for coordinating multiple agents.

This module provides an orchestrator that manages and coordinates multiple agents
to accomplish complex tasks, handling task delegation, agent coordination, and
result integration.
"""
#this file is over 1000 lines, it is only this long for debugging purposes
import json
import time
import re
import os
import threading
from typing import Dict, List, Any, Optional, Union, TypeVar, Type, cast
from dataclasses import dataclass, field

from ..logging import get_logger
from ..agent import Agent, get_llm
from ..config import load_config, get_config_value
from ..exceptions import OrchestratorError, AgentNotFoundError
from .dynamic_agent_factory import DynamicAgentFactory
from .elder_brain import ElderBrain

# Set up logger with more detailed formatting
logger = get_logger(__name__)

# Add structured logging helper with reasoning
def log_task_event(task_id: str, event: str, details: Dict[str, Any] = None, level: str = "info", reasoning: str = None):
    """Helper function for structured task logging with reasoning"""
    log_data = {
        "task_id": task_id,
        "event": event,
        "timestamp": time.time(),
        "details": details or {},
        "reasoning": reasoning
    }
    if level == "info":
        logger.info(f"Task Event: {json.dumps(log_data)}")
    elif level == "error":
        logger.error(f"Task Event: {json.dumps(log_data)}")
    elif level == "debug":
        logger.debug(f"Task Event: {json.dumps(log_data)}")

def log_decision(task_id: str, decision: str, context: Dict[str, Any], reasoning: str):
    """Helper function for logging decisions with context and reasoning"""
    log_data = {
        "task_id": task_id,
        "decision": decision,
        "context": context,
        "reasoning": reasoning,
        "timestamp": time.time()
    }
    logger.info(f"Decision Log: {json.dumps(log_data)}")

def log_section_header(title: str):
    """Helper function for logging section headers with visual separators"""
    separator = "=" * 50
    logger.info(f"\n{separator}")
    logger.info(f"{title}")
    logger.info(f"{separator}\n")

def log_step(step_number: int, title: str, details: Dict[str, Any], reasoning: str):
    """Helper function for logging steps with clear formatting"""
    logger.info(f"\nStep {step_number}: {title}")
    logger.info("-" * 30)
    logger.info(f"Reasoning: {reasoning}")
    for key, value in details.items():
        logger.info(f"{key}: {value}")
    logger.info("-" * 30)


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
        
        # Load configuration
        if config is None:
            self.config = load_config()
        else:
            self.config = config
        
        # Initialize the triage agent
        self._create_triage_agent()
        
        # Initialize the ElderBrain for phased task processing
        self.elder_brain = ElderBrain(self, self.config)
        
        # Set ElderBrain as default based on config (default to True)
        self.elderbrain_default = get_config_value(self.config, 'elder_brain.default_enabled', True)
        
        logger.info("Orchestrator initialized")
        if self.elderbrain_default:
            logger.info("ElderBrain enabled by default for all tasks")
    
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
    
    def submit_task(self, description: str, need_permission: bool = True) -> str:
        """
        Submit a new task to the orchestrator.
        
        Args:
            description: Natural language description of the task
            need_permission: Whether to ask for permission to create new tools
            
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
                "timestamp": time.time()
            },
            reasoning="Initializing new task with provided description"
        )
        
        # Process the task (would be async in production)
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
            
            # Log the triage result before ElderBrain decision
            log_section_header("ELDERBRAIN DECISION PROCESS")
            log_step(
                step_number=6,
                title="STEP 1: Initial Triage Analysis",
                details={
                    "assessment": triage_result.get("assessment"),
                    "use_phased_flow": triage_result.get("use_phased_flow", False),
                    "requires_new_agent": triage_result.get("requires_new_agent", False),
                    "elderbrain_default": self.elderbrain_default,
                    "has_tool": "tool" in triage_result,
                    "has_arguments": "arguments" in triage_result
                },
                reasoning="Analyzing whether task requires ElderBrain processing"
            )
            
            # Check if this task should use the phased approach
            if triage_result.get("use_phased_flow", False) or triage_result.get("assessment") == "phased":
                log_step(
                    step_number=7,
                    title="STEP 2: ElderBrain ACTIVATED",
                    details={
                        "use_phased_flow": triage_result.get("use_phased_flow", False),
                        "assessment": triage_result.get("assessment"),
                        "elderbrain_default": self.elderbrain_default,
                        "reasoning": triage_result.get("reasoning", "No specific reasoning provided")
                    },
                    reasoning="Task complexity or configuration requires ElderBrain processing"
                )
                
                # Process the task using the ElderBrain's three-phase approach
                result = self.elder_brain.process_phased_task(task)
                task.result = result
                task.status = "completed" if result.get("success", False) else "failed"
                
                log_step(
                    step_number=8,
                    title="STEP 3: ElderBrain Results",
                    details={
                        "status": task.status,
                        "success": result.get("success", False),
                        "duration": time.time() - task.started_at,
                        "phases_completed": list(result.get("phases", {}).keys())
                    },
                    reasoning=f"ElderBrain processing completed with {'success' if result.get('success', False) else 'failure'}"
                )
                
                if not result.get("success", False):
                    task.error = result.get("error", "Unknown error in phased processing")
                task.completed_at = time.time()
                return
            else:
                log_step(
                    step_number=7,
                    title="STEP 2: ElderBrain NOT ACTIVATED",
                    details={
                        "assessment": triage_result.get("assessment"),
                        "use_phased_flow": triage_result.get("use_phased_flow", False),
                        "elderbrain_default": self.elderbrain_default,
                        "reasoning": triage_result.get("reasoning", "No specific reasoning provided"),
                        "next_action": "Proceeding with direct handling"
                    },
                    reasoning="Task does not require ElderBrain processing - proceeding with direct handling"
                )
            
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
        
        # Use the triage template for better format flexibility
        triage_template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'prompts', 'workflows', 'triage.md')
        
        # Check if the template exists
        if os.path.exists(triage_template_path):
            logger.debug(f"Using triage template: {triage_template_path}")
            try:
                with open(triage_template_path, 'r', encoding='utf-8') as f:
                    triage_template = f.read()
                    
                # Replace template variables
                import string
                template_obj = string.Template(triage_template.replace("{{", "${").replace("}}", "}"))
                
                variables = {
                    "query": task.description,
                    "tools": ', '.join(self.factory.list_tools().keys()),
                    "agents": ', '.join(list(self.agents.keys()) + dynamic_agent_ids),
                    "reasoning": reasoning_from_check
                }
                
                triage_prompt = template_obj.safe_substitute(variables)
                logger.debug("Using template for triage prompt")
            except Exception as e:
                logger.error(f"Error using triage template: {str(e)}")
                # Fall back to the default prompt
                triage_prompt = f"""
                As the triage agent, analyze the following task and determine the best way to handle it:
                
                Task: {task.description}
                
                Available agents: {', '.join(list(self.agents.keys()) + dynamic_agent_ids)}
                Available tools: {', '.join(self.factory.list_tools().keys())}
                
                Initial capability assessment: {reasoning_from_check}
                
                Please decide whether:
                1. You can handle this task directly with existing tools
                2. Another existing agent should handle it
                3. We need to create a new specialized agent
                
                IMPORTANT: Your response MUST be a valid JSON object with the following structure:
                {{
                    "assessment": "direct|delegate|create_new",
                    "agent_id": "agent_id_if_delegating",
                    "requires_new_agent": true/false,
                    "required_tools": ["tool1", "tool2"] if using existing tools,
                    "reasoning": "Your reasoning for this decision"
                }}
                """
        else:
            logger.warning(f"Triage template not found at {triage_template_path}, using default prompt")
            # Default prompt if template doesn't exist
            triage_prompt = f"""
            As the triage agent, analyze the following task and determine the best way to handle it:
            
            Task: {task.description}
            
            Available agents: {', '.join(list(self.agents.keys()) + dynamic_agent_ids)}
            Available tools: {', '.join(self.factory.list_tools().keys())}
            
            Initial capability assessment: {reasoning_from_check}
            
            Please decide whether:
            1. You can handle this task directly with existing tools
            2. Another existing agent should handle it
            3. We need to create a new specialized agent
            
            IMPORTANT: Your response MUST be a valid JSON object with the following structure:
            {{
                "assessment": "direct|delegate|create_new",
                "agent_id": "agent_id_if_delegating",
                "requires_new_agent": true/false,
                "required_tools": ["tool1", "tool2"] if using existing tools,
                "reasoning": "Your reasoning for this decision"
            }}
            
            Alternative format for direct tool usage:
            {{
                "tool": "tool_name",
                "arguments": {{
                    "param1": value1,
                    "param2": "string_value"
                }}
            }}
            """
        
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
                        # Apply ElderBrain by default if configured and not a direct tool call
                        if self.elderbrain_default and not "tool" in parsed_result:
                            parsed_result["use_phased_flow"] = True
                            logger.info(f"Applied ElderBrain to task {task.task_id} based on default configuration")
                        return parsed_result
                    except json.JSONDecodeError:
                        pass
                        
                # Strategy 2: Try parsing entire content as JSON
                try:
                    parsed_result = json.loads(result)
                    # Apply ElderBrain by default if configured and not a direct tool call
                    if self.elderbrain_default and "tool" not in parsed_result:
                        parsed_result["use_phased_flow"] = True
                        logger.info(f"Applied ElderBrain to task {task.task_id} based on default configuration")
                    return parsed_result
                except json.JSONDecodeError:
                    # Check if this looks like a chat response rather than a JSON response
                    if isinstance(result, str) and len(result.strip()) > 0 and "{" not in result and "}" not in result:
                        logger.warning(f"Triage returned chat response instead of JSON format: {result[:100]}...")
                        # Extract any assessment-like keywords to make a best guess
                        assessment = "direct"  # Default
                        if re.search(r'\b(phased|multi-step|research|planning|implementation)\b', result, re.IGNORECASE):
                            assessment = "phased"
                        elif re.search(r'\b(new agent|specialized|create agent)\b', result, re.IGNORECASE):
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
                        
                    # Apply ElderBrain by default if configured
                    if self.elderbrain_default:
                        default_result["use_phased_flow"] = True
                        logger.info(f"Applied ElderBrain to task {task.task_id} based on default configuration")
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
            # Apply ElderBrain by default if configured
            if self.elderbrain_default:
                fallback_result["use_phased_flow"] = True
                logger.info(f"Applied ElderBrain to task {task.task_id} based on default configuration (in fallback)")
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
