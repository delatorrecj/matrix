# Operations & Observability Runbook (OPS)

**Project:** MATRIX
**Date:** 2026-06-02
**Version:** 0.1
**Owner:** Yushin (platform) · Jerico (incident lead) — [PRD §10](prd-matrix.md)
**Status:** Draft
**Last reconciled:** 2026-06-24 (Deploy runbook §7 was written by CR-011 and is current; §6 performance numbers are from CR-007)
**SDD:** [sdd-matrix.md](sdd-matrix.md)

> Keeps MATRIX alive once it's deployed (public demo + any post-hackathon deployment). SLO targets come from [SDD §7](sdd-matrix.md); the RA 10173 breach path comes from [CLR](clr-matrix.md). Hackathon-scale: small-team best-effort, no formal rotation — alerts go to the team.

---

## 1. SLOs & SLIs

| SLI | SLO | Measured by | Breach action |
|-----|-----|-------------|---------------|
| **End-to-end scenario latency (p95, single-user)** | **≤ 90 s** | `simulation_runs.duration_ms` | investigate the slow stage (RFC budget); if persistent, serve reference scenarios |
| First dimension streamed | ≤ ~65 s | `dimension_results` timestamps | check delta/persona-pool warmth |
| Availability (demo windows) | best-effort; green during judged sessions | uptime check | restart Hugging Face Space; fail over to reference scenarios |
| Error rate | < 2% of runs | API logs | check SUMO/Azure OpenAI health |
| Azure OpenAI cost per run | < 2× baseline | run_trace cost | throttle; persona pool cached |
| **Glass-box completeness** | **100% of emitted numbers carry provenance** | `glass-box-auditor` / TRACE-01 scan | block release — a number without provenance is a P0 |

---

## 2. Observability — Logs, Metrics, Traces

| Pillar | Tool | What's captured | Retention |
|--------|------|-----------------|-----------|
| Logs | FastAPI structured JSON (Hugging Face) | request/run_id on every line; stage timings; **no PII** | 30 days |
| Metrics | Application events (PRD §5.5) + SLIs | `simulation_completed` (duration), `dimension_streamed` (latency), `bias_audit_logged` | rolling |
| Traces | **`run_trace`** (glass-box) + AI tracing (Langfuse-style) | prompt + retrieved chunks + params + seed per run; per-call cost | per run history |

**Dashboards:** (1) health — the 90 s SLO + error rate; (2) AI cost — Azure OpenAI spend/run; (3) fairness — bias-audit deltas. **Correlation ID:** `run_id` propagated client → WS → kernel → modules → `run_trace`, so one scenario is traceable end-to-end (this *is* the glass-box, operationalized). **No-PII rule:** open/aggregated data only; PWA traces anonymized at device (reconcile with [CLR §1](clr-matrix.md)).

---

## 3. Alerting & On-Call

| Alert | Condition | Severity | Notified |
|-------|-----------|----------|----------|
| Latency budget breach | p95 > 90 s over 10 runs | P1 | team chat → Yushin |
| Azure OpenAI outage / 429 storm | error spike on AI calls | P1 | Jerico (AI) |
| Sim failure | SUMO/kernel errors > 5% | P1 | Jerico/Yushin (dev) |
| Provenance gap | any output missing `equation_id`/`dataset_ids` | **P0** | Jerico — block ship |
| RA 10173 data event | suspected exposure of PWA trace data | **P0** | Jerico + DPO — see §4 |

**On-call:** small-team best-effort; alerts to team chat; **dedicated coverage during judged demo windows.** **Alert hygiene:** every alert is actionable or it gets tuned/deleted.

---

## 4. Incident Response

Severity ladder = QAD P0–P3. When an incident fires:
1. **Acknowledge** — claim it.
2. **Assess** — severity, blast radius, worsening?
3. **Mitigate first** — roll back (per [PRD §9](prd-matrix.md)) / flip a kill switch / fail over to reference scenarios. Recovery beats root-cause in the moment.
4. **Communicate** — a line to affected users if user-facing.
5. **Resolve & verify** — SLIs back to normal.
6. **Postmortem** — any P0/P1 → `docs/pm-matrix-NNN.md` within 48 h; fold action items back here + into QAD/BUILD.

