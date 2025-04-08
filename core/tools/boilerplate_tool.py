"""
Boilerplate template for creating new tools in the tinyAgent framework.

This file demonstrates a complete tool implementation with:
- Parameter validation
- Security checks
- Rate limiting
- Error handling
- Logging
- Documentation
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from ..tool import Tool, ParamType
from ..logging import get_logger
from ..exceptions import ToolError, RateLimitExceeded

# Set up logger
logger = get_logger(__name__)

class BoilerplateTool:
    """
    Example tool implementation demonstrating key framework features.
    
    Attributes:
        rate_limit: Maximum allowed calls per minute
        call_history: Timestamps of recent calls for rate limiting
    """
    def __init__(self, rate_limit: int = 10):
        self.rate_limit = rate_limit
        self.call_history: List[datetime] = []

    def validate_arguments(self, params: Dict[str, Any]) -> None:
        """
        Validate input parameters against expected types and values.
        
        Args:
            params: Dictionary of parameters to validate
            
        Raises:
            ValueError: If any parameter is invalid
        """
        required_params = {
            'input_data': ParamType.STRING,
            'max_items': ParamType.INTEGER
        }
        
        for param, ptype in required_params.items():
            if param not in params:
                raise ValueError(f"Missing required parameter: {param}")
                
            if not isinstance(params[param], ptype.value):
                raise ValueError(f"{param} must be {ptype}")

    def check_rate_limit(self) -> None:
        """Enforce rate limiting using sliding window algorithm."""
        now = datetime.now()
        # Remove calls older than 1 minute
        self.call_history = [t for t in self.call_history if (now - t).seconds < 60]
        
        if len(self.call_history) >= self.rate_limit:
            raise RateLimitExceeded(
                f"Rate limit exceeded ({self.rate_limit} calls/minute)"
            )

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Main execution method with full error handling and validation.
        
        Example NLP query for agent:
        "Create a tool that processes input data with max items limit"
        """
        try:
            self.check_rate_limit()
            self.validate_arguments(kwargs)
            
            # Record successful call
            self.call_history.append(datetime.now())
            
            # Core tool logic
            input_data = kwargs['input_data']
            max_items = kwargs['max_items']
            
            processed = [
                item.upper() 
                for item in input_data.split()[:max_items]
            ]
            
            return {
                'success': True,
                'result': processed,
                'item_count': len(processed)
            }
            
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

# Tool instance for framework integration
boilerplate_tool = Tool(
    name="boilerplate_processor",
    description="Example tool demonstrating key framework features. Processes input data by: "
                "1. Validating parameters "
                "2. Applying rate limiting "
                "3. Converting text items to uppercase "
                "4. Returning processed results",
    parameters={
        'input_data': ParamType.STRING,
        'max_items': ParamType.INTEGER
    },
    func=BoilerplateTool().execute,
    rate_limit=10
)

def get_tool() -> Tool:
    """Standard interface for tool discovery."""
    return boilerplate_tool

# Example test case
if __name__ == "__main__":
    # Test with agent-like invocation
    test_query = "Create a tool that reverses input text and counts the number of characters."
    
    try:
        result = boilerplate_tool(
            input_data="hello world example",
            max_items=2
        )
        
        print("Test successful!")
        print("Input:", "hello world example")
        print("Output:", result)
        
    except ToolError as e:
        print("Test failed:", str(e))

    print("\nExecution Results:")
    print("-" * 40)
    final_result = execution_results.get('execution_results', {}).get('final_result', 'No output')
    print("Final Result:", final_result)
