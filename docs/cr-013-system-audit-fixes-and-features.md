# CR-013: System & UI Audit Remediation and New Kernel Features

- **Author:** MATRIX Build Team
- **Date:** 2026-07-08 / 2026-07-09
- **Status:** APPROVED & IMPLEMENTED
- **Affected Packages:** `app/packages/kernel`, `app/apps/api`, `app/apps/web`, `scripts`

---

## 1. Context & Objectives

Following an end-to-end system audit and visual inspect across both Desktop (`1280x800`) and Mobile (`375x812`) viewports, this change record formalizes remediation across three key areas:
1. **Kernel Enhancement**: Introduction of plain-language result humanization (`humanize.py`).
2. **System & Validation Hardening**: Resolving module import paths in CI evaluation scripts (`run_eval.py`) and preventing synthetic baseline fallbacks from passing live validation gates (`validation.py`).
3. **UI/UX Design Excellence**: Transforming cramped inspection modals into a full-height glassmorphic drawer (`InspectDrawer.tsx`) and balancing responsive grid layouts in the Scenario Builder (`ScenarioBuilder.tsx`).

---

## 2. Summary of Changes

### 2.1 Kernel Architecture
- **`matrix_kernel/humanize.py` [NEW]**: Implements backend plain-language brief generation (`humanize_results_for_llm`) tailored for non-technical city officials while retaining bracketed `[equation_id]` citations.
- **`matrix_kernel/validation.py` [MODIFY]**: Added `allow_synthetic: bool = False` to `simulated_corridor_flows_from_baseline`, ensuring offline/in-memory fallback data returns `None` (`NOT_RUN`) rather than creating misleading gate scores.

### 2.2 Execution & Evaluation Scripts
- **`scripts/run_eval.py` [MODIFY]**: Prepend `app/packages/kernel` to `sys.path.insert(0, ...)` prior to module imports; updated symbol formatting so honest `NOT_RUN` gates report warnings rather than breaking CI pipelines.
- **`start-all.ps1` [NEW]**: Added a PowerShell stack launcher that automatically clears ports `8000` and `3000` before spawning API and web servers.

### 2.3 Web Application UI (`apps/web`)
- **`components/InspectDrawer.tsx` [MODIFY]**: Full-height sliding drawer design (`glass-strong`) showing complete mathematical equations, dataset vintages, and confidence matrices.
- **`components/ScenarioBuilder.tsx` [MODIFY]**: Updated intervention grid to `grid-cols-1 sm:grid-cols-2` with `sm:col-span-2` on the 5th option (`New facility`) for symmetrical layout on tablet/desktop, plus responsive suggestion pill wrapping on narrow mobile screens.

---

## 3. Verification & Compliance

All changes have been verified against established test gates:
- **Unit & Integration Suite**: `pytest packages/kernel` → **29 PASSED**
- **Evaluation Gate**: `python scripts/run_eval.py` → **ALL GATES PASSED**
- **Frontend Unit Suite**: `npx vitest run` → **186 PASSED across 16 files**
