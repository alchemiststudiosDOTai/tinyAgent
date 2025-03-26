"""
ElderBrain module for implementing a three-phase task processing approach.

This module provides an ElderBrain class that implements a three-phase approach
to task processing:
1. InformationGatherer - Collects relevant data and context
2. SolutionPlanner - Designs an action plan
3. Executor - Implements the solution

The ElderBrain is designed to work alongside the Orchestrator with minimal
integration hooks.
"""

import json
from typing import Dict, Any, Optional, List, Union

from ..logging import get_logger

# Set up logger
logger = get_logger(__name__)


class ElderBrain:
    """
    ElderBrain adds a three-phase approach to task processing:
    1. InformationGatherer - Collects relevant data and context
    2. SolutionPlanner - Designs an action plan
    3. Executor - Implements the solution
    
    This class is designed to work alongside the Orchestrator with minimal
    integration hooks.
    """
    
    def __init__(self, orchestrator, config=None):
        """
        Initialize with reference to orchestrator for tool/agent access.
        
        Args:
            orchestrator: Reference to the Orchestrator instance
            config: Optional configuration dictionary
        """
        self.orchestrator = orchestrator
        self.factory = orchestrator.factory
        self.config = config or {}
        self.logger = logger
    
    def gather_information(self, task_description: str) -> Dict[str, Any]:
        """
        Phase 1: Research and gather relevant information.
        
        This phase collects context, references, and data needed to understand
        the task requirements fully.
        
        Args:
            task_description: Description of the task
            
        Returns:
            Dictionary with gathered information
        """
        self.logger.info("="*80)
        self.logger.info("===== ELDERBRAIN PHASE 1: INFORMATION GATHERING =====")
        self.logger.info(f"Task: {task_description[:100]}...")
        self.logger.info("="*80)
        
        # Use LLM to analyze what information is needed
        llm = self.orchestrator.factory.llm if hasattr(self.orchestrator.factory, 'llm') else None
        if not llm:
            # Fall back to get_llm function from agent module
            from ..agent import get_llm
            llm = get_llm()
        
        self.logger.info("\nAnalyzing information requirements...")
        
        # Create a prompt for information gathering
        gather_prompt = f"""
        As the InformationGatherer, your role is to identify and collect relevant information 
        needed to understand and solve the following task:
        
        Task: {task_description}
        
        Please analyze what information would be helpful to gather, such as:
        1. Related code or documentation that should be examined
        2. External resources that might be relevant
        3. Specific details that need to be clarified
        4. Domain knowledge required to understand the problem
        
        Return your analysis in JSON format:
        {{
            "required_information": [
                {{
                    "type": "code_review|documentation|external_resource|clarification|domain_knowledge",
                    "description": "Specific description of what's needed",
                    "importance": "high|medium|low"
                }}
            ],
            "key_questions": ["Question 1", "Question 2"],
            "recommended_tools": ["tool1", "tool2"],
            "summary": "Brief summary of information gathering strategy"
        }}
        """
        
        # Get analysis from LLM
        try:
            self.logger.info("Requesting information analysis from LLM...")
            raw_analysis = llm(gather_prompt)
            analysis = self._parse_json_response(raw_analysis)
            
            self.logger.info("\nInformation Gathering Results:")
            self.logger.info("-"*40)
            self.logger.info(f"Required Information Types: {[item['type'] for item in analysis.get('required_information', [])]}")
            self.logger.info(f"Key Questions: {len(analysis.get('key_questions', []))}")
            self.logger.info(f"Recommended Tools: {analysis.get('recommended_tools', [])}")
            self.logger.info(f"Summary: {analysis.get('summary', 'No summary provided')}")
            self.logger.info("-"*40)
            
            return {
                "analysis": analysis,
                "collected_information": {},  # Placeholder for actual gathered info
                "raw_llm_response": raw_analysis
            }
        except Exception as e:
            self.logger.error(f"Error in information gathering: {str(e)}")
            return {
                "error": str(e),
                "phase": "information_gathering",
                "raw_llm_response": raw_analysis if locals().get('raw_analysis') else None
            }
    
    def plan_solution(self, task_description: str, info_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 2: Create a detailed solution plan.
        
        This phase designs a step-by-step approach to solving the task based on
        the information gathered in Phase 1.
        
        Args:
            task_description: Description of the task
            info_results: Results from the information gathering phase
            
        Returns:
            Dictionary with solution plan
        """
        self.logger.info("="*80)
        self.logger.info("===== ELDERBRAIN PHASE 2: SOLUTION PLANNING =====")
        self.logger.info(f"Task: {task_description[:100]}...")
        self.logger.info("="*80)
        
        # Similar to gather_information, use LLM to create a plan
        from ..agent import get_llm
        llm = get_llm()
        
        # Format the gathered information for the prompt
        info_summary = "No information gathered."
        analysis = info_results.get("analysis", {})
        if analysis:
            info_summary = json.dumps(analysis, indent=2)
        
        self.logger.info("\nCreating solution plan based on gathered information...")
        
        # Create a prompt for solution planning
        plan_prompt = f"""
        As the SolutionPlanner, your role is to design a step-by-step plan for solving the following task,
        based on the information gathered:
        
        Task: {task_description}
        
        Information gathered:
        {info_summary}
        
        Please create a detailed plan that includes:
        1. Clear steps to implement the solution
        2. Specific tools or approaches to use for each step
        3. Potential challenges and how to address them
        
        Return your plan in JSON format:
        {{
            "steps": [
                {{
                    "step_number": 1,
                    "description": "Step description",
                    "tools_needed": ["tool1", "tool2"],
                    "expected_outcome": "What this step should accomplish"
                }}
            ],
            "estimated_complexity": "high|medium|low",
            "potential_challenges": ["Challenge 1", "Challenge 2"],
            "success_criteria": ["Criterion 1", "Criterion 2"],
            "summary": "Brief summary of the overall approach"
        }}
        """
        
        # Get plan from LLM
        try:
            self.logger.info("Requesting solution plan from LLM...")
            raw_plan = llm(plan_prompt)
            plan = self._parse_json_response(raw_plan)
            
            self.logger.info("\nSolution Planning Results:")
            self.logger.info("-"*40)
            self.logger.info(f"Number of Steps: {len(plan.get('steps', []))}")
            self.logger.info(f"Estimated Complexity: {plan.get('estimated_complexity', 'unknown')}")
            self.logger.info(f"Potential Challenges: {len(plan.get('potential_challenges', []))}")
            self.logger.info(f"Success Criteria: {len(plan.get('success_criteria', []))}")
            self.logger.info(f"Summary: {plan.get('summary', 'No summary provided')}")
            self.logger.info("-"*40)
            
            return {
                "plan": plan,
                "raw_llm_response": raw_plan
            }
        except Exception as e:
            self.logger.error(f"Error in solution planning: {str(e)}")
            return {
                "error": str(e),
                "phase": "solution_planning",
                "raw_llm_response": raw_plan if locals().get('raw_plan') else None
            }
    
    def execute_plan(self, task_description: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the plan using real agents or tools.

        This method takes a task description and a plan, executes each step with the specified tools,
        manages data between steps via a context, and returns the execution results.

        Args:
            task_description (str): Description of the task to execute.
            plan (dict): Plan containing steps with descriptions and tools_needed.

        Returns:
            dict: Execution results including step outcomes, issues, and final status.
        """
        self.logger.info("="*80)
        self.logger.info("===== ELDERBRAIN PHASE 3: EXECUTION =====")
        self.logger.info(f"Task: {task_description[:100]}...")
        self.logger.info("="*80)

        # Initialize results structure
        execution_results = {
            "executed_steps": [],
            "encountered_issues": [],
            "final_result": "",
            "success": True,
            "next_steps": []
        }

        # Context to store outputs between steps
        context = {
            "task_description": task_description,
            "initial_plan": plan
        }

        # Extract steps from the plan
        steps = plan.get("plan", {}).get("steps", [])
        if not steps:
            error_msg = "No steps found in the plan"
            self.logger.error(error_msg)
            return {
                "error": error_msg,
                "phase": "plan_execution"
            }

        self.logger.info(f"\nStarting execution of {len(steps)} steps...")
        
        # Iterate through each step in the plan
        for step in steps:
            step_number = step.get("step_number", 0)
            description = step.get("description", "Unknown step")
            tools_needed = step.get("tools_needed", [])
            expected_outcome = step.get("expected_outcome", "")

            self.logger.info(f"\nExecuting Step {step_number}:")
            self.logger.info("-"*40)
            self.logger.info(f"Description: {description}")
            self.logger.info(f"Tools Needed: {tools_needed}")
            self.logger.info(f"Expected Outcome: {expected_outcome}")
            self.logger.info("-"*40)

            step_result = {
                "step_number": step_number,
                "description": description,
                "tools_used": [],
                "outcome": "",
                "success": False
            }

            # Retrieve tools for the step
            tools = []
            missing_tools = []
            
            for tool_name in tools_needed:
                # Try to get the tool from the factory
                tool = self.factory.get_tool(tool_name) if hasattr(self.factory, 'get_tool') else None
                
                # If not found through get_tool, check list_tools
                if tool is None and hasattr(self.factory, 'list_tools'):
                    tool_dict = self.factory.list_tools()
                    if tool_name in tool_dict:
                        tool = tool_dict[tool_name]
                
                if tool:
                    tools.append((tool_name, tool))
                    step_result["tools_used"].append(tool_name)
                else:
                    missing_tools.append(tool_name)
                    issue = f"Tool '{tool_name}' not found for step {step_number}"
                    execution_results["encountered_issues"].append(issue)
                    self.logger.warning(issue)

            # If there are missing critical tools, mark the step as problematic
            if missing_tools and not tools:
                step_result["outcome"] = f"Missing tools: {', '.join(missing_tools)}"
                execution_results["executed_steps"].append(step_result)
                execution_results["success"] = False
                continue

            try:
                # Execute each tool in sequence, passing context between them
                step_outputs = {}
                all_tool_success = True
                
                for tool_name, tool in tools:
                    try:
                        self.logger.info(f"Executing tool: {tool_name}")
                        
                        # Handle different tool execution patterns
                        if callable(tool):
                            # If tool is a direct callable
                            tool_result = tool(context)
                        elif hasattr(self.factory, 'execute_tool'):
                            # If factory has execute_tool method
                            tool_args = self._prepare_tool_args(tool_name, context)
                            tool_result = self.factory.execute_tool(tool_name, **tool_args)
                        else:
                            # Fallback for unknown tool pattern
                            issue = f"Don't know how to execute tool '{tool_name}'"
                            execution_results["encountered_issues"].append(issue)
                            self.logger.warning(issue)
                            all_tool_success = False
                            continue
                        
                        # Store result in step outputs
                        step_outputs[tool_name] = tool_result
                        self.logger.info(f"Tool {tool_name} executed successfully")
                        
                    except Exception as e:
                        error_msg = f"Error executing tool '{tool_name}': {str(e)}"
                        self.logger.error(error_msg)
                        execution_results["encountered_issues"].append(error_msg)
                        step_outputs[tool_name] = {"error": str(e)}
                        all_tool_success = False
                
                # Update the context with this step's outputs
                context[f"step_{step_number}_outputs"] = step_outputs
                
                # Determine step success
                step_result["success"] = all_tool_success
                
                # Set step outcome
                if all_tool_success:
                    step_result["outcome"] = expected_outcome or "Step completed successfully"
                else:
                    step_result["outcome"] = "Step completed with issues"
                
                # Record detailed outputs
                step_result["outputs"] = step_outputs
                
            except Exception as e:
                # Handle errors during step execution
                error_msg = f"Error in step {step_number}: {str(e)}"
                step_result["outcome"] = error_msg
                step_result["success"] = False
                execution_results["encountered_issues"].append(error_msg)
                execution_results["success"] = False
                self.logger.error(error_msg)

            # Add step result to the execution log
            execution_results["executed_steps"].append(step_result)
            
            # Check if we should continue after a failed step
            if not step_result["success"] and step.get("critical", False):
                self.logger.warning(f"Critical step {step_number} failed. Stopping execution.")
                break

        # Set the final result based on overall success
        if execution_results["success"]:
            execution_results["final_result"] = "All steps completed successfully"
        else:
            executed_count = len(execution_results["executed_steps"])
            total_count = len(steps)
            execution_results["final_result"] = f"Execution completed with issues. {executed_count}/{total_count} steps executed."

        # Add next steps if applicable (for future enhancements or human intervention)
        if not execution_results["success"]:
            execution_results["next_steps"] = ["Review execution issues", "Retry failed steps manually"]

        self.logger.info(f"Execution completed: {execution_results['final_result']}")
        return {
            "execution_results": execution_results,
            "raw_context": context  # Include context for debugging/analysis
        }

    def _prepare_tool_args(self, tool_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare arguments for a specific tool based on context.
        
        This helper method extracts relevant arguments from the context
        for a specific tool.
        
        Args:
            tool_name: Name of the tool to prepare arguments for
            context: Current execution context
            
        Returns:
            Dictionary of arguments for the tool
        """
        # Default approach: pass the whole context
        # This could be enhanced with tool-specific argument mapping
        return {"context": context}
    
    def process_phased_task(self, task) -> Dict[str, Any]:
        """
        Process a task through all three phases.
        
        Args:
            task: Task object with description and status
            
        Returns:
            Dictionary with results from all phases
        """
        self.logger.info("="*80)
        self.logger.info(f"===== ELDERBRAIN PROCESSING TASK: {task.task_id} =====")
        self.logger.info(f"Task description: {task.description[:100]}...")
        self.logger.info("="*80)
        
        results = {
            "task_id": task.task_id,
            "phases": {}
        }
        
        # Phase 1: Information Gathering
        info_results = self.gather_information(task.description)
        results["phases"]["information_gathering"] = info_results
        
        # Check for errors before proceeding
        if "error" in info_results:
            results["success"] = False
            results["error"] = f"Error in information gathering: {info_results['error']}"
            return results
        
        # Phase 2: Solution Planning
        plan_results = self.plan_solution(task.description, info_results)
        results["phases"]["solution_planning"] = plan_results
        
        # Check for errors before proceeding
        if "error" in plan_results:
            results["success"] = False
            results["error"] = f"Error in solution planning: {plan_results['error']}"
            return results
        
        # Phase 3: Execution
        execution_results = self.execute_plan(task.description, plan_results)
        results["phases"]["execution"] = execution_results
        
        # Determine overall success
        if "error" in execution_results:
            results["success"] = False
            results["error"] = f"Error in execution: {execution_results['error']}"
        else:
            results["success"] = True
            
            # Extract the final result if available
            if execution_results.get("execution_results", {}).get("final_result"):
                results["final_result"] = execution_results["execution_results"]["final_result"]
            else:
                results["final_result"] = "Task completed through all three phases."
        
        return results
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response.
        
        Args:
            response: String response from LLM
            
        Returns:
            Parsed JSON as dictionary
        """
        import re
        import json
        
        # Try to find JSON object using regex
        json_match = re.search(r'({[\s\S]*})', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                # Try the whole string if regex failed
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    self.logger.warning("Could not parse LLM response as JSON")
                    return {"raw_text": response}
        else:
            # No JSON found, return as raw text
            return {"raw_text": response}
