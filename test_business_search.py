from core.tools.business_deepsearch import business_deepsearch_tool
import json
import os
from datetime import datetime

def load_latest_state(search_term: str) -> dict:
    """Load the latest search state for a given search term."""
    output_dir = os.path.join("tinyAgent_output", "business_research")
    if not os.path.exists(output_dir):
        return None
        
    # Find the most recent directory for this search term
    dirs = [d for d in os.listdir(output_dir) if d.startswith("query_")]
    if not dirs:
        return None
        
    latest_dir = max(dirs, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
    state_path = os.path.join(output_dir, latest_dir, "search_state.json")
    
    if os.path.exists(state_path):
        try:
            with open(state_path, 'r') as f:
                state = json.load(f)
                if state.get("search_term") == search_term:
                    return state
        except Exception as e:
            print(f"Error loading state: {e}")
    return None

def main():
    search_term = "kratom"
    
    # Try to load previous state
    resume_state = load_latest_state(search_term)
    if resume_state:
        print(f"\nFound previous search state from {resume_state.get('start_time', 'unknown')}")
        print(f"Completed queries: {len(resume_state.get('completed_queries', []))}")
        print(f"Failed queries: {len(resume_state.get('failed_queries', []))}")
        resume = input("Would you like to resume from this state? (y/n): ").lower() == 'y'
        if not resume:
            resume_state = None
    
    # Perform the search
    result = business_deepsearch_tool.search(
        search_term,
        max_results=5,
        resume_state=resume_state
    )
    
    # Print the results
    print("\nSearch Results:")
    print("=" * 50)
    
    # Print search state
    if 'search_state' in result:
        state = result['search_state']
        print("\nSearch State:")
        print("-" * 50)
        print(f"Start time: {state.get('start_time', 'unknown')}")
        print(f"End time: {state.get('end_time', 'unknown')}")
        print(f"Total queries: {state.get('total_queries', 0)}")
        print(f"Completed queries: {state.get('completed_count', 0)}")
        print(f"Failed queries: {state.get('failed_count', 0)}")
        print(f"Total results: {state.get('total_results', 0)}")
        
        if state.get('failed_queries'):
            print("\nFailed Queries:")
            for failed in state['failed_queries']:
                print(f"  - {failed.get('query', 'Unknown')}: {failed.get('error', 'Unknown error')}")
    
    # Print processed data
    if 'processed_data' in result:
        print("\nProcessed Data:")
        print("-" * 50)
        processed_data = result['processed_data']
        for category, items in processed_data.items():
            if category not in ['search_term', 'timestamp']:
                print(f"\n{category.upper()}:")
                for item in items:
                    if isinstance(item, dict):
                        for key, value in item.items():
                            print(f"  {key}: {value}")
                    else:
                        print(f"  - {item}")
    
    # Print save results
    if 'save_results' in result:
        print("\nSave Results:")
        print("-" * 50)
        save_results = result['save_results']
        print(f"Success: {save_results.get('success', False)}")
        if 'saved_files' in save_results:
            print("\nSaved Files:")
            for file_path in save_results['saved_files']:
                print(f"  - {file_path}")

if __name__ == "__main__":
    main() 