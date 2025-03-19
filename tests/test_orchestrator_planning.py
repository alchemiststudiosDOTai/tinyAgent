"""Tests for the Orchestrator and ElderBrain planning phase."""

import unittest
from unittest.mock import patch, MagicMock, call
import json
from typing import Dict, Any, List

# Add parent directory to path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "...")))

from core.factory.orchestrator import Orchestrator, TaskStatus
from core.factory.elder_brain import ElderBrain
from core.exceptions import OrchestratorError


class TestOrchestratorPlanning(unittest.TestCase):
    """Test the Orchestrator and ElderBrain planning functionality."""

    def setUp(self):
        """Set up the test environment with mocked components."""
        # Create a test configuration
        self.config = {
            "elder_brain": {
                "default_enabled": True,
                "verbosity": 2,
                "model": "test-model"
            }
        }
        
        # Create a patch for get_llm to avoid actual API calls
        self.llm_patcher = patch('core.agent.get_llm')
        self.mock_get_llm = self.llm_patcher.start()
        
        # Create a mock LLM function that will be returned by get_llm
        self.mock_llm = MagicMock()
        self.mock_get_llm.return_value = self.mock_llm
        
        # Set up the orchestrator with our mocked components
        self.orchestrator = Orchestrator(self.config)
        
        # Create a direct reference to the ElderBrain for testing
        self.elder_brain = self.orchestrator.elder_brain
    
    def tearDown(self):
        """Clean up after the tests."""
        self.llm_patcher.stop()
    
    def test_elderbrain_planning_phase(self):
        """Test that the ElderBrain executes the planning phase correctly."""
        # Configure mock LLM responses for the three phases
        research_response = json.dumps({
            "research": [
                {"topic": "API Structure", "details": "The API follows REST principles."}, 
                {"topic": "Authentication", "details": "Uses JWT tokens for auth."}
            ]
        })
        
        plan_response = json.dumps({
            "plan": [
                {"step": 1, "action": "Initialize REST client", "details": "Create a client instance"}, 
                {"step": 2, "action": "Request auth token", "details": "Authenticate with credentials"}, 
                {"step": 3, "action": "Execute API call", "details": "Send the request and parse response"}
            ]
        })
        
        execution_response = "API call was successful with response: {\"status\": \"success\", \"data\": {\"result\": 42}}"
        
        # Configure the mock to return our predefined responses
        self.mock_llm.side_effect = [research_response, plan_response, execution_response]
        
        # Call the process_task method with our test task
        task_id = self.orchestrator.create_task("Process API request for data")
        
        # Mock the task as assigned to elder_brain
        task = self.orchestrator.tasks[task_id]
        task.assigned_agent = "elder_brain"
        
        # Process the task with ElderBrain
        result = self.elder_brain.process_task(task_id, "Process API request for data")
        
        # Verify the LLM was called for each phase
        self.assertEqual(self.mock_llm.call_count, 3)
        
        # Verify the final result contains our execution response
        self.assertIn("API call was successful", result)
        
        # Verify the task was marked as completed
        self.assertEqual(self.orchestrator.tasks[task_id].status, "completed")
    
    def test_orchestrator_task_delegation(self):
        """Test that the Orchestrator correctly delegates tasks to agents."""
        # Create a mock for the triage agent
        self.orchestrator.agents["triage"] = MagicMock()
        self.orchestrator.agents["triage"].run.return_value = json.dumps({
            "tool": "elder_brain",
            "arguments": {"query": "Complex task requiring planning"}
        })
        
        # Create a mock for the elder_brain process_task method
        self.elder_brain.process_task = MagicMock()
        self.elder_brain.process_task.return_value = "Task completed successfully"
        
        # Execute a task through the orchestrator
        result = self.orchestrator.execute_task("Complex task requiring planning")
        
        # Verify the triage agent was called to analyze the task
        self.orchestrator.agents["triage"].run.assert_called_once()
        
        # Verify the elder_brain was called to process the task
        self.elder_brain.process_task.assert_called_once()
        
        # Verify we got the expected result
        self.assertEqual(result, "Task completed successfully")
    
    def test_task_status_tracking(self):
        """Test that task status is correctly tracked through the workflow."""
        # Create a new task
        task_id = self.orchestrator.create_task("Track this task through the workflow")
        
        # Verify initial status
        self.assertEqual(self.orchestrator.tasks[task_id].status, "pending")
        
        # Update task to in_progress
        self.orchestrator.update_task_status(task_id, "in_progress", assigned_agent="test_agent")
        self.assertEqual(self.orchestrator.tasks[task_id].status, "in_progress")
        self.assertEqual(self.orchestrator.tasks[task_id].assigned_agent, "test_agent")
        
        # Update task to completed with a result
        result = "Task completed with test result"
        self.orchestrator.update_task_status(task_id, "completed", result=result)
        self.assertEqual(self.orchestrator.tasks[task_id].status, "completed")
        self.assertEqual(self.orchestrator.tasks[task_id].result, result)
        
        # Verify completed_at was set
        self.assertIsNotNone(self.orchestrator.tasks[task_id].completed_at)


if __name__ == "__main__":
    unittest.main()
