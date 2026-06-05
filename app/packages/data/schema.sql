-- MATRIX local dev schema — the subset of SDD §3 the Milestone A glass-box slice needs.
-- Faithful to docs/sdd-matrix.md §3. The remaining tables (run_trace, datasets) and the
-- managed Supabase migrations come later. Apply:
--   docker compose -f app/docker-compose.yml exec -T postgres psql -U matrix -d matrix < app/packages/data/schema.sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS scenarios (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    input_type    TEXT NOT NULL CHECK (input_type IN ('nl', 'map')),
    raw_input     TEXT NOT NULL,
    parsed_params JSONB,
    geometry      GEOMETRY,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS simulation_runs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id  UUID REFERENCES scenarios(id) ON DELETE CASCADE,
    baseline_id  UUID REFERENCES simulation_runs(id),
    status       TEXT NOT NULL DEFAULT 'queued'
                 CHECK (status IN ('queued', 'running', 'streaming', 'done', 'failed')),
    duration_ms  INT,
    agent_count  INT,
    started_at   TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_simruns_status ON simulation_runs(status);

CREATE TABLE IF NOT EXISTS dimension_results (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id            UUID NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
    dimension         TEXT NOT NULL
                      CHECK (dimension IN ('behavioral', 'social', 'economic', 'ecological', 'societal')),
    score             JSONB NOT NULL,
    confidence        TEXT NOT NULL CHECK (confidence IN ('H', 'M', 'L')),
    range_low         NUMERIC,
    range_high        NUMERIC,
    directional_only  BOOL NOT NULL DEFAULT false,
    equation_id       TEXT NOT NULL,
    input_dataset_ids TEXT[] NOT NULL,
    assumptions       JSONB,
    "references"      TEXT[]
);
CREATE INDEX IF NOT EXISTS idx_dimresults_run_dim ON dimension_results(run_id, dimension);

-- Public-readable mode-share audit (PRD-F6). Slice deviation from SDD §3 (reconcile later):
-- run_id is NULLABLE because the persona-pool audit runs pre-simulation (no run yet), and
-- batch_id is added to match the kernel's BiasAuditEntry(batch_id, ...) for pool-level audits.
CREATE TABLE IF NOT EXISTS bias_audit_log (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id       UUID REFERENCES simulation_runs(id) ON DELETE CASCADE,
    batch_id     TEXT,
    mode_share   JSONB NOT NULL,
    ground_truth JSONB NOT NULL,
    max_delta    NUMERIC NOT NULL,
    reweighted   BOOL NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
