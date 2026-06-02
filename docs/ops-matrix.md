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
| Availability (demo windows) | best-effort; green during judged sessions | uptime check | restart Fly app; fail over to reference scenarios |
| Error rate | < 2% of runs | API logs | check SUMO/Gemini health |
| Gemini cost per run | < 2× baseline | run_trace cost | throttle; persona pool cached, Pro low-call |
| **Glass-box completeness** | **100% of emitted numbers carry provenance** | `glass-box-auditor` / TRACE-01 scan | block release — a number without provenance is a P0 |

---

## 2. Observability — Logs, Metrics, Traces

| Pillar | Tool | What's captured | Retention |
|--------|------|-----------------|-----------|
| Logs | FastAPI structured JSON (Fly) | request/run_id on every line; stage timings; **no PII** | 30 days |
| Metrics | Supabase events (PRD §5.5) + SLIs | `simulation_completed` (duration), `dimension_streamed` (latency), `bias_audit_logged` | rolling |
| Traces | **`run_trace`** (glass-box) + Gemini tracing (Langfuse-style) | prompt + retrieved chunks + params + seed per run; per-call cost | per run history |

**Dashboards:** (1) health — the 90 s SLO + error rate; (2) AI cost — Gemini spend/run; (3) fairness — bias-audit deltas. **Correlation ID:** `run_id` propagated client → WS → kernel → modules → `run_trace`, so one scenario is traceable end-to-end (this *is* the glass-box, operationalized). **No-PII rule:** open/aggregated data only; PWA traces anonymized at device (reconcile with [CLR §1](clr-matrix.md)).

---

## 3. Alerting & On-Call

| Alert | Condition | Severity | Notified |
|-------|-----------|----------|----------|
| Latency budget breach | p95 > 90 s over 10 runs | P1 | team chat → Yushin |
| Gemini outage / 429 storm | error spike on Gemini calls | P1 | Jerico (AI) |
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

**Rollback:** redeploy the last-good tagged build serving pre-computed reference scenarios (PRD §9). **Kill switches / flags:** `USE_BASELINE_DELTA` (fall back to cold/cached), `ENABLE_PWA_TRACES` (disable trace collection instantly), `ENABLE_GEMINI` (serve cached parses for reference scenarios).

---

## 5. Routine Operations

- **Secret rotation:** Gemini/TomTom/OpenWeather keys in gitignored `.env` / host secrets; rotate if exposed.
- **Dependency / stack currency:** re-verify the BUILD §3 pins (esp. Gemini SDK, Next.js, Deck.gl) before each sprint; patch promptly.
- **Cost review:** weekly Gemini spend vs free-tier; confirm persona pool stays cached.
- **Data refresh:** re-run `data/fetch/*` for live sources; re-stamp vintages in INVENTORY (owner: Rica/Russell — research — via `data-pipeline-runner`).
- **Backup:** Supabase daily snapshots; raw data is reproducible via `data/fetch/*` (SDD §6 RTO ~2 h / RPO 24 h).

---

## Self-Check

- [x] Every SLO has a real measurement source (run metadata, run_trace, events).
- [x] Logs carry `run_id` and no PII; glass-box trace is the correlation backbone.
- [x] Every alert is actionable and routes to a named owner (§10).
- [x] §4 names rollback + kill switches + the RA 10173 72 h breach path.
- [ ] Run a backup restore drill once a real deployment exists (SDD §6).
- [x] P0/P1 → Postmortem SLA (48 h) defined.
