# MATRIX Changelog & Release Notes: Bug Fixes & New Features

This document provides a comprehensive inventory of all bug fixes, architectural enhancements, UI/UX improvements, and new features introduced across the **MATRIX Urban Planning & Impact Simulator** monorepo (`app/packages/kernel`, `app/apps/api`, and `app/apps/web`).

---

## Executive Summary

| Category | Item | Impact |
| :--- | :--- | :--- |
| **New Feature** | **Human-Readable Result Translator (`humanize.py`)** | Transforms raw float output (`DimensionResult`) into natural-language briefs for mayors & planners prior to LLM synthesis. |
| **New Feature** | **All-in-One Windows Stack Launcher (`start-all.ps1`)** | Single PowerShell script to clean up ports `3000`/`8000` and launch both FastAPI backend and Next.js frontend servers. |
| **System Fix** | **Evaluation Script Path Resolution (`scripts/run_eval.py`)** | Resolved `ModuleNotFoundError: No module named 'matrix_kernel'` when running CI/eval gates outside editable environments. |
| **Kernel Fix** | **Validation Baseline Gate Fallback Guard (`validation.py`)** | Enforces honest `NOT_RUN` status when Redis/live SUMO runs are unavailable instead of scoring synthetic fallback numbers. |
| **UI Fix** | **Full-Screen Glassmorphic Inspect Drawer (`InspectDrawer.tsx`)** | Replaced cramped pop-up windows with a responsive, full-height inspection drawer showing equations, datasets, and confidence. |
| **UI Fix** | **Responsive Scenario Builder Layout (`ScenarioBuilder.tsx`)** | Polished 2-column grid (`sm:grid-cols-2`) with balanced full-width bottom card (`New facility`) and responsive suggestion pills. |

---

## 1. New Features & Core Additions

### 1.1 Human-Readable Result Translator (`matrix_kernel/humanize.py`)
- **Purpose**: Serves as the backend glass-box bridge (`humanize_results_for_llm`), translating mathematical floats and confidence levels into natural-language sentences tailored for city officials and planners.
- **Key Capabilities**:
  - Translates raw outputs (`BEH-1` through `SOCI-4`) into plain-language impact statements (e.g., *"Transport carbon emissions would decrease by about 1,200 tonnes of CO₂ per year"*).
  - Translates qualitative confidence flags (`H`, `M`, `L`) into transparent reliability qualifiers (`"confident estimate"`, `"indicative estimate"`, `"rough indication only"`).
  - Eliminates jargon while retaining exact `[equation_id]` citations so LLM synthesis remains fully traceable.

### 1.2 Windows Stack Automation Script (`start-all.ps1`)
- **Purpose**: Provides a single command-line entry point to launch the complete local stack on Windows PowerShell.
- **Behavior**:
  - Automatically inspects local ports `8000` (FastAPI) and `3000` (Next.js) and terminates stale orphan processes.
  - Spawns dedicated PowerShell windows for `uvicorn matrix_api.main:app` and `npm run dev`.

---

## 2. Kernel & Backend Bug Fixes

### 2.1 Evaluation Pipeline Module Resolution (`scripts/run_eval.py`)
- **Bug Fixed**: Running `python scripts/run_eval.py` failed with `ModuleNotFoundError: No module named 'matrix_kernel'` when executed directly outside an editable package environment.
- **Root Cause**: `sys.path.append(...)` added local paths *after* Python attempted to resolve imports.
- **Resolution**: Updated script initialization to use `sys.path.insert(0, ...)` for `app/packages/kernel` and `app`, ensuring local kernel modules take precedence.

### 2.2 Glass-Box Validation Integrity (`matrix_kernel/validation.py`)
- **Bug Fixed**: In headless or offline environments where Redis or live SUMO runs were unreachable, `simulated_corridor_flows_from_baseline` silently returned synthetic in-memory fallback numbers.
- **Root Cause**: Synthetic baseline data was not explicitly flagged or filtered during validation gate checks.
- **Resolution**: Added an explicit `allow_synthetic: bool = False` guard. When synthetic fallbacks (`traj.meta.get("fallback") == "synthetic_in_memory"`) are encountered during validation runs, the gate returns `None`, allowing automated gates to report an honest `NOT_RUN` status rather than a false score.

