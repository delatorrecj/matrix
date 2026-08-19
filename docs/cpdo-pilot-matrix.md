# CPDO pilot package (Phase 3)

Working guide for a 30-minute Iloilo CPDO walkthrough. Not Locked.

## Reference scenarios

1. **School in Molo** — `new_facility`, BEH-4 demand (SUMO-injected sample trips).
2. **Lane closure on Diversion Road** — honest corridor overlay + corridor-box camera.
3. **Flood-sensitive esplanade** — ecological flood exposure (directional where VAL-02 is NOT_RUN).

## Session flow

1. Open `/scenario/{id}` from Cockpit preset or NL query.
2. Watch map truth: corridor overlay only on honest resolution; city default on fallback.
3. Summary cards → Inspect → flag **Plausible / Implausible** (PRD-F20, requires completed `run_id`).
4. Export **Scenario brief** (print-scoped one-pager).
5. Capture written feedback or quote — do not invent CPDO sign-off.

## Feedback API

`POST /feedback` with `{ run_id, equation_id, verdict, note? }` — surfaced in Inspect drawer when `run_id` is known.

## Highest-leverage next step

One real planner session → triage implausible flags into validation fixtures (CR-013+).
