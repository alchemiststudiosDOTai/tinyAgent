import os
import openai
import time
from abc import ABC, abstractmethod
from typing import List, Optional
from functools import lru_cache
from sentence_transformers import SentenceTransformer

class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.
    """
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text string.
        """
        pass

    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text strings.
        """
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """
        Return the dimension of the embeddings produced by this provider.
        """
        pass

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider that uses the OpenAI API to generate embeddings.
    """
    _MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        # Add more models and their dimensions as needed
    }

    def __init__(self, model_name: str, api_key: Optional[str] = None, dimensions: Optional[int] = None, timeout: Optional[float] = None, enable_caching: bool = True, cache_size: int = 1024, cache_ttl: int = 3600):
        """
        Initialize the OpenAI embedding provider.
        Args:
            model_name: Name of the OpenAI embedding model (e.g., 'text-embedding-3-small')
            api_key: OpenAI API key (optional, can be loaded from env)
            dimensions: Optional embedding dimension override
            timeout: Optional request timeout in seconds
            enable_caching: Whether to enable in-memory LRU caching
            cache_size: Maximum number of items to cache
            cache_ttl: Time-to-live for cached items in seconds
        """
        self.model_name = model_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.dimensions = dimensions
        self.timeout = timeout
        self.enable_caching = enable_caching
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided via argument or OPENAI_API_KEY env var.")
        openai.api_key = self.api_key
        self._cached_dimension = None
        # For batch caching: (text,...) -> (embedding, timestamp)
        self._batch_cache = {} if enable_caching else None

    def _with_retries(self, func, *args, **kwargs):
        max_attempts = 3
        backoff = 1.0
        for attempt in range(1, max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except (openai.error.RateLimitError, openai.error.Timeout, openai.error.APIConnectionError) as e:
                if attempt == max_attempts:
                    raise RuntimeError(f"OpenAI embedding API error after {attempt} attempts: {e}")
                time.sleep(backoff)
                backoff *= 2
            except Exception as e:
                raise RuntimeError(f"OpenAI embedding API error: {e}")

    def _cache_single(self):
        # functools.lru_cache can't be used directly on instance methods with self, so wrap
        @lru_cache(maxsize=self.cache_size)
        def cached(text):
            return self._with_retries(self._embed_single, text)
        return cached

    def _embed_single(self, text: str) -> List[float]:
        response = openai.embeddings.create(
            input=text,
            model=self.model_name,
            timeout=self.timeout
        )
        return response.data[0].embedding

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text string using OpenAI API.
        """
        if not text:
            raise ValueError("Text for embedding must not be empty.")
        if self.enable_caching:
            if not hasattr(self, '_single_cache'):
                self._single_cache = self._cache_single()
            return self._single_cache(text)
        return self._with_retries(self._embed_single, text)

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text strings using OpenAI API.
        """
        if not texts:
            return []
        if self.enable_caching:
            now = time.time()
            results = []
            uncached = []
            uncached_indices = []
            for i, t in enumerate(texts):
                key = (t,)
                val = self._batch_cache.get(key) if self._batch_cache else None
                if val and now - val[1] < self.cache_ttl:
                    results.append(val[0])
                else:
                    results.append(None)
                    uncached.append(t)
                    uncached_indices.append(i)
            if uncached:
                def call():
                    response = openai.embeddings.create(
                        input=uncached,
                        model=self.model_name,
                        timeout=self.timeout
                    )
                    return [item.embedding for item in response.data]
                new_embs = self._with_retries(call)
                for idx, emb in zip(uncached_indices, new_embs):
                    results[idx] = emb
                    if self._batch_cache is not None:
                        self._batch_cache[(texts[idx],)] = (emb, now)
                # Prune cache if over size
                if self._batch_cache is not None and len(self._batch_cache) > self.cache_size:
                    # Remove oldest
                    sorted_items = sorted(self._batch_cache.items(), key=lambda x: x[1][1])
                    for k, _ in sorted_items[:len(self._batch_cache)-self.cache_size]:
                        del self._batch_cache[k]
            return results
        # No caching
        def call():
            response = openai.embeddings.create(
                input=texts,
                model=self.model_name,
                timeout=self.timeout
            )
            return [item.embedding for item in response.data]
        return self._with_retries(call)

    def get_embedding_dimension(self) -> int:
        """
        Return the dimension of the embeddings produced by the configured model.
        """
        if self.dimensions:
            return self.dimensions
        if self._cached_dimension:
            return self._cached_dimension
        # Try to get from known model dimensions
        dim = self._MODEL_DIMENSIONS.get(self.model_name)
        if dim:
            self._cached_dimension = dim
            return dim
        # Fallback: try to get dimension from a dummy embedding
        try:
            emb = self.generate_embedding("test")
            self._cached_dimension = len(emb)
            return self._cached_dimension
        except Exception:
            raise RuntimeError(f"Could not determine embedding dimension for model {self.model_name}")

    def validate_api_key(self) -> bool:
        """
        Validate the OpenAI API key by making a lightweight API call.
        Returns True if valid, False otherwise.
        """
        try:
            # List models is a lightweight call
            openai.Model.list()
            return True
        except openai.error.AuthenticationError:
            return False
        except Exception:
            return False

    def check_model_available(self) -> bool:
        """
        Check if the configured model is available for the API key.
        Returns True if available, False otherwise.
        """
        try:
            models = openai.Model.list()
            model_ids = [m.id for m in models.data]
            return self.model_name in model_ids
        except Exception:
            return False

    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Normalize text for embedding: trim, lowercase, and strip whitespace.
        """
        return text.strip().lower()

class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Embedding provider using local sentence-transformers models.
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu", cache_folder: str = None, dimensions: int = None):
        self.model_name = model_name
        self.device = device
        self.cache_folder = cache_folder
        self.dimensions = dimensions
        self.model = SentenceTransformer(model_name, cache_folder=cache_folder) if cache_folder else SentenceTransformer(model_name)
        self.model.to(device)
        self._cached_dimension = None

    def generate_embedding(self, text: str) -> list:
        if not text:
            raise ValueError("Text for embedding must not be empty.")
        emb = self.model.encode([text])[0]
        return emb.tolist() if hasattr(emb, 'tolist') else list(emb)

    def generate_embeddings(self, texts: list) -> list:
        if not texts:
            return []
        embs = self.model.encode(texts)
        return [e.tolist() if hasattr(e, 'tolist') else list(e) for e in embs]

    def get_embedding_dimension(self) -> int:
        if self.dimensions:
            return self.dimensions
        if self._cached_dimension:
            return self._cached_dimension
        # Infer from a dummy embedding
        emb = self.generate_embedding("test")
        self._cached_dimension = len(emb)
        return self._cached_dimension

def create_embedding_provider_from_config(config: dict):
    """
    Factory to create an EmbeddingProvider from config dict.
    Supports only OpenAI for now.
    """
    ep_cfg = config.get("embedding_provider", {})
    provider_type = ep_cfg.get("provider_type", "openai")
    if provider_type == "openai":
        from .embedding_provider import OpenAIEmbeddingProvider
        return OpenAIEmbeddingProvider(
            model_name=ep_cfg.get("model_name", "text-embedding-3-small"),
            api_key=ep_cfg.get("api_key"),
            dimensions=ep_cfg.get("dimensions"),
            timeout=ep_cfg.get("timeout_seconds"),
            # Optionally: expose caching config here if needed
        )
    elif provider_type == "local":
        return LocalEmbeddingProvider(
            model_name=ep_cfg.get("model_name", "all-MiniLM-L6-v2"),
            device=ep_cfg.get("device", "cpu"),
            cache_folder=ep_cfg.get("cache_folder"),
            dimensions=ep_cfg.get("dimensions"),
        )
    raise ValueError(f"Unsupported embedding provider type: {provider_type}") 