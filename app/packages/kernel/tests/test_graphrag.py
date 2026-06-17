"""Tests for GraphRAG ingestion and retrieval (CR-008 Item 9)."""
from __future__ import annotations

import pytest

from matrix_kernel.build_graphrag import ingest_corpus
from matrix_kernel.graphrag import get_collection, retrieve

chromadb = pytest.importorskip("chromadb")


@pytest.fixture(scope="module", autouse=True)
def setup_chromadb():
    """Ensure the corpus is ingested before running retrieval tests."""
    ingest_corpus()


def test_collection_is_populated():
    collection = get_collection()
    assert collection.count() > 0


def test_retrieve_gazetteer_hit():
    chunks = retrieve("what happens if we close the merkado?", top_k=2)
    assert len(chunks) > 0
    # One of the chunks should mention the central market or the colloquial term
    found = any("Iloilo Central Market" in chunk["text"] or "merkado" in chunk["text"] for chunk in chunks)
    assert found is True
    # Verify source metadata is present
    assert any("gazetteer_iloilo.json" in chunk["source"] for chunk in chunks)


def test_retrieve_method_ledger_hit():
    chunks = retrieve("how is the air quality delta calculated?", top_k=1)
    assert len(chunks) == 1
    assert "ECO-2" in chunks[0]["text"]
    assert "methods-matrix.md" in chunks[0]["source"]
