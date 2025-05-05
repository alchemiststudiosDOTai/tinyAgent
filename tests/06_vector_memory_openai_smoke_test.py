import sys
import os
import pytest
import shutil
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from tinyagent.utils.vector_memory import VectorMemory
from tinyagent.utils.embedding_provider import OpenAIEmbeddingProvider


@pytest.fixture
def openai_api_key():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("Skipping OpenAI provider test: OPENAI_API_KEY not set.")
    return api_key


@pytest.fixture
def openai_embedding_provider(openai_api_key):
    return OpenAIEmbeddingProvider(model_name="text-embedding-3-small", api_key=openai_api_key)


@pytest.fixture
def vector_memory(openai_embedding_provider):
    test_dir = ".test_chroma_memory_openai"
    vm = VectorMemory(
        persistence_directory=test_dir,
        collection_name="test_collection_openai",
        embedding_provider=openai_embedding_provider
    )
    vm.clear()
    yield vm
    # Cleanup after test
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