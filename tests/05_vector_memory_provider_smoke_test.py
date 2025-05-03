import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from tinyagent.utils.vector_memory import VectorMemory
from tinyagent.utils.embedding_provider import (
    OpenAIEmbeddingProvider, LocalEmbeddingProvider
)
import os

@pytest.fixture
def local_vector_memory(tmp_path):
    provider = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")
    vm = VectorMemory(
        persistence_directory=str(tmp_path / "chroma_local"),
        collection_name="test_collection_local",
        embedding_provider=provider
    )
    vm.clear()
    return vm

def test_vector_memory_with_local_provider(local_vector_memory):
    vm = local_vector_memory
    vm.add("user", "Local embedding test message.")
    results = vm.fetch("embedding test", k=1)
    assert results, "No results returned for local provider."
    assert results[0]["role"] == "user"
    assert "content" in results[0]

@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set.")
@pytest.mark.forked
def test_vector_memory_with_openai_provider(tmp_path):
    provider = OpenAIEmbeddingProvider(
    model_name="text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY")
)
    vm = VectorMemory(
        persistence_directory=str(tmp_path / "chroma_openai"),
        collection_name="test_collection_openai",
        embedding_provider=provider
    )
    vm.clear()
    vm.add("user", "OpenAI embedding test message.")
    results = vm.fetch("embedding test", k=1)
    assert results, "No results returned for OpenAI provider."
    assert results[0]["role"] == "user"
    assert "content" in results[0]

    provider = OpenAIEmbeddingProvider(model_name="text-embedding-3-small", api_key=os.getenv("OPENAI_API_KEY"))
    vm = VectorMemory(
        persistence_directory=str(tmp_path / "chroma_openai"),
        collection_name="test_collection_openai",
        embedding_provider=provider
    )
    vm.clear()
    vm.add("user", "OpenAI embedding test message.")
    results = vm.fetch("embedding test", k=1)
    print("Fetch results (openai):", results)
    assert results, "No results returned for OpenAI provider."
    print("OpenAI provider smoke test passed.")

if __name__ == "__main__":
    test_vector_memory_with_local_provider()
    test_vector_memory_with_openai_provider()