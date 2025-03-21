import asyncio
import logging
from datetime import datetime
from elder_brain.task import Task, TaskResult
from elder_brain.agent_type import AgentType
from elder_brain.agent_config import AgentConfig

class Agent:
    # Cache management constants
    MAX_CACHE_SIZE = 1000
    CACHE_EXPIRY_DAYS = 30
    
    def __init__(self, agent_id: str, agent_type: AgentType, config: AgentConfig):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.config = config
        self.context = {}
        self.message_queue = asyncio.Queue()
        self.learning_cache = {}  # Store successful task patterns
        self.logger = logging.getLogger(f"Agent-{agent_id}")
        self.logger.setLevel(logging.INFO)
        
        # Add handler if not already added
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _cleanup_cache(self):
        """Clean up the learning cache based on size and expiration"""
        current_time = datetime.now()
        
        # Remove expired entries
        expired_keys = [
            k for k, v in self.learning_cache.items() 
            if (current_time - datetime.fromisoformat(v['timestamp'])).days > self.CACHE_EXPIRY_DAYS
        ]
        for k in expired_keys:
            del self.learning_cache[k]
            self.logger.debug(f"Removed expired cache entry: {k}")
        
        # Remove oldest entries if cache is too large
        if len(self.learning_cache) >= self.MAX_CACHE_SIZE:
            # Sort by timestamp and remove oldest entries
            sorted_entries = sorted(
                self.learning_cache.items(),
                key=lambda x: x[1]['timestamp']
            )
            entries_to_remove = len(self.learning_cache) - self.MAX_CACHE_SIZE
            for k, _ in sorted_entries[:entries_to_remove]:
                del self.learning_cache[k]
                self.logger.debug(f"Removed oldest cache entry: {k}")

    def _compress_task_data(self, task: Task) -> dict:
        """Compress task data for storage"""
        return {
            'context': {k: v for k, v in task.context.items() if v is not None},
            'parameters': {k: v for k, v in task.parameters.items() if v is not None},
            'timestamp': datetime.now().isoformat()
        }

    async def execute(self, task: Task) -> TaskResult:
        """Execute a task using the agent's capabilities"""
        try:
            # Clean up cache before processing
            self._cleanup_cache()
            
            # Check learning cache for similar tasks
            task_key = f"{task.task_type}_{task.description[:50]}"
            if task_key in self.learning_cache:
                self.logger.info(f"Using learned pattern for task: {task.task_id}")
                learned_pattern = self.learning_cache[task_key]
                # Use learned pattern to enhance execution
                task.context.update(learned_pattern.get('context', {}))
                task.parameters.update(learned_pattern.get('parameters', {}))

            # Execute the task
            result = await self._execute_task(task)
            
            # Store successful pattern in learning cache
            if result.status == "success":
                self.learning_cache[task_key] = self._compress_task_data(task)
                self.logger.debug(f"Stored new pattern in cache for task: {task.task_id}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing task {task.task_id}: {str(e)}")
            return TaskResult(
                task_id=task.task_id,
                status="failed",
                result={"error": str(e)},
                metadata={"agent_id": self.agent_id}
            ) 
