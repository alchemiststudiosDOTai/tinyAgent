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
        self.logger.info("===== PHASE 1: INFORMATION GATHERING =====")
        self.logger.info(f"Task: {task_description[:100]}...")
        self.logger.info("="*80)
        
        # Use LLM to analyze what information is needed
        llm = self.orchestrator.factory.llm if hasattr(self.orchestrator.factory, 'llm') else None
        if not llm:
            # Fall back to get_llm function from agent module
            from ..agent import get_llm
            llm = get_llm()
        
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
            raw_analysis = llm(gather_prompt)
            analysis = self._parse_json_response(raw_analysis)
            
            # Run tools to gather the recommended information if needed
            # (This would be expanded in a full implementation)
            
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
        self.logger.info("===== PHASE 2: SOLUTION PLANNING =====")
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
            raw_plan = llm(plan_prompt)
            plan = self._parse_json_response(raw_plan)
            
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
        Phase 3: Execute the plan.
        
        This phase carries out the solution plan created in Phase 2, using
        appropriate tools and agents.
        
        Args:
            task_description: Description of the task
            plan: The solution plan from Phase 2
            
        Returns:
            Dictionary with execution results
        """
        self.logger.info("="*80)
        self.logger.info("===== PHASE 3: EXECUTION =====")
        self.logger.info(f"Task: {task_description[:100]}...")
        self.logger.info("="*80)
        
        # Get execution agent (could be a specialized agent or the triage agent)
        executor_agent = self.orchestrator.agents.get("triage")
        
        # In a full implementation, we would:
        # 1. Process each step in the plan
        # 2. Use the appropriate tools or agents for each step
        # 3. Track progress and handle errors
        
        # For this simplified version, we'll just pass the plan to the executor agent
        from ..agent import get_llm
        llm = get_llm()
        
        # Format the plan for the prompt
        plan_summary = "No plan available."
        if plan.get("plan"):
            plan_summary = json.dumps(plan.get("plan"), indent=2)
        
        # Create a prompt for execution
        execute_prompt = f"""
        As the Executor, your role is to carry out the following solution plan for this task:
        
        Task: {task_description}
        
        Solution plan:
        {plan_summary}
        
        Please execute this plan and report on your progress and results.
        If you need to use specific tools, please indicate which ones and how they should be used.
        
        Return your execution results in JSON format:
        {{
            "executed_steps": [
                {{
                    "step_number": 1,
                    "description": "Step that was executed",
                    "tools_used": ["tool1", "tool2"],
                    "outcome": "What was accomplished",
                    "success": true/false
                }}
            ],
            "encountered_issues": ["Issue 1", "Issue 2"],
            "final_result": "Description of the overall outcome",
            "success": true/false,
            "next_steps": ["Step 1", "Step 2"] if further action is needed
        }}
        """
        
        # Get execution results from LLM
        try:
            raw_execution = llm(execute_prompt)
            execution_results = self._parse_json_response(raw_execution)
            
            return {
                "execution_results": execution_results,
                "raw_llm_response": raw_execution
            }
        except Exception as e:
            self.logger.error(f"Error in plan execution: {str(e)}")
            return {
                "error": str(e),
                "phase": "plan_execution",
                "raw_llm_response": raw_execution if locals().get('raw_execution') else None
            }
    
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
