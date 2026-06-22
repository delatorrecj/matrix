# CR-011: Deployment Migration — Fly.io → Hugging Face Spaces

**Date:** 2026-06-22
**Status:** Applied
**Author:** Team ATLAN

## Context

The MATRIX backend (FastAPI + WebSocket + the Eclipse SUMO kernel) was originally
deployed to **Fly.io** with a `fly.toml`, a persistent volume for the SUMO net/demand
files, and `fly secrets` for credentials. That path was retired in favor of a single
**Docker-based Hugging Face Space** that is self-contained and needs no managed
datastore. The Next.js frontend stays on **Vercel** — unchanged.

## Decision

- **Decommission the Fly.io deployment.** `app/fly.toml` and the Fly CLI are removed
  from the operational path.
- Deploy the FastAPI backend + SUMO simulation engine as a **Docker Hugging Face Space**
  (`deploy/hf-space/`). The image:
  - clones the app from the public repo at build time (kernel + API),
  - bakes in the SUMO `iloilo.net.xml` / `iloilo.rou.xml` (carried in the Space repo via
    Git LFS) — no persistent volume,
  - runs **Redis inside the container** (caches are ephemeral, re-seeded each boot),
  - serves on port **7860**; first boot seeds the SUMO baseline (~45 s) before `/health`
    reports ready,
  - sets `MATRIX_PERSONA_LLM=0` so personas come from the static literature-anchored pool
    (no per-persona LLM cost in prod).
- Persistence uses the **in-memory fallback** in `matrix_api/db.py` (no external Postgres
  required for the public demo); Postgres+PostGIS is local-dev only via `docker compose`.
- **Secrets** move from `fly secrets` to **Hugging Face Space → Settings → Secrets**.

## Consequences

- **Deploy process:** `git push` to the Hugging Face Space remote (or a GitHub Action)
  replaces `fly deploy`.
- **Required Space secrets:** `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`,
  `AZURE_OPENAI_DEPLOYMENT`, and `MATRIX_ALLOWED_ORIGINS` (the Vercel frontend origin, for
  browser CORS).
- **Frontend:** `app/apps/web/vercel.json` points `NEXT_PUBLIC_API_WS_URL` /
  `NEXT_PUBLIC_API_URL` at the Space (`*.hf.space`).
- **Removed dependencies:** the Fly CLI and any Fly-specific config are no longer needed.

> Supersedes the Fly.io deploy steps recorded in [cr-007-close-the-loop.md](cr-007-close-the-loop.md) §P4.
> The live runbook is [ops-matrix.md](ops-matrix.md) §7.
