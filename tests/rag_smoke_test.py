import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from tinyagent.decorators import tool
from tinyagent.agent import tiny_agent
from tinyagent.utils.vector_memory import VectorMemory

@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two integers."""
    return a + b


def main():
    # Create an agent with the calculate_sum tool
    agent = tiny_agent(tools=[calculate_sum])
    query = "calculate the sum of 5 and 3"
    result = agent.run(query, expected_type=int)
    print(f"Query: '{query}' -> Result: {result}")


def test_vector_memory_smoke():
    print("\n[VectorMemory Smoke Test]")
    vm = VectorMemory(persistence_directory=".test_chroma_memory", collection_name="test_collection")
    assert vm.collection is not None, "ChromaDB collection was not initialized."
    text = "Hello, this is a test message."
    embedding = vm._embed_text(text)
    print(f"Embedding shape: {embedding.shape if hasattr(embedding, 'shape') else type(embedding)}")
    meta = vm._format_metadata(role="user", content=text)
    print(f"Metadata: {meta}")
    assert isinstance(meta, dict) and "role" in meta and "timestamp" in meta, "Metadata format incorrect."
    print("VectorMemory smoke test passed.")


def test_vector_memory_extended():
    print("\n[VectorMemory Extended Smoke Test]")
    vm = VectorMemory(persistence_directory=".test_chroma_memory", collection_name="test_collection")
    vm.clear()  # Ensure clean state
    # Single add
    vm.add("user", "The Eiffel Tower is in Paris.")
    vm.add("assistant", "Paris is the capital of France.")
    # Batch add
    batch_data = [
        ("user", "What is the capital of Germany?"),
        ("assistant", "Berlin is the capital of Germany."),
        ("user", "Tell me about the Colosseum."),
        ("assistant", "The Colosseum is in Rome.")
    ]
    vm.add(None, batch_data, batch=True)  # role is ignored in batch mode
    # Fetch semantic
    results = vm.fetch("Where is the Eiffel Tower?", k=2)
    print("Semantic fetch results:", results)
    # Fetch recent
    recent = vm.fetch_recent(k=3)
    print("Recent messages:", recent)
    # Fetch by similarity
    sim = vm.fetch_by_similarity("capital", threshold=0.5, max_results=3)
    print("Similarity fetch results:", sim)
    # Stats
    stats = vm.get_stats()
    print("Stats:", stats)
    # Edge: fetch with k > count
    all_msgs = vm.fetch_recent(k=100)
    print(f"Fetch with k > count: {len(all_msgs)} messages")
    # Clear and check
    vm.clear()
    stats_after = vm.get_stats()
    print("Stats after clear:", stats_after)
    print("VectorMemory extended smoke test passed.")


if __name__ == "__main__":
    main()
    test_vector_memory_smoke()
    test_vector_memory_extended()

