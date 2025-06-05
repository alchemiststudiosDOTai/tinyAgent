import os
import shutil
import sys

import pytest
import chromadb

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from tinyagent.utils.embedding_provider import LocalEmbeddingProvider
from tinyagent.utils.vector_memory import VectorMemory


@pytest.fixture
def local_embedding_provider():
    return LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")


@pytest.fixture
def vector_memory(local_embedding_provider):
    test_dir = ".test_chroma_memory_local"
    
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
        collection_name="test_collection_local",
        embedding_provider=local_embedding_provider,
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


def test_vector_memory_with_local_provider(vector_memory):
    """Test that VectorMemory works with LocalEmbeddingProvider."""
    # Add a test message
    test_message = "Local embedding test message."
    vector_memory.add("user", test_message)

    # Fetch results and verify
    results = vector_memory.fetch("embedding test", k=1)

    # Assert that results were returned
    assert results, "No results returned for local provider."
    assert len(results) == 1, "Expected exactly 1 result"
    assert test_message in results[0]["content"]
    print(f"Successfully retrieved: {results[0]['content']}")


# Only run the test when the file is executed directly
if __name__ == "__main__":
    # This will run pytest with the following arguments:
    # -x: exit on first failure
    # -v: verbose output
    # -s: don't capture stdout (so print statements are shown)
    sys.exit(pytest.main(["-xvs", __file__]))
