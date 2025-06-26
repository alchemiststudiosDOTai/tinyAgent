# ChromaDB Test Instance Conflict Fix
**Date: January 6, 2025**

## Issue
The OpenAI vector memory test (`tests/06_vector_memory_openai_smoke_test.py`) was failing with the error:
```
ValueError: An instance of Chroma already exists for ephemeral with different settings
```

This occurred because ChromaDB maintains a singleton pattern with shared state across tests, causing conflicts when multiple tests tried to create ChromaDB instances.

## Root Cause
ChromaDB uses a shared system client (`chromadb.api.shared_system_client.SharedSystemClient`) that maintains a dictionary of instances (`_identifier_to_system`). When tests run in sequence, the previous test's ChromaDB instance remains in memory, preventing new tests from creating instances with different settings.

## Solution Implemented
Updated both vector memory test files to properly clean up ChromaDB state:

### Files Modified
1. `tests/05_vector_memory_local_smoke_test.py`
2. `tests/06_vector_memory_openai_smoke_test.py`

### Key Changes
1. **Added ChromaDB import** to access internal state
2. **Pre-test cleanup**: Clear ChromaDB's shared state and remove persistence directories
3. **Post-test cleanup**: Reset ChromaDB state again and clean up directories

### Code Implementation
```python
@pytest.fixture
def vector_memory(embedding_provider):
    test_dir = ".test_chroma_memory_[local/openai]"
    
    # Clean up any existing ChromaDB instances
    try:
        # Reset ChromaDB's shared system state
        if hasattr(chromadb.api.shared_system_client.SharedSystemClient, '_identifier_to_system'):
            chromadb.api.shared_system_client.SharedSystemClient._identifier_to_system.clear()
    except Exception:
        pass
    
    # Remove directory if it exists
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    
    # Create fresh VectorMemory instance
    vm = VectorMemory(
        persistence_directory=test_dir,
        collection_name="test_collection_[local/openai]",
        embedding_provider=embedding_provider,
    )
    vm.clear()
    
    yield vm
    
    # Cleanup after test
    try:
        # Reset ChromaDB state again
        if hasattr(chromadb.api.shared_system_client.SharedSystemClient, '_identifier_to_system'):
            chromadb.api.shared_system_client.SharedSystemClient._identifier_to_system.clear()
    except Exception:
        pass
    
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
```

## Results
- Before fix: 18 tests passing, 1 error (OpenAI vector memory test)
- After fix: 19 tests passing, 0 errors
- All tests now run successfully without ChromaDB conflicts

## Lessons Learned
1. Singleton patterns in dependencies can cause test isolation issues
2. Always clean up shared state in test fixtures
3. Both pre-test and post-test cleanup are important for reliability
4. ChromaDB's internal state management requires special handling in test environments

## Future Considerations
- Consider using unique collection names with timestamps/UUIDs for each test run
- Investigate ChromaDB's test utilities for better test isolation
- Add this cleanup pattern to any new tests using ChromaDB