**RA 10173 breach runbook (PWA trace data — the one personal-data surface):** on suspected exposure, **notify the NPC and affected data subjects within 72 hours** of knowledge if there is real risk of serious harm (CLR §2); the **DPO** (designate per CLR) leads. Disable the PWA trace endpoint immediately (kill switch below).

**Rollback:** redeploy the last-good tagged build serving pre-computed reference scenarios (PRD §9). **Kill switches / flags:** `USE_BASELINE_DELTA` (fall back to cold/cached), `ENABLE_PWA_TRACES` (disable trace collection instantly), `ENABLE_LLM` (serve cached parses for reference scenarios).

---

## 5. Routine Operations

- **Secret rotation:** Azure OpenAI/TomTom/OpenWeather keys in gitignored `.env` / host secrets; rotate if exposed.
- **Dependency / stack currency:** re-verify the BUILD §3 pins (esp. Azure OpenAI SDK, Next.js, Deck.gl) before each sprint; patch promptly.
- **Cost review:** weekly Azure OpenAI spend vs budget; confirm persona pool stays cached.
- **Data refresh:** re-run `data/fetch/*` for live sources; re-stamp vintages in INVENTORY (owner: Rica/Russell — research — via `data-pipeline-runner`).
- **Backup:** in production the run/scenario store is the **in-memory fallback** (ephemeral by design — a Space restart re-seeds the baseline and starts fresh). In local dev, Postgres+PostGIS holds run metadata (`docker compose`). Raw input data is reproducible via `data/fetch/*` (SDD §6 RTO ~2 h / RPO 24 h), so it is regenerable rather than backed up.

### 5.1 Triage Runbook (Planner Feedback)

*Applies to `PRD-F20`: converting CPDO feedback into validation fixtures.*

**Trigger:** Weekly review by the Data/Validation Lead.
**Steps:**
1. **Query Feedback:** Retrieve all `implausible` verdicts via Postgres:
   `SELECT * FROM planner_feedback WHERE verdict = 'implausible' ORDER BY created_at DESC;`
2. **Review Notes & Ground Truth:** Assess the CPDO planner's `note` and `observed_value`. Verify if the underlying data source (INVENTORY) or module logic is at fault.
3. **Draft a Fixture:** For valid corrections, formulate a scenario-to-target mapping and add it to `packages/kernel/validation_fixtures.json`.
4. **Iterate Kernel:** Run `pytest tests/test_validation.py`. The kernel must pass the new fixture before merging.
5. **Close Loop:** Notify the CPDO planner that their feedback is now an enforced validation gate.

---

## 6. Performance Tuning

**Observed baseline latency (warm, no trajectory cache hit):** SUMO ≈ 44 s · modules ≈ 89 ms · AI ≈ 3.8 s · total ≈ 48 s. With a trajectory cache hit (Redis has `scenario:{id}:latest`) the SUMO stage is skipped entirely → total < 5 s. The 90 s budget (SLO §1) is met comfortably for warm runs; cold-start latency above 90 s signals a cache miss + slow AI call.

| Knob | Env var | Default | Effect | Constraint |
|------|---------|---------|--------|------------|
| Sim horizon | `MATRIX_SIM_HORIZON` | `900` s | 600 s saves ~8 s of SUMO wall time | Baseline + scenario must share the same value — **always re-run `run_nightly_baseline()` after changing** |
| Trajectory cache TTL | `MATRIX_TRAJ_CACHE_TTL_S` | `7200` s (2 h) | Repeated runs of the same scenario hit Redis, skipping SUMO | Set `0` to disable caching (forces live SUMO every run) |
| Concurrent sim cap | `MATRIX_MAX_CONCURRENT_SIMS` | `2` | More → more parallel users; fewer → less memory pressure | Each SUMO run needs ~600 MB; a 16 GB Space → cap 20 |
| Rerouting period | `--device.rerouting.period` in `runner.py` | `120` s | Cut to 60 s for higher realism; increase to 180 s to save CPU | Hardcoded in source; a future PR may expose via env var |

**The biggest single win is the trajectory cache.** For a hackathon demo where judges re-run the same scenarios, the first run costs ~48 s; every subsequent run < 1 s. Pre-warm the cache via the frontend or API before a judged session.

---

## 7. Deploy Runbook (Hugging Face Spaces + Vercel)