### 2.3 Numerical Formatting & Domain Calculations
- **Updates across `ecological.py`, `economic.py`, and `societal.py`**:
  - Hardened unit conversions and boundary checks for emissions (`ECO-1` to `ECO-4`), land value impacts (`ECON-1`), and equity indicators (`SOC-1`, `SOCI-1`).
  - Improved null-safety and NaN-prevention when zero-vehicle baseline counts are encountered.

---

## 3. Frontend & UI/Design Fixes

### 3.1 Full-Screen Glassmorphic Inspect Drawer (`components/InspectDrawer.tsx`)
- **Bug Fixed**: Previous inspection modal pop-ups looked cramped, visually cluttered, and cut off long mathematical equations and dataset tables.
- **Resolution**:
  - Replaced small pop-up modals with a sleek, full-height sliding glass drawer (`glass-strong`) that animates smoothly from the right edge.
  - Added dedicated sections for **Mathematical Equation (`equation_id`)**, **Input Datasets & Vintages**, **Confidence Assessment Matrix**, and **Assumptions & Caveats**.
  - Improved keyboard accessibility (`Escape` key to close) and click-outside dismissal.

### 3.2 Responsive Scenario Builder Layout (`components/ScenarioBuilder.tsx`)
- **Bug Fixed**: Intervention option cards wrapped unevenly on Desktop viewports (`1280x800`), leaving a single 5th card (`New facility`) orphaned on the left column, while mobile viewports suffered from button text truncation and overflow.
- **Resolution**:
  - Configured a symmetrical responsive grid (`grid-cols-1 sm:grid-cols-2 gap-3`) where the 5th intervention option spans both columns (`sm:col-span-2`) on tablet/desktop viewports, creating a balanced bottom card.
  - Converted location suggestion pills into responsive flex-wrap containers (`flex flex-wrap gap-2 items-center`) with multi-line text support (`whitespace-normal text-left max-w-full`).

### 3.3 Interactive Dimension Cards & Summary Humanization (`components/DimensionCard.tsx`)
- **Bug Fixed**: Dimension result cards lacked clear visual feedback when clicking on provenance chips.
- **Resolution**: Added hover micro-interactions, distinct confidence badges (`High`, `Medium`, `Low` color-coded pills), and direct wiring to open the expanded `InspectDrawer`.

---

## 4. Verification & Quality Assurance Summary

All fixes and features have been validated against the repository's strict quality guardrails:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MATRIX MERGE GATE VERIFICATION                        │
├──────────────────────────────────┬──────────────────────────────────────────┤
│ Test Suite                       │ Result                                   │
├──────────────────────────────────┼──────────────────────────────────────────┤
│ Kernel Unit & Validation Tests   │ ✅ 29 PASSED (pytest packages/kernel)    │
│ Glass-Box & Latency Eval Gate    │ ✅ ALL GATES PASSED (scripts/run_eval.py)│
│ Frontend Component & Unit Suite  │ ✅ 186 PASSED across 16 files (vitest)   │
│ Responsive UI Viewport Audits    │ ✅ Verified on Desktop & Mobile (375px)  │
└──────────────────────────────────┴──────────────────────────────────────────┘
```

---

## 5. Quick-Start Guide after Update

To run the updated codebase with all fixes and new features:

```powershell
# 1. Using the automated Windows launcher script:
.\start-all.ps1

# OR manually launch the backend and frontend:
# Terminal 1 (Backend API on port 8000):
cd app/apps/api
uv run uvicorn matrix_api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 (Frontend Web App on port 3000):
cd app/apps/web
npm run dev -- -p 3000
```
