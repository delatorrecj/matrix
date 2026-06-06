"""GraphRAG knowledge base layer (PRD-F9).

ChromaDB index over OSM context, CCHAIN summaries, literature, etc.
Embedded with bge-small-en to provide grounding for the orchestrator and synthesis.
"""
from __future__ import annotations

import os
from typing import TypedDict

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None


class RetrievedChunk(TypedDict):
    text: str
    source: str


def get_collection():
    """Get or create the ChromaDB collection."""
    if chromadb is None:
        raise ImportError("chromadb not installed. Run: uv add chromadb sentence-transformers")

    chroma_path = os.environ.get("CHROMA_PATH", "./.chroma")
    chroma_url = os.environ.get("CHROMA_URL")
    
    if chroma_url:
        client = chromadb.HttpClient(host=chroma_url.split(":")[1].strip("/"), port=int(chroma_url.split(":")[-1]))
    else:
        client = chromadb.PersistentClient(path=chroma_path)
        
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-small-en-v1.5")
    
    return client.get_or_create_collection(name="matrix_knowledge_base", embedding_function=ef)


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
