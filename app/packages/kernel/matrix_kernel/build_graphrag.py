"""GraphRAG Ingestion Builder (CR-008 Item 9).

Populates the ChromaDB knowledge base (`matrix_knowledge_base`) with chunks from:
- The Hiligaynon colloquial gazetteer
- Methods-ledger snippets
- Place context for orchestrator grounding

This script must be run once to build the `.chroma` directory, enabling `retrieve()`.
"""
import os
import sys

# Ensure matrix_kernel is importable if run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from matrix_kernel.graphrag import get_collection
from matrix_kernel.gazetteer import load_gazetteer


def ingest_corpus():
    """Build the semantic knowledge base."""
    collection = get_collection()
    
    docs = []
    metadatas = []
    ids = []

    # 1. Ingest Gazetteer entries for colloquial grounding
    gaz = load_gazetteer()
    for colloquial, entry in gaz.items():
        doc = (
            f"Colloquial term: '{colloquial}'. "
            f"Canonical name: {entry.canonical_name}. "
            f"This is a {entry.feature_type} located in Iloilo City. "
            f"OSM ID: {entry.osm_id}. SUMO Edge: {entry.sumo_edge}."
        )
        docs.append(doc)
        metadatas.append({"source": "gazetteer_iloilo.json", "type": "gazetteer"})
        ids.append(f"gaz_{colloquial.replace(' ', '_')}")

    # 2. Add some core methods ledger context to ground synthesis
    core_methods = [
        (
            "methods_eco2",
            "ECO-2 Air-quality delta measures PM2.5 dispersion calibrated to DENR-EMB stations. "
            "Confidence is Medium due to satellite proxies.",
            "methods-matrix.md §3.2"
        ),
        (
            "methods_beh4",
            "BEH-4 Facility demand redistribution uses a distance-decay gravity model. "
            "It diverts trips from the baseline but is currently flagged as PROVISIONAL "
            "until travel survey calibration is complete.",
            "methods-matrix.md §3.1"
        )
    ]
    
    for doc_id, text, source in core_methods:
        docs.append(text)
        metadatas.append({"source": source, "type": "method_ledger"})
        ids.append(doc_id)
        
    print(f"Ingesting {len(docs)} chunks into ChromaDB...")
    
    # Upsert avoids crashing on duplicate runs
    collection.upsert(
        documents=docs,
        metadatas=metadatas,
        ids=ids
    )
    
    print(f"Success. Collection now holds {collection.count()} documents.")


if __name__ == "__main__":
    ingest_corpus()
