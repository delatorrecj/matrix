-- MATRIX persistence schema — Postgres + PostGIS (postgis/postgis:16-3.4, docker-compose).
--
-- Canonical design: docs/sdd-matrix.md §3 (Backend Schema). Idempotent (IF NOT EXISTS
-- throughout) so it can be re-applied safely by load_postgis.py or matrix_api.db at startup.
--
-- Deliberate deviations from the SDD tables, with reasons:
--   * `scenarios.id` / `runs.run_id` are TEXT, not UUID — the kernel's Scenario.scenario_id
--     is a free-form string ("demo", uuid4 hex, ...); TEXT accommodates both. New ids still
--     default to gen_random_uuid()::text.
--   * `runs` is the SDD's `simulation_runs` (shorter name matches the REST surface
--     GET /runs/{run_id}); columns are a superset of the SDD's.
--   * `bias_audit_log.run_id` carries NO foreign key: the kernel's
--     matrix_kernel.bias_auditor.persist_audit() appends entries during persona generation,
--     potentially before a run row exists. The audit log is public + append-only (PRD-F6) —
--     it must never lose a write to referential ordering.
--   * `scenarios.intervention_type` is intentionally un-CHECKed: the orchestrator's enum
--     (lane_closure | full_closure | speed_change | capacity_change) is expected to grow;
--     parsed_params keeps the full structured payload either way.

CREATE EXTENSION IF NOT EXISTS postgis;

-- ─── scenarios — one row per parsed NL/map input (SDD §3 `scenarios`) ────────────────────
CREATE TABLE IF NOT EXISTS scenarios (
    id                TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    city_slug         TEXT NOT NULL DEFAULT 'iloilo',          -- env MATRIX_CITY_SLUG
    input_type        TEXT NOT NULL DEFAULT 'nl' CHECK (input_type IN ('nl', 'map')),
    raw_input         TEXT NOT NULL DEFAULT '',                -- the NL query or map action
    description       TEXT,
    intervention_type TEXT,                                    -- Scenario v2 (see header note)
    location          TEXT,                                    -- Scenario v2 human-readable place
    parsed_params     JSONB,                                   -- full orchestrator output (v1+v2)
    geometry          geometry(Geometry, 4326),                -- project footprint (GeoJSON in/out)
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS scenarios_geometry_gist ON scenarios USING GIST (geometry);

-- ─── runs — one row per kernel simulation (SDD §3 `simulation_runs`) ─────────────────────
CREATE TABLE IF NOT EXISTS runs (
    run_id       TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    scenario_id  TEXT NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    baseline_id  TEXT REFERENCES runs(run_id),                 -- delta source (nightly baseline)
    status       TEXT NOT NULL DEFAULT 'queued'
                 CHECK (status IN ('queued', 'running', 'streaming', 'done', 'failed')),
    duration_ms  INTEGER,                                      -- for the 90 s SLO (RFC-001)
    agent_count  INTEGER,                                      -- personas simulated
    timings      JSONB,                                        -- per-stage breakdown
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS runs_status_idx ON runs (status);
CREATE INDEX IF NOT EXISTS runs_scenario_idx ON runs (scenario_id);

-- ─── dimension_results — one row per DimensionResult, full glass-box provenance ──────────
-- Mirrors matrix_kernel.results.DimensionResult exactly (PRD-F14): a stored run must be as
-- inspectable as a live one. The CHECKs replicate DimensionResult.__post_init__ invariants.
CREATE TABLE IF NOT EXISTS dimension_results (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id            TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    dimension         TEXT NOT NULL CHECK (dimension IN
                        ('behavioral', 'social', 'economic', 'ecological', 'societal')),
    metric            TEXT NOT NULL,
    equation_id       TEXT NOT NULL CHECK (equation_id <> ''),       -- methods-matrix §3 id
    value             DOUBLE PRECISION NOT NULL,
    range_low         DOUBLE PRECISION NOT NULL,
    range_high        DOUBLE PRECISION NOT NULL,
    unit              TEXT NOT NULL,
    confidence        TEXT NOT NULL CHECK (confidence IN ('H', 'M', 'L')),
    directional_only  BOOLEAN NOT NULL DEFAULT false,                -- true when confidence = L
    input_dataset_ids TEXT[] NOT NULL CHECK (cardinality(input_dataset_ids) > 0),
    "references"      TEXT[] NOT NULL DEFAULT '{}',
    assumptions       JSONB NOT NULL DEFAULT '[]',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (range_low <= range_high)                                  -- earned range (PRD-F15)
);
CREATE INDEX IF NOT EXISTS dimension_results_run_dim_idx ON dimension_results (run_id, dimension);

-- ─── bias_audit_log — public, append-only (PRD-F6; SDD §3 `bias_audit_log`) ──────────────
-- Column names/order match matrix_kernel.bias_auditor.persist_audit()'s INSERT exactly —
-- do not rename without updating the kernel.
CREATE TABLE IF NOT EXISTS bias_audit_log (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id       TEXT,                                         -- no FK: see header note
    batch_id     TEXT NOT NULL DEFAULT '',
    mode_share   JSONB NOT NULL,                               -- observed (generated personas)
    ground_truth JSONB NOT NULL,                               -- Iloilo mode-share anchor
    max_delta    NUMERIC NOT NULL,                             -- vs ±3% tolerance
    reweighted   BOOLEAN NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS bias_audit_log_run_idx ON bias_audit_log (run_id);
