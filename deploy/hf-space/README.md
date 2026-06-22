---
title: MATRIX System
emoji: 🏙️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# MATRIX System Backend

FastAPI + WebSocket backend for **MATRIX** (Multi-Agent Twin for Routing & Infrastructure eXchange) — a pre-construction infrastructure-impact simulator for Iloilo City.

**Self-contained Space.** The Docker image clones the app from the public repo, bakes in the
SUMO network/demand files (carried here via Git LFS), and runs Redis inside the container,
so no persistent volume or external datastore is required.

**Required secrets** (Space → Settings → Secrets):

| Secret | Purpose |
| --- | --- |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI key |
| `AZURE_OPENAI_ENDPOINT` | e.g. `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_DEPLOYMENT` | deployment name (default `gpt-5.4`) |
| `MATRIX_ALLOWED_ORIGINS` | the Vercel frontend origin (for browser CORS) |

First boot seeds the SUMO baseline (~45 s) before serving; `GET /health` reports readiness.
