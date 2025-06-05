import os
import shutil
import sys

import pytest
import chromadb

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from tinyagent.utils.embedding_provider import OpenAIEmbeddingProvider
from tinyagent.utils.vector_memory import VectorMemory


@pytest.fixture
def openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("Skipping OpenAI provider test: OPENAI_API_KEY not set.")
    return api_key


@pytest.fixture
def openai_embedding_provider(openai_api_key):
    return OpenAIEmbeddingProvider(
        model_name="text-embedding-3-small", api_key=openai_api_key
    )


@pytest.fixture
def vector_memory(openai_embedding_provider):
    test_dir = ".test_chroma_memory_openai"
    
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
        collection_name="test_collection_openai",
        embedding_provider=openai_embedding_provider,
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


def test_vector_memory_with_openai_provider(vector_memory):
    """Test that VectorMemory works with OpenAIEmbeddingProvider."""
    # Add a test message
    test_message = "OpenAI embedding test message."
    vector_memory.add("user", test_message)

    # Fetch results and verify
    results = vector_memory.fetch("embedding test", k=1)

    # Assert that results were returned
    assert results, "No results returned for OpenAI provider."
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
