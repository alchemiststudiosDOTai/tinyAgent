import threading
import time
import uuid
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from .embedding_provider import EmbeddingProvider


class VectorMemory:
    """
    VectorMemory provides a vector-based memory system using ChromaDB as the backend.
    It supports configurable persistence, embedding models, and collection management.
    """

    def __init__(
        self,
        persistence_directory: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        collection_name: str = "tinyagent_memory",
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        """
        Initialize the VectorMemory system.
        Args:
            persistence_directory: Directory for ChromaDB persistence (optional)
            embedding_model: Name of the embedding model to use (ignored if embedding_provider is given)
            collection_name: Name of the ChromaDB collection
            embedding_provider: Optional EmbeddingProvider instance (OpenAI or local)
        """
        self.persistence_directory = persistence_directory or ".chroma_memory"
        self.embedding_model_name = embedding_model
        self.collection_name = collection_name
        self.embedding_provider = embedding_provider
        self._init_chromadb()
        if not self.embedding_provider:
            self._init_embedding_model()
        self._lock = threading.Lock()
        self._embedding_cache = {}  # text -> embedding

    def _init_chromadb(self):
        self.chroma_client = chromadb.Client(
            Settings(persist_directory=self.persistence_directory)
        )
        self.collection = self.chroma_client.get_or_create_collection(
            self.collection_name
        )

    def _init_embedding_model(self):
        # Only used if no embedding_provider is given
        self.embedding_model = SentenceTransformer(self.embedding_model_name)

    def configure_persistence(self, directory: str):
        """Change the persistence directory and reinitialize ChromaDB."""
        self.persistence_directory = directory
        self._init_chromadb()

    def configure_embedding_model(self, model_name: str):
        """Switch the embedding model used for vectorization."""
        self.embedding_model_name = model_name
        if not self.embedding_provider:
            self._init_embedding_model()

    def _embed_text(self, text: str):
        """Generate an embedding for the given text."""
        if not text:
            raise ValueError("Text for embedding must not be empty.")
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        if self.embedding_provider:
            emb = self.embedding_provider.generate_embedding(text)
        else:
            emb = self.embedding_model.encode([text])[0]
        self._embedding_cache[text] = emb
        return emb

    def _format_metadata(self, role: str, content: str) -> Dict[str, Any]:
        """Create metadata dict with role, timestamp, and token count."""
        return {
            "role": role,
            "timestamp": time.time(),
            "token_count": self.count_tokens(content),
        }

    @staticmethod
    def count_tokens(text: str) -> int:
        # Simple whitespace token count; replace with tokenizer if needed
        return len(text.split())

    def add(self, role: str, content: str, batch: bool = False):
        """Add a message to memory. If batch=True, content is a list of (role, content) tuples."""
        with self._lock:
            if batch:
                roles, contents, ids, metas, embeddings = [], [], [], [], []
                for r, c in content:
                    if not c:
                        continue
                    roles.append(r)
                    contents.append(c)
                    ids.append(str(uuid.uuid4()))
                    metas.append(self._format_metadata(r, c))
                    embeddings.append(self._embed_text(c))
                if contents:
                    self.collection.add(
                        ids=ids,
                        documents=contents,
                        metadatas=metas,
                        embeddings=embeddings,
                    )
            else:
                if not content:
                    raise ValueError("Content must not be empty.")
                doc_id = str(uuid.uuid4())
                meta = self._format_metadata(role, content)
                emb = self._embed_text(content)
                self.collection.add(
                    ids=[doc_id],
                    documents=[content],
                    metadatas=[meta],
                    embeddings=[emb],
                )

    def fetch(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve k most relevant messages for a query."""
        if not query:
            raise ValueError("Query must not be empty.")
        query_emb = self._embed_text(query)
        results = self.collection.query(query_embeddings=[query_emb], n_results=k)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        return [
            {"role": meta.get("role", "unknown"), "content": doc, "metadata": meta}
            for doc, meta in zip(docs, metas)
        ]

    def fetch_recent(self, k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve k most recent messages."""
        # ChromaDB does not support sort by timestamp, so we fetch all and sort
        all_results = self.collection.get()
        docs = all_results.get("documents", [])
        metas = all_results.get("metadatas", [])
        items = [
            {"role": meta.get("role", "unknown"), "content": doc, "metadata": meta}
            for doc, meta in zip(docs, metas)
        ]
        items.sort(key=lambda x: x["metadata"].get("timestamp", 0), reverse=True)
        return items[:k]

    def fetch_by_similarity(
        self, query: str, threshold: float = 0.7, max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Return msgs whose cosine-similarity ≥ threshold (≈ 1-distance)."""
        if not query:
            raise ValueError("Query must not be empty.")

        q_emb = self._embed_text(query)
        res = self.collection.query(
            query_embeddings=[q_emb],
            n_results=max_results,
            include=["documents", "metadatas", "distances"],
        )

        # Chroma can return None when nothing is found
        docs = res.get("documents") or [[]]
        metas = res.get("metadatas") or [[]]
        dists = res.get("distances") or [[]]

        if not docs[0]:  # no hits at all
            return []

        out = []
        for doc, meta, dist in zip(docs[0], metas[0], dists[0]):
            # distance 0 → identical, 1 → orthogonal for normalized embeddings
            if dist <= (1 - threshold):
                out.append(
                    {
                        "role": meta.get("role", "unknown"),
                        "content": doc,
                        "metadata": meta,
                        "distance": dist,
                    }
                )
        return out

    def clear(self):
        """Remove all items from the collection."""
        with self._lock:
            all_results = self.collection.get()
            ids = all_results.get("ids", [])
            if ids:
                self.collection.delete(ids=ids)

    def get_stats(self) -> Dict[str, Any]:
        """Return stats about the memory collection."""
        all_results = self.collection.get()
        count = len(all_results.get("documents", []))
        return {
            "count": count,
            "collection_name": self.collection_name,
            "persist_directory": self.persistence_directory,
        }

    def _truncate(
        self, items: List[Dict[str, Any]], max_tokens: int
    ) -> List[Dict[str, Any]]:
        """Truncate items so total token count does not exceed max_tokens."""
        total = 0
        out = []
        for item in items:
            tokens = item["metadata"].get("token_count", 0)
            if total + tokens > max_tokens:
                break
            out.append(item)
            total += tokens
        return out


# Example usage (for testing):
if __name__ == "__main__":
    vm = VectorMemory()
    print(f"ChromaDB collection: {vm.collection_name}")
    print(f"Persistence dir: {vm.persistence_directory}")
    print(f"Embedding model: {vm.embedding_model_name}")
