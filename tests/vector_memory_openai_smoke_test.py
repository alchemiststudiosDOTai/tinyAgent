import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from tinyagent.utils.vector_memory import VectorMemory
from tinyagent.utils.embedding_provider import OpenAIEmbeddingProvider

def test_vector_memory_with_openai_provider():
    print("\n[VectorMemory Smoke Test: OpenAIEmbeddingProvider]")
    # NOTE: This test requires a valid OpenAI API key in env or config
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Skipping OpenAI provider test: OPENAI_API_KEY not set.")
        return
    provider = OpenAIEmbeddingProvider(model_name="text-embedding-3-small", api_key=api_key)
    vm = VectorMemory(
        persistence_directory=".test_chroma_memory_openai",
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
    test_vector_memory_with_openai_provider() 