# MATRIX — Grand Finals Evidence Index

**Purpose:** What you can show on stage vs keep for Q&A. Every figure cites [`CLAIMS.md`](CLAIMS.md) or a repo path.  
**Do not invent numbers here.**

---

## A. Show on stage (Proof / Demo)

| Asset | Where | What it proves | Claim bucket |
|-------|-------|----------------|--------------|
| Live app | https://matrix-atlan.vercel.app/ | Product runs in production | PROVEN |
| 20–30s demo video | *(record per [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md); store under `presentation/assets/` when ready)* | Scenario → consequence story | PROVEN (of UX) |
| Inspect drawer screenshot / live click | `apps/web` Inspect; optional `presentation/assets/` | Glass-box provenance | PROVEN |
| Summary / Analytics view | CR-010 UX | Plain-language results | PROVEN |
| Bias audit panel | Live `/audit/{scenario_id}` path | Public audit log | PROVEN |

### On-slide proof figures (allowed)

| Figure | Meaning | Source |
|------|---------|--------|
| 180 barangays | CCHAIN Iloilo subset coverage | [data/READINESS.md](../../data/READINESS.md) / INVENTORY |
| 5,680 priced parcels | BIR zonal RDO 74 land-value entries | [data/READINESS.md](../../data/READINESS.md) |
| 5 dimensions | Behavioral · Social · Economic · Ecological · Societal | methods-matrix / kernel modules |
| 190 + 64 tests | Kernel bare + API bare passing (skipped = SUMO-guarded) | [docs/qad-matrix.md](../../docs/qad-matrix.md) |
| “250+ automated tests” | Spoken rounding of 190+64 | Same — prefer exact if challenged |

---

## B. Keep for Q&A (appendix / verbal)

| Topic | Safe answer pointer | Status |
|-------|---------------------|--------|
| VAL-01 Calderon | [semifinal-qa-prep.md](../semifinal-qa-prep.md) Q2.2; methods §6 | Gate built; headline **WITHHELD** |
| VAL-02 flood | Q2.4; methods §6 | **NOT_RUN** |
| Accuracy % | Q2.2b — per-gate only; never one headline % | — |
| Who validated? | Q2.1 — literature gate + eng gates; **no CPDO sign-off yet** | LIMIT |
| 90 s latency | RFC-001; QAD PERF-01; CLAIMS latency row | **Target**; measure live |
| Bias / informal economy | Q&A prep bias section; bias_auditor | PROVEN (auditor); static pool nuance |
| Scale beyond Iloilo | OSM bbox + persona reweight | Path / VISION for regional twin |
| Business model | Public-good LGU free now; paid later TBD | Not the spoken spine |
| Privacy / RA 10173 | No PII in core pipeline; open-data licenses | Q&A |

Full Q&A bible: [`../semifinal-qa-prep.md`](../semifinal-qa-prep.md) — **update any line that still says validation gates are merely “planned.”** Correct framing: machinery shipped; VAL-01 withheld; VAL-02 NOT_RUN.

---

## C. Deploy & repo

| Item | Value |
|------|-------|
| Frontend | https://matrix-atlan.vercel.app/ |
| Backend | Hugging Face Spaces (CR-011) |
| Repo | github.com/delatorrecj/matrix *(confirm public URL team will cite)* |
| Spec | [MATRIX.md](../../MATRIX.md) |
| Methods / glass box | [docs/methods-matrix.md](../../docs/methods-matrix.md) |
| Change records | CR-010 UX · CR-011 deploy · CR-012 validation |

---

## D. Validation status card (appendix slide)

| Gate | Metric | Threshold | Status |
|------|--------|-----------|--------|
| VAL-01 Behavioral | NRMSE vs Calderon 2014 corridor | 0.30 (FHWA-documented) | **WITHHELD** — demand calibration |
| VAL-02 Flood | IoU vs 2024 extent | 0.50 | **NOT_RUN** — extent not wired |
| VAL-03 Personas | Mode-share vs anchors | ±3% | Enforced via bias auditor |
| Eng gates | glass-box-auditor + eval-test-runner | PASS to merge | **Shipped** |

---

## E. Asset checklist (produce before finals)

- [ ] Final 20–30s demo MP4 (+ silent alternate)  
- [ ] Inspect still (high-res)  
- [ ] Summary dock still  
- [ ] Optional: staircase diagram for Slide 7  
- [ ] Optional: cascade still / city B-roll for open/close (real Iloilo if possible)  
- [ ] Projector PDF / PPTX from updated story deck  
- [ ] Offline copy of demo video on presenter laptop  

Drop recorded media under [`../assets/`](../assets/) and note filenames here when ready.

---

## F. Conflict log (docs that can poison the pitch)

| Source | Risk | Grand Finals rule |
|--------|------|-------------------|
| [`../walkthrough.md`](../walkthrough.md) | Says validation “planned for semi-final” | Use CLAIMS: gates built; withheld / NOT_RUN |
| [`../CONTENT-OUTLINE.md`](../CONTENT-OUTLINE.md) | Feature-BMC spine | Story beats only |
| [`../semifinal-video-script.md`](../semifinal-video-script.md) | Tech-Execution weighting | Impact + human consequence spine |
| Implementation plan “~123 s” vs QAD “~48 s warm” | Latency whiplash | Say **target 90 s**; measure; don’t overclaim |

---

## G. One-line evidence closer (Proof beat)

> Built today. Honest about what isn’t calibrated yet. Ready to learn with the city — before the city pays the price.
