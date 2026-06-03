# `packages/data` — processing pipeline

Turns the **acquired raw data** (in this repo's top-level [`../../data/`](../../../data/INVENTORY.md))
into simulation-ready inputs and the GraphRAG corpus. This is **Phase 1 (Gate 1)** work.

> **Acquisition vs. processing.** Raw fetch/outreach lives in `../../data/` (`fetch/`,
> `outreach/`, `raw/`, `processed/`) and is owned by [INVENTORY.md](../../../data/INVENTORY.md)
> + [READINESS.md](../../../data/READINESS.md). *This* package only **transforms** what's
> already there — it does not re-document sources. The `data-pipeline-runner` agent (SAD-A5)
> runs the fetch scripts; this package consumes their output.

## Outputs (Phase 1)

| Output | From | Consumed by |
|--------|------|-------------|
| `iloilo.net.xml` + `iloilo.taz.xml` (SUMO network + barangay trip zones) | OSM-ILO, OVERTURE via `netconvert` | `packages/kernel` (Phase 2) |
| PostGIS `barangay_social`, `barangay_economic` | CCHAIN, PSA economic, WorldPop | Social/Economic modules (Phase 3) |
| ChromaDB GraphRAG index (`bge-small-en`) | OSM, CCHAIN, Calderon 2014, TSSP-2019, INVENTORY/READINESS | orchestrator + synthesis (Phase 4) |

Every table/layer is stamped with its `input_dataset_id` + confidence
([methods-matrix.md §2](../../../docs/methods-matrix.md)) so the provenance contract is
wired from the data layer up.
