# Retrieval-Augmented Generation (RAG) in tinyAgent

## Quick Start: How to Use RAG

Retrieval-Augmented Generation (RAG) lets tinyAgent combine LLMs with a vector database to provide contextually relevant information from documents or conversation history.

**To get started:**

1. **Install the package with RAG support:**
   - For local embeddings (sentence-transformers):
     ```bash
     pip install tiny_agent_os[rag-local]
     ```
   - For OpenAI API embeddings:
     ```bash
     pip install tiny_agent_os[rag-api]
     ```
   - For both local and API embedding support:
     ```bash
     pip install tiny_agent_os[rag]
     ```

2. **Configure your embedding provider in `config.yml`:**
   - For OpenAI:
     ```yaml
     embedding_provider:
       provider_type: "openai"
       model_name: "text-embedding-3-small"
       api_key: ${OPENAI_API_KEY} # Set this in your environment
     ```
   - For local (sentence-transformers):
     ```yaml
     embedding_provider:
       provider_type: "local"
       model_name: "all-MiniLM-L6-v2"
       device: "cpu" # or "cuda" for GPU
     ```

3. **Set any required environment variables** (e.g., `OPENAI_API_KEY` for OpenAI provider).

4. **Run tinyAgent as usual.** RAG will be used automatically for retrieval-augmented responses based on your configuration.

---

## What is RAG?

Retrieval-Augmented Generation (RAG) is a technique that combines large language models (LLMs) with a vector database to provide contextually relevant information from external sources or conversation history. This enables agents to "recall" facts, previous messages, or documents, improving accuracy and grounding responses.

## Installation for RAG

Depending on your embedding provider, install the appropriate optional dependencies:

- For local embeddings (sentence-transformers):
  ```bash
  pip install tiny_agent_os[rag-local]
  ```
- For OpenAI API embeddings:
  ```bash
  pip install tiny_agent_os[rag-api]
  ```
- For both local and API embedding support:
  ```bash
  pip install tiny_agent_os[rag]
  ```

## How RAG Works in tinyAgent

- **VectorMemory** stores and retrieves conversation history or documents using vector embeddings.
- **Embedding Providers** convert text into embeddings. tinyAgent supports both local (sentence-transformers) and OpenAI embedding models.
- **ChromaDB** is used as the vector database backend.

## Enabling and Configuring Vector Memory

To use RAG in tinyAgent, configure the `embedding_provider` section in your `config.yml`:

### Example: OpenAI Embedding Provider

```yaml
embedding_provider:
  provider_type: "openai"
  model_name: "text-embedding-3-small"
  api_key: ${OPENAI_API_KEY} # Set this in your environment
  # dimensions: 1536           # Optional
  # timeout_seconds: 30        # Optional
```

### Example: Local Embedding Provider (sentence-transformers)

```yaml
embedding_provider:
  provider_type: "local"
  model_name: "all-MiniLM-L6-v2"
  device: "cpu" # or "cuda" for GPU
  # cache_folder: "/path/to/cache" # Optional
  # dimensions: 384                 # Optional
```

## Switching Providers

- Change the `provider_type` in `config.yml` to either `openai` or `local`.
- Make sure you have installed the correct optional dependencies for your provider (see Installation for RAG above).
- No code changes are needed—tinyAgent will automatically use the correct provider at runtime.

## Troubleshooting

- **OpenAI API Key:** Ensure `OPENAI_API_KEY` is set in your environment for OpenAI provider.
- **Model Not Found:** For local models, ensure the model name is correct and available in sentence-transformers.
- **Performance:** Local models are faster and cost-free, but may be less accurate than OpenAI's latest models.
- **ChromaDB Issues:** Ensure the persistence directory is writable and not corrupted.

## Example: Using VectorMemory in Your Code

You can use RAG features programmatically in your own code. Here are real examples for both local and OpenAI embedding providers:

### Local Embedding Provider Example

```python
from tinyagent.utils.vector_memory import VectorMemory
from tinyagent.utils.embedding_provider import LocalEmbeddingProvider

# Initialize the local embedding provider
provider = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2", device="cpu")

# Create a VectorMemory instance
vm = VectorMemory(
    persistence_directory=".chroma_memory",
    collection_name="my_collection",
    embedding_provider=provider
)

# Add a message to memory
vm.add("user", "This is a message to store in vector memory.")

# Fetch the most relevant message for a query
results = vm.fetch("message", k=1)
print("Fetch results:", results)
```

### OpenAI Embedding Provider Example

```python
import os
from tinyagent.utils.vector_memory import VectorMemory
from tinyagent.utils.embedding_provider import OpenAIEmbeddingProvider

# Make sure your OpenAI API key is set in the environment
api_key = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI embedding provider
provider = OpenAIEmbeddingProvider(model_name="text-embedding-3-small", api_key=api_key)

# Create a VectorMemory instance
vm = VectorMemory(
    persistence_directory=".chroma_memory",
    collection_name="my_collection",
    embedding_provider=provider
)

# Add a message to memory
vm.add("user", "This is a message to store in vector memory.")

# Fetch the most relevant message for a query
results = vm.fetch("message", k=1)
print("Fetch results:", results)
```

## References

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [sentence-transformers](https://www.sbert.net/)

---

For more advanced orchestration and agent patterns, see the other docs in this folder.
