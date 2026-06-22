# Operations & Observability Runbook (OPS)

**Project:** MATRIX
**Date:** 2026-06-02
**Version:** 0.1
**Owner:** Yushin (platform) · Jerico (incident lead) — [PRD §10](prd-matrix.md)
**Status:** Draft
**Last reconciled:** N/A — not yet reconciled with prod
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
| Metrics | Supabase events (PRD §5.5) + SLIs | `simulation_completed` (duration), `dimension_streamed` (latency), `bias_audit_logged` | rolling |
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
- **Backup:** Supabase daily snapshots; raw data is reproducible via `data/fetch/*` (SDD §6 RTO ~2 h / RPO 24 h).

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

**Status as of CR-009:** Migrated backend to Hugging Face Spaces (Docker).

### 7.1 Prerequisites

- Hugging Face account and a created Docker Space.
- `vercel` CLI installed and authenticated (`vercel login`).
- `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` provisioned.
- Redis instance provisioned (e.g., Upstash) and URL available.
- Net + demand files built locally: `cd app/packages/kernel && uv run python ../../packages/data/build_network.py` + `build_demand.py`.

### 7.2 First-time API deploy (Hugging Face Spaces)

1. Create a new Docker Space on Hugging Face (e.g., `matrix-api-backend`).
2. Navigate to **Settings > Variables and secrets** in your Space.
3. Add the following secrets:
   - `AZURE_OPENAI_API_KEY`
   - `AZURE_OPENAI_ENDPOINT`
   - `DATABASE_URL` (Supabase pooled URL, port 6543)
   - `SUPABASE_KEY`
   - `MATRIX_REDIS_URL`
4. Deploy the code by pushing to the Hugging Face git remote:
   ```bash
   git remote add hf https://huggingface.co/spaces/<your-username>/<your-space-name>
   git push hf main
   ```
5. Ensure that the `app/packages/kernel/data` folder containing `iloilo.net.xml` and `iloilo.rou.xml` is pushed along with the repository, or downloaded during the Docker build process, as Hugging Face Spaces do not use Hugging Face Spaces's persistent volumes in the same way.

### 7.3 First-time web deploy (Vercel)

```bash
# From apps/web; Vercel auto-detects Next.js
cd app/apps/web
vercel --prod

# Set env secrets in Vercel dashboard (Settings → Environment Variables):
#   NEXT_PUBLIC_MAPBOX_TOKEN    — Mapbox public token
#   NEXT_PUBLIC_SUPABASE_URL    — Supabase project URL
#   NEXT_PUBLIC_SUPABASE_ANON_KEY — Supabase anon key
# NEXT_PUBLIC_API_WS_URL should point to your Hugging Face space: wss://<your-username>-<your-space-name>.hf.space
```

### 7.4 Nightly baseline refresh

The SUMO baseline (`baseline:iloilo:latest`) expires from Redis when the TTL runs out or Redis restarts. Set a cron script in a separate environment or GitHub Action to trigger the baseline refresh via a secure API endpoint:
```bash
curl -X POST https://<your-username>-<your-space-name>.hf.space/admin/baseline -H "Authorization: Bearer <ADMIN_TOKEN>"
```

### 7.5 Pre-warm trajectory cache before a demo session

Similarly, trigger the pre-warm via an API call to the backend:
```bash
curl -X POST https://<your-username>-<your-space-name>.hf.space/admin/prewarm -H "Authorization: Bearer <ADMIN_TOKEN>"
```

### 7.6 Rollback

Use `git revert` or revert to a previous commit on the Hugging Face remote:
```bash
git push hf <previous-commit-hash>:main --force
```

---

## Self-Check

- [x] Every SLO has a real measurement source (run metadata, run_trace, events).
- [x] Logs carry `run_id` and no PII; glass-box trace is the correlation backbone.
- [x] Every alert is actionable and routes to a named owner (§10).
- [x] §4 names rollback + kill switches + the RA 10173 72 h breach path.
- [ ] Run a backup restore drill once a real deployment exists (SDD §6).
- [x] P0/P1 → Postmortem SLA (48 h) defined.
