"""Shared test config for the API suite.

Disable the startup warm-up (persona pool + GraphRAG ingest) by default so the suite stays
hermetic and fast: those caches reach for Redis/Chroma/an LLM, which a bare test env does not
have. The warm-up is best-effort in production (matrix_api.main._warm_kernel_caches); skipping
it here only affects the optional caches, never the REST/WS behaviour the tests assert."""
import os

os.environ.setdefault("MATRIX_SKIP_WARMUP", "1")
