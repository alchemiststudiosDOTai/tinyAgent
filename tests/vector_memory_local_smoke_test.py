import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from tinyagent.utils.vector_memory import VectorMemory
from tinyagent.utils.embedding_provider import LocalEmbeddingProvider

def test_vector_memory_with_local_provider():
    print("\n[VectorMemory Smoke Test: LocalEmbeddingProvider]")
    provider = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")
    vm = VectorMemory(
        persistence_directory=".test_chroma_memory_local",
        collection_name="test_collection_local",
        embedding_provider=provider
    )
    vm.clear()
    vm.add("user", "Local embedding test message.")
    results = vm.fetch("embedding test", k=1)
    print("Fetch results (local):", results)
    assert results, "No results returned for local provider."
    print("Local provider smoke test passed.")

if __name__ == "__main__":
    test_vector_memory_with_local_provider() 