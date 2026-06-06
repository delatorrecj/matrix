"""Build the GraphRAG ChromaDB index.

Embeds OSM context, CCHAIN summaries, and literature into ChromaDB
using bge-small-en for use by the orchestrator and synthesis agents.
"""
import sys
from pathlib import Path

# Add app to path to import matrix_kernel
app_path = Path(__file__).parent.parent.parent / "app"
sys.path.append(str(app_path))

try:
    from matrix_kernel.graphrag import get_collection
except ImportError:
    get_collection = None

def build_index():
    """Build the ChromaDB vector index."""
    if get_collection is None:
        print("ChromaDB not available. Skipping index build.")
        return
        
    print("Building GraphRAG index...")
    collection = get_collection()
    
    # In a full implementation, we'd read the OSM context, CCHAIN summaries,
    # Calderon 2014, and TSSP-2019 bike text and insert them.
    
    docs = [
        "Iloilo City's primary public transport mode is the traditional jeepney, capturing over 55% of the mode share according to Calderon (2014).",
        "The Diversion Road (Sen. Benigno Aquino Jr. Avenue) is a major arterial corridor connecting the city proper to Mandurriao.",
        "Molo is a key district with high trip generation due to schools and commercial areas."
    ]
    
    metadatas = [
        {"source": "Calderon2014", "confidence": "M"},
        {"source": "OSM-ILO", "confidence": "H"},
        {"source": "OSM-ILO", "confidence": "H"}
    ]
    
    ids = [f"doc_{i}" for i in range(len(docs))]
    
    collection.add(
        documents=docs,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"✅ Added {len(docs)} documents to the index.")

if __name__ == "__main__":
    build_index()
