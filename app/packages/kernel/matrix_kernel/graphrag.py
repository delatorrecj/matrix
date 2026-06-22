"""GraphRAG knowledge base layer (PRD-F9).

ChromaDB index over OSM context, CCHAIN summaries, literature, etc.
Embedded with bge-small-en to provide grounding for the orchestrator and synthesis.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import TypedDict

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None

EMBED_MODEL = "BAAI/bge-small-en-v1.5"
COLLECTION_NAME = "matrix_knowledge_base"


@lru_cache(maxsize=1)
def _embedding_fn(model_name: str = EMBED_MODEL):
    """The bge-small embedding model — built once per process. This is the slow part of
    get_collection() (it loads the model from disk), and it sits on the orchestrator's 90 s
    critical path via retrieve(), so it must never be reconstructed per request (RFC-001)."""
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)


@lru_cache(maxsize=8)
def _collection_for(chroma_path: str, chroma_url: str | None):
    """Memoized collection per (path, url) target. The embedding function is shared across
    targets via _embedding_fn(), so the model loads once even if several stores are touched."""
    if chroma_url:
        client = chromadb.HttpClient(
            host=chroma_url.split(":")[1].strip("/"), port=int(chroma_url.split(":")[-1])
        )
    else:
        client = chromadb.PersistentClient(path=chroma_path)
    return client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=_embedding_fn())


class RetrievedChunk(TypedDict):
    text: str
    source: str


def get_collection():
    """Get or create the ChromaDB collection (memoized per CHROMA_PATH/CHROMA_URL).

    The env vars are still honored — they form the cache key — so changing the target
    yields a different (also-cached) collection. Within one process and target, the same
    collection object (and the same loaded embedding model) is reused on every call."""
    if chromadb is None:
        raise ImportError("chromadb not installed. Run: uv add chromadb sentence-transformers")

    chroma_path = os.environ.get("CHROMA_PATH", "./.chroma")
    chroma_url = os.environ.get("CHROMA_URL")
    return _collection_for(chroma_path, chroma_url)


def retrieve(query: str, top_k: int = 5) -> list[RetrievedChunk]:
    """Retrieve relevant chunks from the knowledge base for a given query."""
    try:
        collection = get_collection()
    except ImportError:
        # If not installed/built, return empty context
        print("Warning: ChromaDB not available. Returning empty GraphRAG context.")
        return []
        
    # If the collection is empty, return empty
    if collection.count() == 0:
        return []
        
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    
    chunks = []
    if results and results['documents'] and results['documents'][0]:
        for i, doc in enumerate(results['documents'][0]):
            meta = results['metadatas'][0][i] if results['metadatas'] else {}
            chunks.append({
                "text": doc,
                "source": meta.get("source", "unknown")
            })
            
    return chunks
