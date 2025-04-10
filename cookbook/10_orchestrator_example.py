import os
import sys
import time
# Add parent directory to the path so we can import the core package: When the pip package is installed, we won't need this
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tinyagent.factory.orchestrator import Orchestrator

def main():
    orchestrator = Orchestrator.get_instance()
    
    # Submit a task that will create a markdown file using our new tool
    task_description = """Research the latest US tariffs and create a comprehensive markdown summary file called tariffs_summary.md"""
    
    # Use the RIV (Reflect-Improve-Verify) execution mode
    task_id = orchestrator.submit_task(
        description=task_description, 
        need_permission=False,
        execution_mode="riv",
        max_iterations=5
    )
    print(f"Submitted task with ID: {task_id}")
    
    # Since RIV processing is asynchronous, we need to wait for completion
    print("Processing task using RIV pattern (may take some time)...")
    
    status = orchestrator.get_task_status(task_id)
    while status.status == "in_progress":
        print(".", end="", flush=True)
        time.sleep(2)
        status = orchestrator.get_task_status(task_id)
    
    print("\nTask completed!")
    print(f"Task Status: {status.status}")
    
    # Print the final result in a formatted way
    if status.result and "final_result" in status.result:
        print("\n=== FINAL RESULT ===")
        
        # If we have a file created, show it
        if os.path.exists("tariffs_summary.md"):
            print("\n=== CREATED FILE: tariffs_summary.md ===")
            try:
                with open("tariffs_summary.md", "r") as f:
                    print(f.read())
            except Exception as e:
                print(f"Error reading file: {str(e)}")
        else:
            # Show the raw result if no file
            print(status.result["final_result"])
        
        # If you want to see the execution history
        if "execution_memory" in status.result and "iterations" in status.result["execution_memory"]:
            print(f"\n=== EXECUTION SUMMARY ({status.result.get('iterations_completed', 0)} iterations) ===")
            for i, iteration in enumerate(status.result["execution_memory"]["iterations"], start=1):
                print(f"Iteration {i}:")
                
                reflection = iteration.get("reflection", {})
                action = iteration.get("action", {})
                verification = iteration.get("verification", {})
                
                print(f"  - Action: {action.get('type', 'unknown')}")
                if action.get("type") == "use_tool":
                    tool_name = action.get("details", {}).get("tool", "unknown")
                    print(f"  - Tool: {tool_name}")
                print(f"  - Success: {action.get('error') is None}")
                print(f"  - Verified: {verification.get('quality', 'unknown')}")
    else:
        print("No structured result available")
    
    print("\nTask ID for reference:", task_id)

if __name__ == "__main__":
    main()