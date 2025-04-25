# Retrieval-Augmented Generation (RAG) in tinyAgent

## What is RAG?

Retrieval-Augmented Generation (RAG) is a technique that combines large language models (LLMs) with a vector database to provide contextually relevant information from external sources or conversation history. This enables agents to "recall" facts, previous messages, or documents, improving accuracy and grounding responses.

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
- No code changes are needed—tinyAgent will automatically use the correct provider at runtime.

## Troubleshooting

- **OpenAI API Key:** Ensure `OPENAI_API_KEY` is set in your environment for OpenAI provider.
- **Model Not Found:** For local models, ensure the model name is correct and available in sentence-transformers.
- **Performance:** Local models are faster and cost-free, but may be less accurate than OpenAI's latest models.
- **ChromaDB Issues:** Ensure the persistence directory is writable and not corrupted.

## Testing Your Setup

- See `tests/vector_memory_provider_smoke_test.py` for smoke tests covering both providers.
- Run the tests to verify your configuration and provider integration.

## References

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [sentence-transformers](https://www.sbert.net/)

---

For more advanced orchestration and agent patterns, see the other docs in this folder.
