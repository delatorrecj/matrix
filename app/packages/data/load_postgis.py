#!/usr/bin/env python3
"""Stand up the MATRIX persistence schema on Postgres + PostGIS.

Applies the idempotent `schema.sql` next to this script (scenarios, runs,
dimension_results, bias_audit_log — SDD §3) to the database in DATABASE_URL, then
verifies PostGIS and reports per-table row counts. Safe to re-run any time; it never
drops anything. The API (`matrix_api.db`) also applies the schema at startup, so this
script is for standing the DB up explicitly (CI, a fresh docker volume, Supabase).

Requirements:
  psycopg3 (`psycopg[binary]`) — already a dependency of packages/kernel and apps/api,
  so any project venv works:
    uv run --directory apps/api python ../../packages/data/load_postgis.py

Target (docker-compose.yml): postgis/postgis:16-3.4 on :5432, dsn matching
app/.env.example DATABASE_URL. Override with --dsn or env DATABASE_URL/MATRIX_PG_DSN.

Usage (from app/ directory, with `docker compose up -d` running):
  python packages/data/load_postgis.py                 # apply schema + verify
  python packages/data/load_postgis.py --check         # verify only, change nothing
  python packages/data/load_postgis.py --dsn postgresql://matrix:matrix@localhost:5432/matrix

Canonical references:
  docs/sdd-matrix.md  §3 (Backend Schema)
  docs/methods-matrix.md  §4 (bias-audit log card — `bias_audit_log` is public/append-only)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent / "schema.sql"
DEFAULT_DSN = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("MATRIX_PG_DSN")
    or "postgresql://matrix:matrix@localhost:5432/matrix"
)
TABLES = ("scenarios", "runs", "dimension_results", "bias_audit_log")
CONNECT_TIMEOUT_S = 5


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dsn", default=DEFAULT_DSN, help="Postgres DSN (default: DATABASE_URL)")
    parser.add_argument("--check", action="store_true", help="verify only; do not apply schema")
    args = parser.parse_args()

    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg3 not installed. Run via a project venv, e.g.\n"
              "  uv run --directory apps/api python ../../packages/data/load_postgis.py")
        return 1

    redacted = args.dsn.rsplit("@", 1)[-1] if "@" in args.dsn else args.dsn
    try:
        conn = psycopg.connect(args.dsn, connect_timeout=CONNECT_TIMEOUT_S)
    except Exception as exc:
        print(f"ERROR: cannot connect to Postgres at {redacted}: {exc}\n"
              "Is docker compose up? (cd app && docker compose up -d)")
        return 1

    with conn:
        if not args.check:
            if not SCHEMA.is_file():
                print(f"ERROR: schema file missing: {SCHEMA}")
                return 1
            # No bind params -> simple query protocol; the multi-statement file runs whole.
            conn.execute(SCHEMA.read_text(encoding="utf-8"))
            conn.commit()
            print(f"applied {SCHEMA.name} -> {redacted}")

        postgis = conn.execute("SELECT extversion FROM pg_extension WHERE extname='postgis'").fetchone()
        print(f"postgis: {postgis[0] if postgis else 'MISSING (geometry columns will not work)'}")

        ok = True
        for table in TABLES:
            exists = conn.execute("SELECT to_regclass(%s)", (f"public.{table}",)).fetchone()[0]
            if exists is None:
                print(f"  {table:>20}: MISSING")
                ok = False
            else:
                count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]  # noqa: S608 - fixed names
                print(f"  {table:>20}: ok ({count} rows)")

    if not ok:
        print("schema incomplete — re-run without --check to apply it")
        return 1
    print("schema ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