**Status (CR-011):** backend on a **Docker Hugging Face Space** (`deploy/hf-space/`),
frontend on **Vercel**. Fly.io is decommissioned. The Space is *self-contained* — it runs
Redis in-container, bakes the SUMO net/demand via Git LFS, and uses the in-memory
persistence fallback, so **no managed Postgres/Redis is required**.

### 7.1 Prerequisites

- Hugging Face account + a created **Docker** Space.
- `vercel` CLI installed and authenticated (`vercel login`).
- An Azure OpenAI (AI Foundry) resource with a `gpt-5.4` deployment: `AZURE_OPENAI_API_KEY`,
  `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`.
- Git LFS installed (`git lfs install`) — the Space carries `iloilo.net.xml` /
  `iloilo.rou.xml` as LFS objects.

### 7.2 First-time API deploy (Hugging Face Space)

The Space repo content lives in [`deploy/hf-space/`](../deploy/hf-space): a `Dockerfile`
(clones the app repo + installs the kernel/API), `start.sh` (boots Redis, seeds the SUMO
baseline ~45 s, then serves on **:7860**), the two SUMO files, and the Space `README.md`
front-matter (`sdk: docker`, `app_port: 7860`).

1. Create a new **Docker** Space (e.g. `matrix-api-backend`).
2. **Settings → Variables and secrets** → add **secrets**:
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_ENDPOINT` (e.g. `https://<resource>.services.ai.azure.com/`)
   - `AZURE_OPENAI_DEPLOYMENT` (default `gpt-5.4`)
   - `MATRIX_ALLOWED_ORIGINS` (the Vercel frontend origin, for browser CORS)
3. Push the Space content to the HF git remote:
   ```bash
   git lfs install
   cd deploy/hf-space
   git init && git remote add space https://huggingface.co/spaces/<user>/<space>
   git lfs track "*.net.xml" "*.rou.xml" && git add -A && git commit -m "deploy"
   git push space main
   ```
4. The build clones the **public** app repo, so push app changes to GitHub first and then
   **Factory Reboot** the Space (or bump the Dockerfile) to pull new commits.
5. `GET https://<user>-<space>.hf.space/health` → `{"status":"ok"|"degraded", ...}` once the
   baseline finishes seeding.

### 7.3 First-time web deploy (Vercel)

`app/apps/web/vercel.json` already pins `NEXT_PUBLIC_API_WS_URL` / `NEXT_PUBLIC_API_URL` to
the Space and region `sin1`, so the only optional dashboard var is the Mapbox token.

```bash
cd app/apps/web
vercel --prod

# Optional (Settings → Environment Variables):
#   NEXT_PUBLIC_MAPBOX_TOKEN — only if switching off the keyless OpenFreeMap style
# If the Space URL differs from vercel.json, override NEXT_PUBLIC_API_WS_URL /
#   NEXT_PUBLIC_API_URL here (wss:// and https:// to <user>-<space>.hf.space).
```

### 7.4 Baseline refresh

The SUMO baseline (`baseline:iloilo:latest`) lives in the **in-container Redis** and is
**re-seeded automatically on every Space boot** by `start.sh` — a restart/reboot is the
refresh. There is no `/admin` endpoint; to force a fresh baseline, **Factory Reboot** the
Space (or run `run_nightly_baseline()` in the Space terminal).

### 7.5 Pre-warm the trajectory cache before a demo

`_get_trajectory` writes each run's trajectory back to Redis (TTL
`MATRIX_TRAJ_CACHE_TTL_S`, default 2 h). **Run the demo scenarios once** through the
frontend or `wss://…/simulate/{id}` ahead of a judged session — the first run is ~48 s,
every repeat of the same `scenario_id` is < 1 s (OPS §6).

### 7.6 Rollback

Revert the Space to a previous commit, then it rebuilds:
```bash
cd deploy/hf-space && git push space <previous-commit>:main --force
```
For app-code rollbacks, revert on GitHub and Factory Reboot the Space.

---

## Self-Check

- [x] Every SLO has a real measurement source (run metadata, run_trace, events).
- [x] Logs carry `run_id` and no PII; glass-box trace is the correlation backbone.
- [x] Every alert is actionable and routes to a named owner (§10).
- [x] §4 names rollback + kill switches + the RA 10173 72 h breach path.
- [ ] Run a backup restore drill once a real deployment exists (SDD §6).
- [x] P0/P1 → Postmortem SLA (48 h) defined.
