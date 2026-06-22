#!/usr/bin/env bash
# HF Space entrypoint: bring up the bundled Redis, seed the SUMO baseline, then serve.
set -e

# 1) Bundled Redis (HF has no managed Redis). Ephemeral — the baseline + caches below are
#    re-seeded on every boot, so data loss across restarts is by design.
redis-server --daemonize yes
# Wait until Redis answers before seeding (cheap loop, ~instant locally).
for _ in $(seq 1 30); do redis-cli ping >/dev/null 2>&1 && break; sleep 0.2; done

# 2) Seed the SUMO baseline into Redis. The FIRST /simulate reads baseline:iloilo:latest,
#    so seeding here means the first real request works instead of erroring. Heavy (~45s
#    SUMO run) but one-time per boot; best-effort so a failure still lets the API serve
#    /health and the REST surface while we diagnose.
echo "Seeding SUMO baseline (one-time, ~45s)…"
# The Python traceback (incl. the SUMO binary's stderr — e.g. a missing shared library)
# prints above on failure; do NOT swallow it. Best-effort so the API still serves /health
# and the REST surface while we diagnose. /health now reports baseline:missing explicitly.
if python -c "from matrix_kernel.baseline import run_nightly_baseline; print('baseline seeded:', run_nightly_baseline())"; then
    echo "baseline OK"
else
    echo "ERROR: SUMO baseline seed FAILED (traceback above). /simulate will error until it is"
    echo "       seeded; GET /health -> dependencies.baseline = missing. Continuing so the API"
    echo "       still serves /health + REST."
fi

# 3) Serve. Single worker: the startup warm-up (persona pool + bge embedding model) loads
#    torch once; concurrency is gated by the MATRIX_MAX_CONCURRENT_SIMS semaphore, not workers.
exec uvicorn matrix_api.main:app --host 0.0.0.0 --port 7860 --workers 1
