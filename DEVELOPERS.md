# MATRIX Developers Guide

This guide contains the technical setup, conventions, and data layout for the MATRIX project. For a high-level overview of the project, please see the [README.md](README.md).

---

## Quick Start (Developers)

**Prerequisites:** Python 3.12+, Node.js (v20+), Git, Docker. Windows, macOS, and Linux are supported.

### 1. Start Local Datastores
Local datastores run via Docker:
```bash
cd app
docker compose up -d
```

### 2. Start the Backend API
The FastAPI backend serves scenario parsing and trajectory streaming:
```bash
cd app/apps/api
uv sync
uv run uvicorn matrix_api.main:app --reload
```

### 3. Start the Frontend Application
Run the Next.js development server:
```bash
cd app/apps/web
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the application.

### 4. Run Test Suite
Run the unit tests to verify the simulation logic:
```bash
cd app/packages/kernel
uv sync
uv run pytest
```

---

## Where Things Are

| Path | Description |
|---|---|
| **[MATRIX.md](MATRIX.md)** | Canonical product and technical specification. |
| [data/INVENTORY.md](data/INVENTORY.md) | Live data manifest. |
| [data/READINESS.md](data/READINESS.md) | Data mapped to the impact dimensions. |
| [MATRIX_Iloilo_Data_Sources.md](MATRIX_Iloilo_Data_Sources.md) | Source rationale and details. |
| [CLAUDE.md](CLAUDE.md) | Operating guide for AI coding agents. |
| `docs/` | Formal documentation suite. |

## Data Layout

```
data/
  raw/        # fetched as is (gitignored)
  interim/    # conversions (gitignored)
  processed/  # analysis-ready and git-tracked
  fetch/      # download scripts
  outreach/   # contact drafts
  INVENTORY.md   READINESS.md   README.md
```

## Conventions

* **Never commit raw or interim data, or secrets.** They are gitignored. Regenerate raw data with the fetch scripts.
* **Branch off main** and open a pull request. Keep history clean.
* **Data honesty:** every dataset carries a confidence tier. We do not present estimates as absolute facts.
* **Prefer the newest data** when available.
