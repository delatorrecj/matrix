---
name: simulate-up
description: >-
  Boots MATRIX for real simulations: Docker + SUMO nightly baseline in Redis +
  API with persona/GraphRAG warm + Web. Use when the user says simulate up,
  run a simulation locally, need baseline, end-to-end /simulate, or glass-box
  scoring — not for UI-only button fixes (use matrix-dev / dev up instead).
---

# MATRIX simulate-up

Full local stack for actual scenario runs. Slower than **matrix-dev**.

## Do this

1. From the repo root, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .claude/skills/simulate-up/scripts/simulate-up.ps1
```

2. Paste stdout (DOCKER + BASELINE + API + WEB). Stop when all ready. No browser unless asked.

## Do not

- Skip baseline "to go faster" — without it, delta sims / module scoring break
- Use this for pure UI work (use **matrix-dev** / `dev-up.ps1`)
- Force-refresh baseline every time (script seeds only if Redis key missing)

## Note

If API was already started via **matrix-dev** (`MATRIX_SKIP_WARMUP=1`), kill the process on `:8000` then re-run so persona/GraphRAG warm applies.

## On failure

Show log tails. Hint: Docker Desktop, eclipse-sumo / `uv`, net+rou under `packages/kernel/data`, `.env`, or ports.
