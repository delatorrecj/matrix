# MATRIX — Claims Firewall (Grand Finals)

**Purpose:** Prevent the pitch from claiming what the product does not do.  
**Rule:** Every spoken or slide fact must map to **PROVEN**, **IN DEVELOPMENT / HONEST LIMITS**, or **VISION**.  
**Strategy owner:** [`PITCH_STRATEGY.md`](PITCH_STRATEGY.md)  
**As-built snapshot:** through CR-010 / CR-012 (see [`docs/index.md`](../../docs/index.md))

---

## How to use this file

| Bucket | Verb tense on stage | Example |
|--------|---------------------|---------|
| **PROVEN** | Present (“runs,” “shows,” “traces”) | “Every number opens in Inspect.” |
| **IN DEVELOPMENT / HONEST LIMITS** | Labeled (“target,” “withheld,” “next,” “not yet”) | “VAL-01 headline is withheld until demand is calibrated.” |
| **VISION** | Future only (“will,” “can become,” “eventually”) | “Eventually, the city itself becomes the feedback loop.” |

If a claim is not listed, **do not invent it**. Add it here first with a citation, or cut it.

---

## PROVEN — say freely

### Product & deploy

| Claim | Citation |
|-------|----------|
| Live web app at [https://matrix-atlan.vercel.app/](https://matrix-atlan.vercel.app/) | Deployed frontend; site copy matches “See the impact before you build it.” |
| Backend on Hugging Face Spaces (Docker); Vercel frontend unchanged | [docs/cr-011-huggingface-migration.md](../../docs/cr-011-huggingface-migration.md) |
| Pre-construction urban impact simulator for Iloilo pilot | [MATRIX.md](../../MATRIX.md); live site |

### Architecture that runs today

| Claim | Citation |
|-------|----------|
| One unified SUMO (+ persona) kernel produces one trajectory dataset | [MATRIX.md](../../MATRIX.md); `app/packages/kernel` |
| Five impact modules score that **same** simulated reality in parallel: Behavioral, Social, Economic, Ecological, Societal | `app/packages/kernel/matrix_kernel/modules/*.py`; [docs/methods-matrix.md](../../docs/methods-matrix.md) |
| Natural-language / map scenario → orchestrator → simulate → dimension results → synthesis → Deck.gl playback | [docs/sdd-matrix.md](../../docs/sdd-matrix.md); WebSocket progressive stream in `apps/api` |
| Azure OpenAI `gpt-5.4` narrates and cites; **does not originate numbers** | [docs/cr-008-azure-openai-migration.md](../../docs/cr-008-azure-openai-migration.md); [docs/cr-009-azure-foundry-client.md](../../docs/cr-009-azure-foundry-client.md); citation guard |

### Glass box & honesty UX

| Claim | Citation |
|-------|----------|
| Every scored number carries `equation_id` + `input_dataset_ids` + a **computed** confidence (H/M/L) | PRD-F14; `DimensionResult` in `matrix_kernel/results.py`; [docs/methods-matrix.md](../../docs/methods-matrix.md) |
| Inspect drawer resolves provenance in the UI | `apps/web` Inspect drawer; [docs/dsd-matrix.md](../../docs/dsd-matrix.md) |
| Low confidence can suppress false-precision point estimates (“directional only”) | Confidence / presentation rules; CR-010 formatters |
| Summary-first results UX + plain-language / BLUF synthesis (+ Hiligaynon delimited) | [docs/cr-010-ui-summary-humanization.md](../../docs/cr-010-ui-summary-humanization.md) |
| Bias auditor runs in the live pipeline; public audit log keyed to scenario | API warm path + `GET /audit/{scenario_id}`; CLAUDE.md as-built notes |
| GraphRAG / Chroma corpus ingested at API startup to ground orchestration | CLAUDE.md wire-up notes; `graphrag.py` |

### Engineering evidence

| Claim | Citation |
|-------|----------|
| Kernel tests: **190 passed, 11 skipped** bare (`python -m pytest`, SUMO tests skip cleanly) | [docs/qad-matrix.md](../../docs/qad-matrix.md) (reconciled 2026-06-24) |
| API tests: **64 passed, 4 skipped** bare | [docs/qad-matrix.md](../../docs/qad-matrix.md) |
| Two merge guardrails: glass-box-auditor + eval-test-runner | [AGENTS.md](../../AGENTS.md) |
| Validation **machinery** (VAL-01 / VAL-02 gates) is implemented and tested | `matrix_kernel/validation.py`; [docs/methods-matrix.md §6](../../docs/methods-matrix.md); [docs/cr-012-validation-calibration.md](../../docs/cr-012-validation-calibration.md) |
| Planner feedback loop exists in product (PRD-F20) | [docs/prd-matrix.md](../../docs/prd-matrix.md) PRD-F20 |

### Iloilo data foundation (inventory-backed figures only)

| Claim | Citation |
|-------|----------|
| CCHAIN Iloilo subset across **180 barangays** | [data/INVENTORY.md](../../data/INVENTORY.md); [data/READINESS.md](../../data/READINESS.md) |
| BIR zonal values RDO 74: **5,680 priced entries** (land-value layer) | [data/READINESS.md](../../data/READINESS.md) Economic row |
| All five dimensions have real Iloilo data at barangay granularity (open-data / scripted path) | [data/READINESS.md](../../data/READINESS.md) |
| Confidence floors are explicit per dimension; Behavioral mode-share remains the soft spot | [data/READINESS.md](../../data/READINESS.md) |

### Competitive framing (allowed form)

| Claim | Citation |
|-------|----------|
| Feature-survey framing: combination of NL input + five dimensions in one run + per-dimension confidence — “based on our feature survey,” not an absolute monopoly | [docs/gtm-matrix.md](../../docs/gtm-matrix.md) §2.1; [presentation/CONTENT-OUTLINE.md](../CONTENT-OUTLINE.md) |

---

## IN DEVELOPMENT / HONEST LIMITS — say only with labels

| Topic | Honest line | Citation |
|-------|-------------|----------|
| **VAL-01 (Calderon corridor)** | Gate is **built**; headline NRMSE is **WITHHELD** pending demand-volume calibration. Threshold: normalized RMSE vs Calderon 2014, FHWA-documented **0.30**. Say “withheld pending calibration,” not “not validated.” | [docs/methods-matrix.md §6](../../docs/methods-matrix.md); [docs/cr-012-validation-calibration.md](../../docs/cr-012-validation-calibration.md); [presentation/semifinal-qa-prep.md](../semifinal-qa-prep.md) Q2.2 |
| **VAL-02 (flood)** | **NOT_RUN** — closure helper staged; no real Sentinel-1 2024 extent wired → no IoU. Do not claim flood validation passed. | [docs/methods-matrix.md §6](../../docs/methods-matrix.md) |
| **External planner sign-off** | No Iloilo CPDO / transport engineer has formally signed off yet. PRD-F20 is built to capture that feedback. Highest-leverage next step. | [presentation/semifinal-qa-prep.md](../semifinal-qa-prep.md) Q2.1; PRD-F20 |
| **90-second latency** | **Engineered target.** Warm / cached paths are designed to hit it (pre-warmed personas, delta vs baseline, parallel modules, Redis trajectory cache for repeats). Cold / first runs can exceed it. Docs historically cite ~123 s probes; QAD reconciled note also records ~48 s warm after caching work — **do not claim “always under 90 s” without a live measured figure for that day.** Prefer: “architected for a 90-second answer.” | [docs/rfc-matrix-realtime-pipeline.md](../../docs/rfc-matrix-realtime-pipeline.md); [docs/qad-matrix.md](../../docs/qad-matrix.md); CLAUDE.md |
| **Continuous / real-time urban data ingestion** | Not a shipped product surface. Open / batch data + scripts today. | [data/INVENTORY.md](../../data/INVENTORY.md); this strategy |
| **Automated citywide data auditing as a product** | Bias audit + confidence + glass box exist; full data-gathering / cleansing / audit ops platform does **not**. | Positioning in [PITCH_STRATEGY.md](PITCH_STRATEGY.md) |
| **Mode-share / demand calibration** | Behavioral stays Medium; uncalibrated demand is why VAL-01 is withheld. | [data/READINESS.md](../../data/READINESS.md); CR-012 |
| **Gazetteer GIS node ids** | Provisional placeholders remain an honest gap. | CLAUDE.md as-built notes |
| **Some fixtures / samples** | Flood/edges/confidence-map samples may be labeled PROVISIONAL. | methods-matrix; CR-006 honesty notes |

---

## VISION — future tense only

| Vision line | Safe phrasing |
|-------------|----------------|
| Living Digital Twin | “Eventually, cities can build a living model of their environment, continuously learning from reality.” |
| Continuous urban data | “Tomorrow, MATRIX can connect to continuously updated urban data.” |
| Simulation ↔ reality loop | “The city itself becomes the feedback loop.” |
| ASEAN-wide deployment | Beachhead Iloilo → other PH cities → ASEAN (API bbox swap + persona reweight) — **path**, not “already deployed across ASEAN.” |
| Decision intelligence at regional scale | “A regional way for cities to learn before they act.” |
| Full data gathering + processing + auditing ops | Part of the staircase **after** simulation proof — not claimed as shipped. |

---

## Absolute must-not-claim (hard bans)

1. “We have a complete Digital Twin of Iloilo / ASEAN.”  
2. “MATRIX provides real-time urban data.”  
3. “We’ve solved Philippine data scarcity” / “we already do data gathering and auditing end-to-end.”  
4. “Validated by CPDO” or a published empirical RMSE / IoU without the WITHHELD / NOT_RUN status.  
5. Invented accuracy % (“94% accurate”).  
6. False-precision ROI, TAM/SAM/SOM, or “multi-billion” as a sourced statistic (illustrative pattern language only, if used at all).  
7. Absolute “no ASEAN / no tool does this.”  
8. “Validation gates are not built” (false — machinery is shipped).  
9. Reintroducing Gemini / Supabase / Fly.io as the live stack (stale).  
10. Claiming the LLM invents dimension scores.

---

## Preferred proof lines (safe)

> “This isn’t just an idea. The kernel, all five modules, the streaming API, and the Deck.gl frontend run today — on an Iloilo open-data foundation including 180 barangays and 5,680 priced parcels.”

> “Our empirical validation gates are built. We deliberately withhold the Behavioral headline until demand is calibrated — because publishing a confident number off uncalibrated demand would break our own glass-box rule.”

> “Every number you see can open in Inspect: equation, named datasets, computed confidence. The AI narrates. It does not invent the figure.”

---

## Semi-final doc hygiene

When Phase II scripts conflict with older materials:

| Older line | Correct Grand Finals line |
|------------|---------------------------|
| Validation gates “planned / not shipped” | Gates **shipped**; VAL-01 **withheld**; VAL-02 **NOT_RUN** |
| Always “~123 s” as current truth | “90 s target”; measure live; cite cache for repeats |
| “Digital Twin City Simulator” as primary identity | Decision-intelligence / see consequences **before** reality; Digital Twin is the staircase destination |

Update older presentation files only when explicitly asked; this folder owns Grand Finals truth.
