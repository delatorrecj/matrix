/**
 * Equation formula registry (CR-010 glass-box presentation).
 *
 * Transcribed from docs/methods-matrix.md §3. Presentation only — the kernel
 * owns computed values; this registry supplies the formula text for Inspect.
 */

export interface EquationMeta {
  equationId: string;
  formula: string;
  plainExplanation?: string;
}

/** Keyed by methods-matrix §3 equation id. */
export const EQUATION_REGISTRY: Record<string, EquationMeta> = {
  "BEH-1": {
    equationId: "BEH-1",
    formula: "ΔT_c = Σ_a 1[a traverses c]_scenario − _baseline",
    plainExplanation: "Trip count delta on corridor c from SUMO trajectories.",
  },
  "BEH-2": {
    equationId: "BEH-2",
    formula: "Δm_k = (n_k^sc − n_k^base) / N",
    plainExplanation: "Mode-share shift, constrained to ground-truth anchor ±3%.",
  },
  "BEH-3": {
    equationId: "BEH-3",
    formula: "VC_l = volume_l / capacity_l",
    plainExplanation: "Peak volume-to-capacity ratio per link.",
  },
  "BEH-4": {
    equationId: "BEH-4",
    formula:
      "n_total = capacity × trips_per_capacity; n_redirected = round(n_total × redirected_fraction); w(d) ∝ d^-β",
    plainExplanation: "Gravity-style facility demand redistribution (Wilson-type catchment).",
  },
  "ECO-1": {
    equationId: "ECO-1",
    formula: "ΔCO2e = Σ_k (VKT_k · EF_k)_sc − _base",
    plainExplanation: "Transport CO₂-equivalent delta from vehicle-km traveled per mode.",
  },
  "ECO-2": {
    equationId: "ECO-2",
    formula: "ΔPM2.5 ∝ Δemissions (dispersed, calibrated to station readings)",
    plainExplanation: "Air-quality delta proportional to emission change.",
  },
  "ECO-3": {
    equationId: "ECO-3",
    formula: "Σ area(class_change) vs land-cover baseline",
    plainExplanation: "Green-cover loss from land-use class change.",
  },
  "ECO-4": {
    equationId: "ECO-4",
    formula: "project footprint × hazard layer → Δ pop_exposed",
    plainExplanation: "Change in population exposed to flood hazard.",
  },
  "SOC-1": {
    equationId: "SOC-1",
    formula: "A = Σ_b w_b · Δaccess_b, w_b = inverse income decile",
    plainExplanation: "Equity-weighted access change across barangays.",
  },
  "SOC-2": {
    equationId: "SOC-2",
    formula: "vendors = lanes_closed · _VENDORS_PER_CLOSED_LANE",
    plainExplanation: "Displacement risk proxy from closed-lane vendor count.",
  },
  "SOC-3": {
    equationId: "SOC-3",
    formula: "win/lose by income decile & barangay",
    plainExplanation: "Distributional split of impacts (PRD-F17).",
  },
  "ECON-1": {
    equationId: "ECON-1",
    formula: "ΔLV = LV_base · uplift(Δaccessibility)",
    plainExplanation: "Land-value change within ~1 km of the intervention.",
  },
  "ECON-2": {
    equationId: "ECON-2",
    formula: "footfall = Δtrips · 1.2",
    plainExplanation: "Foot traffic change proportional to trip delta.",
  },
  "ECON-3": {
    equationId: "ECON-3",
    formula: "direct + indirect(multiplier) − displaced",
    plainExplanation: "Net employment change from direct, indirect, and displaced jobs.",
  },
  "SOCI-1": {
    equationId: "SOCI-1",
    formula: "Σ w_i · subscore_i (heritage, health, walk, noise)",
    plainExplanation: "Composite societal wellbeing score (0–100).",
  },
  "SOCI-2": {
    equationId: "SOCI-2",
    formula: "distance decay to nearest declared heritage site",
    plainExplanation: "Heritage proximity pressure score.",
  },
  "SOCI-3": {
    equationId: "SOCI-3",
    formula: "PM2.5 × population density",
    plainExplanation: "Health-exposure proxy combining air quality and density.",
  },
  "SOCI-4": {
    equationId: "SOCI-4",
    formula: "bike/sidewalk coverage + Macalalag factors",
    plainExplanation: "Walkability change from active-transport infrastructure.",
  },
};

export function getEquationText(equationId: string | undefined): string | undefined {
  if (!equationId) return undefined;
  return EQUATION_REGISTRY[equationId]?.formula;
}
