    # you need pip install duckduckgo-search for internal search, but you can use any

import time
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field

from tinyagent.agent import Agent
from tinyagent.factory.dynamic_agent_factory import DynamicAgentFactory
from tinyagent.tool import Tool, ParamType
from tinyagent.utils.json_parser import robust_json_parse


@dataclass
class tiny_task:
    """
    tiny_task tracks the state of a submitted user request (a "task").
    """
    task_id: str
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class tiny_chain:
    """
    A robust tiny_chain that:
      1) Maintains a registry of tasks.
      2) Uses a 'triage agent' to determine how to handle each task.
      3) Optionally executes multi-step plans if returned by triage.
      4) Retries or falls back if parsing fails.
    """

    _instance = None  # Singleton reference

    @classmethod
    def get_instance(
        cls,
        config: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Tool]] = None,
        max_retries: int = 2,
    ):
        """
        Get or create the singleton instance of tiny_chain.

        Args:
            config: Optional config dictionary (e.g., loaded from config.yml).
            tools: Optional list of Tool objects to register.
            max_retries: How many times to retry if triage returns malformed or empty responses.
        """
        if cls._instance is None:
            cls._instance = cls(config, tools, max_retries)
        return cls._instance

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Tool]] = None,
        max_retries: int = 2
    ):
        self.config = config or {}
        self.tasks: Dict[str, tiny_task] = {}
        self.agents: Dict[str, Agent] = {}
        self.next_task_id = 1
        self.max_retries = max_retries

        # Create or retrieve the global dynamic factory
        self.factory = DynamicAgentFactory.get_instance(self.config)

        # If the user provided tools, register them
        if tools:
            for tool in tools:
                self.factory.register_tool(tool)

        # Create a triage agent with all known (registered) tools
        triage_agent = self.factory.create_agent(
            tools=list(self.factory.list_tools().values())
        )
        triage_agent.name = "triage_agent"
        triage_agent.description = "Analyzes queries and decides next steps"
        self.agents["triage"] = triage_agent

    def _generate_task_id(self) -> str:
        t_id = f"task_{self.next_task_id}"
        self.next_task_id += 1
        return t_id

    def submit_task(self, description: str) -> str:
        """
        Submit a task (user query) to the tiny_chain.
        1) Creates a new tiny_task and sets status to in_progress.
        2) Calls triage logic to see if we need a multi-step plan, direct tool call, or new agent creation.
        3) Executes accordingly.
        """
        task_id = self._generate_task_id()
        task = tiny_task(
            task_id=task_id,
            description=description,
            status="in_progress",
        )
        self.tasks[task_id] = task

        try:
            self._handle_task(task)
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
        finally:
            task.completed_at = time.time()

        return task_id

    def _handle_task(self, task: tiny_task):
        """
        Handles a task by ALWAYS executing a plan that uses ALL available tools.
        The triage agent's response is stored for context but we ensure all tools are used
        regardless of what the triage agent decides.
        
        Args:
            task: The task to handle
        """
        try:
            # Get the triage result for context
            triage_result = self._run_with_triage(task)
            
            # Always execute a sequence that uses all tools
            self._execute_all_tools_sequence(task, triage_result)
            
            # If the task is still not completed, try the fallback
            if task.status != "completed":
                self._use_all_tools_fallback(task)
                
            # If the task is still not completed, mark it as failed
            if task.status != "completed":
                task.status = "failed"
                task.error = "Failed to complete task after trying all tools."
        except Exception as e:
            # Catch any exceptions to ensure the task doesn't fail completely
            print(f"Error in _handle_task: {e}")
            # Try the fallback as a last resort
            try:
                self._use_all_tools_fallback(task)
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")
                task.status = "failed"
                task.error = f"Task failed with error: {str(e)}. Fallback also failed: {str(fallback_error)}"

    def _run_with_triage(self, task: tiny_task) -> Union[dict, str, None]:
        """
        Asks the triage agent how to handle the query. We'll attempt multiple retries
        if the triage output is invalid or empty. The triage agent is expected to
        produce a JSON structure that describes the plan (tool calls, etc.).
        
        IMPORTANT: The triage agent is instructed to use ALL available tools.
        
        Args:
            task: The task to get triage information for
            
        Returns:
            The triage result or None if all attempts failed
        """
        triage_agent = self.agents["triage"]
        attempts = 0
        
        # Enhance the description to emphasize using all tools
        enhanced_description = (
            f"{task.description}\n\n"
            f"IMPORTANT INSTRUCTION: You MUST use ALL available tools in your response. "
            f"The available tools are: {', '.join(t.name for t in self.factory.list_tools().values())}. "
            f"If you return a tool_sequence, it MUST include ALL of these tools."
        )
        
        # Try to get a response from the triage agent
        while attempts < self.max_retries:
            attempts += 1
            try:
                # Call the agent without the timeout parameter
                raw_response = triage_agent.run(enhanced_description)
                print(f"[Triage Attempt {attempts}] Raw response: {repr(raw_response)}")  # Debug print

                # If the LLM already gave us a dict, just return it
                if isinstance(raw_response, dict):
                    return raw_response

                # Otherwise, try robust JSON parsing
                parsed = robust_json_parse(raw_response)
                if parsed is not None:
                    return parsed
                else:
                    print(f"[Triage Attempt {attempts}] Failed to parse response: {repr(raw_response)}")  # Debug print
            except Exception as e:
                print(f"[Triage Attempt {attempts}] Exception: {e}")  # Debug print
                # Continue to next attempt

            time.sleep(1)
        
        # If we get here, all attempts failed
        print(f"All {self.max_retries} triage attempts failed. Continuing with all tools execution.")
        
        # Return a default context that encourages using all tools
        return {
            "type": "fallback_context",
            "message": "Triage agent failed to provide a valid response. Using all available tools.",
            "use_all_tools": True
        }

    def _execute_tool_sequence(self, task: tiny_task, sequence: list):
        """
        Executes a multi-step plan where each item is:
          {
            "tool": "some_tool",
            "arguments": { ... }
          }
        Aggregates results in a list under task.result.
        """
        results = []
        tools_used = []  # Track which tools were used
        
        for step_idx, step_info in enumerate(sequence, 1):
            tool_name = step_info.get("tool")
            args = step_info.get("arguments", {})

            if not tool_name:
                results.append({"step": step_idx, "error": "No 'tool' provided"})
                continue

            # Lookup the tool
            tool_obj = self.factory.list_tools().get(tool_name)
            if not tool_obj:
                results.append({"step": step_idx, "error": f"Tool '{tool_name}' not found"})
                continue

            # Record that this tool was used
            tools_used.append(tool_name)

            # Invoke the tool
            try:
                step_result = tool_obj.func(**args)
                results.append({
                    "step": step_idx,
                    "tool": tool_name,
                    "arguments": args,
                    "result": step_result
                })
            except Exception as e:
                results.append({
                    "step": step_idx,
                    "tool": tool_name,
                    "arguments": args,
                    "error": str(e)
                })

        # Get all available tools for comparison
        all_tools = [t.name for t in self.factory.list_tools().values()]
        unused_tools = [t for t in all_tools if t not in tools_used]
        
        task.result = {
            "type": "tool_sequence",
            "steps": results,
            "tools_used": tools_used,
            "unused_tools": unused_tools,
            "all_tools": all_tools
        }
        task.status = "completed"

    def _execute_single_tool(self, task: tiny_task, triage_result: dict):
        """
        If the triage says: 
          { "tool": "...", "arguments": {...} }
        """
        tool_name = triage_result["tool"]
        args = triage_result["arguments"]

        tool_obj = self.factory.list_tools().get(tool_name)
        if not tool_obj:
            task.status = "failed"
            task.error = f"Tool '{tool_name}' not found."
            return

        try:
            result = tool_obj.func(**args)
            
            # Get all available tools for comparison
            all_tools = [t.name for t in self.factory.list_tools().values()]
            unused_tools = [t for t in all_tools if t != tool_name]
            
            task.result = {
                "type": "single_tool",
                "tool": tool_name,
                "arguments": args,
                "result": result,
                "tools_used": [tool_name],
                "unused_tools": unused_tools,
                "all_tools": all_tools
            }
            task.status = "completed"
        except Exception as e:
            task.status = "failed"
            task.error = str(e)

    def _create_and_use_new_agent(self, task: tiny_task):
        """
        If triage decides we need a brand-new specialized agent,
        we call DynamicAgentFactory to create it, then run the user's query.
        """
        try:
            specialized_agent = self.factory.create_dynamic_agent(task.description)
            final_result = specialized_agent.run(task.description)
            
            # Get all available tools for comparison
            all_tools = [t.name for t in self.factory.list_tools().values()]
            
            task.result = {
                "type": "new_dynamic_agent",
                "agent_name": specialized_agent.name, # Assuming factory sets a name
                "result": final_result,
                "tools_used": all_tools,  # Assume the dynamic agent uses all tools
                "unused_tools": [],  # No unused tools if dynamic agent uses all
                "all_tools": all_tools
            }
            task.status = "completed"
        except Exception as e:
            task.status = "failed"
            task.error = str(e)

    def _use_all_tools_fallback(self, task: tiny_task):
        """
        Fallback method that ensures all available tools are used.
        This is called when the triage agent doesn't use all tools or fails.
        """
        # Get all available tools
        all_tools = list(self.factory.list_tools().values())
        
        if not all_tools:
            task.status = "failed"
            task.error = "No tools available for fallback."
            return
            
        # Create a tool sequence that uses all available tools
        tool_sequence = []
        tools_used = []  # Track which tools were used
        
        # First, try to use search tools
        search_tools = [t for t in all_tools if "search" in t.name.lower()]
        if search_tools:
            for tool in search_tools:
                tool_sequence.append({
                    "tool": tool.name,
                    "arguments": {"keywords": task.description}
                })
                tools_used.append(tool.name)
                
        # Then, try to use browser tools
        browser_tools = [t for t in all_tools if "browser" in t.name.lower()]
        if browser_tools and tool_sequence:  # Only if we have search results
            for tool in browser_tools:
                # Use the first URL from the first search result if available
                first_result = tool_sequence[0].get("result", {})
                if isinstance(first_result, dict) and "results" in first_result:
                    results = first_result["results"]
                    if results and isinstance(results, list) and len(results) > 0:
                        first_url = results[0].get("href")
                        if first_url:
                            tool_sequence.append({
                                "tool": tool.name,
                                "arguments": {"url": first_url, "action": "visit"}
                            })
                            tools_used.append(tool.name)
                
        # Finally, use any remaining tools
        remaining_tools = [t for t in all_tools 
                          if t not in search_tools and t not in browser_tools]
        for tool in remaining_tools:
            # Try to determine appropriate arguments based on tool parameters
            args = {}
            for param_name, param_type in tool.parameters.items():
                if param_type == ParamType.STRING:
                    args[param_name] = f"Processing task: {task.description}"
                elif param_type == ParamType.INTEGER:
                    args[param_name] = 1
                elif param_type == ParamType.BOOLEAN:
                    args[param_name] = True
                # Add more parameter types as needed
                
            tool_sequence.append({
                "tool": tool.name,
                "arguments": args
            })
            tools_used.append(tool.name)
            
        # Get all tool names for comparison
        all_tool_names = [t.name for t in all_tools]
        unused_tools = [t for t in all_tool_names if t not in tools_used]
        
        # Execute the tool sequence
        self._execute_tool_sequence(task, tool_sequence)
        
        # If the task is still not completed, update it with tool usage information
        if task.status != "completed":
            task.result = {
                "type": "fallback_all_tools",
                "tools_used": tools_used,
                "unused_tools": unused_tools,
                "all_tools": all_tool_names,
                "error": "Fallback execution failed but tools were attempted"
            }
            task.status = "completed"

    def _execute_all_tools_sequence(self, task: tiny_task, _unused_context=None):
        """
        Executes ALL tools in sequence, passing outputs from one tool to the next.
        Each tool's output is used to construct meaningful input for the next tool.
        
        Args:
            task: The task to execute
            _unused_context: Kept for compatibility but not used
        """
        # Get all available tools
        all_tools = list(self.factory.list_tools().values())
        if not all_tools:
            task.status = "failed"
            task.error = "No tools available for execution."
            return
            
        # Initialize our execution sequence and tracking
        tool_sequence = []
        tools_used = []
        execution_context = {
            "task_description": task.description,
            "current_data": None,
            "urls_found": [],
            "search_results": [],
            "browser_results": [],
            "analysis_results": []
        }
        
        # Execute each tool and feed results forward
        for tool in all_tools:
            try:
                # Prepare arguments based on previous results
                args = self._prepare_tool_args(tool, execution_context)
                
                # Execute the tool
                result = tool.func(**args)
                
                # Store the result
                step_result = {
                    "tool": tool.name,
                    "arguments": args,
                    "result": result
                }
                tool_sequence.append(step_result)
                tools_used.append(tool.name)
                
                # Update execution context with new results
                self._update_execution_context(execution_context, tool.name, result)
                
            except Exception as e:
                print(f"Error executing {tool.name}: {e}")
                # Continue with next tool even if this one fails
                
        # Update task with results
        task.result = {
            "type": "tool_chain",
            "steps": tool_sequence,
            "tools_used": tools_used,
            "final_context": execution_context
        }
        task.status = "completed"

    def _prepare_tool_args(self, tool, context):
        """
        Prepares arguments for a tool based on previous results in the context.
        """
        args = {}
        
        # For search tools
        if "search" in tool.name.lower():
            args["keywords"] = context["task_description"]
            
        # For browser tools
        elif "browser" in tool.name.lower():
            # Use the first unused URL from our collected URLs
            unused_urls = [url for url in context["urls_found"] 
                         if url not in [br.get("url") for br in context["browser_results"]]]
            if unused_urls:
                args["url"] = unused_urls[0]
                args["action"] = "visit"
            else:
                # If no URLs from search, use the first search result's content
                args["content"] = str(context["search_results"][0]) if context["search_results"] else context["task_description"]
                
        # For analysis/processing tools
        else:
            # Combine all previous results into a meaningful input
            combined_data = {
                "task": context["task_description"],
                "search_results": context["search_results"],
                "browser_results": context["browser_results"],
                "previous_analysis": context["analysis_results"]
            }
            # Match the tool's parameter types
            for param_name, param_type in tool.parameters.items():
                if param_type == ParamType.STRING:
                    args[param_name] = str(combined_data)
                elif param_type == ParamType.INTEGER:
                    args[param_name] = len(combined_data["search_results"])
                elif param_type == ParamType.BOOLEAN:
                    args[param_name] = bool(combined_data["search_results"])
                    
        return args

    def _update_execution_context(self, context, tool_name, result):
        """
        Updates the execution context with new results from a tool.
        """
        # Handle search results
        if "search" in tool_name.lower():
            if isinstance(result, dict) and "results" in result:
                context["search_results"].extend(result["results"])
                # Extract URLs from search results
                for item in result["results"]:
                    if isinstance(item, dict) and "href" in item:
                        context["urls_found"].append(item["href"])
                        
        # Handle browser results
        elif "browser" in tool_name.lower():
            context["browser_results"].append(result)
            # Extract any new URLs found while browsing
            if isinstance(result, dict):
                if "links" in result:
                    context["urls_found"].extend(result["links"])
                if "url" in result:
                    context["urls_found"].append(result["url"])
                    
        # Handle other tool results
        else:
            context["analysis_results"].append({
                "tool": tool_name,
                "result": result
            })
            
        # Update current_data with latest result
        context["current_data"] = result

    def get_task_status(self, task_id: str) -> Optional[tiny_task]:
        """
        Retrieve the tiny_task object by ID, or None if not found.
        """
        return self.tasks.get(task_id)
