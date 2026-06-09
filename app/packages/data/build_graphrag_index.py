"""Build the GraphRAG ChromaDB index.

Embeds OSM context, CCHAIN summaries, and literature into ChromaDB
using bge-small-en for use by the orchestrator and synthesis agents.
"""
import sys
import os
from pathlib import Path

# Add packages/kernel to path to import matrix_kernel
kernel_path = Path(__file__).parent.parent / "kernel"
sys.path.append(str(kernel_path))

try:
    from matrix_kernel.graphrag import get_collection  # type: ignore
except ImportError as e:
    print(f"Failed to import graphrag: {e}")
    get_collection = None


def build_index():
    """Build the ChromaDB vector index."""
    if get_collection is None:
        print("ChromaDB not available. Skipping index build.")
        return
        
    print("Building GraphRAG index...")
    collection = get_collection()
    
    # Read actual documentation and inventory files
    root_dir = Path(__file__).parent.parent.parent.parent
    docs_dir = root_dir / "docs"
    inventory_file = root_dir / "data" / "INVENTORY.md"
    
    files_to_index = list(docs_dir.glob("*.md"))
    if inventory_file.exists():
        files_to_index.append(inventory_file)
        
    docs = []
    metadatas = []
    ids = []
    
    print(f"Found {len(files_to_index)} files to index.")
    
    for filepath in files_to_index:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Basic chunking: split by double newlines (paragraphs/sections)
            chunks = [c.strip() for c in content.split("\n\n") if len(c.strip()) > 50]
            
            for i, chunk in enumerate(chunks):
                # To avoid hitting DB batch limits in one go or excessive memory,
                # we just append them all here (Chroma Python client handles chunking under the hood or we can batch it)
                docs.append(chunk)
                metadatas.append({"source": filepath.name, "confidence": "H"})
                ids.append(f"{filepath.name}_chunk_{i}")
                
        except Exception as e:
            print(f"Error reading {filepath.name}: {e}")
            
    if not docs:
        print("No documents found to index.")
        return
        
    # ChromaDB has a maximum batch size for additions (often 5461 or 166 or 41666 depending on SQLite limits)
    # We batch insert by 500
    batch_size = 500
    for i in range(0, len(docs), batch_size):
        batch_docs = docs[i:i+batch_size]
        batch_metas = metadatas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        
        collection.add(
            documents=batch_docs,
            metadatas=batch_metas,
            ids=batch_ids
        )
        print(f"Added batch of {len(batch_docs)} documents.")
    
    print(f"✅ Added a total of {len(docs)} document chunks to the index.")

if __name__ == "__main__":
    build_index()

