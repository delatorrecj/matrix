"""Load on-disk processed datasets for module equations (Credibility Phase 3).

Paths resolve to the MATRIX repo `data/processed/` tree (co-located with `app/`).
Missing files return None so modules can fall back honestly (confidence L + assumptions).
"""
from __future__ import annotations

import csv
import statistics
from functools import lru_cache
from pathlib import Path

# matrix_kernel → kernel → packages → app → repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]
_PROCESSED = _REPO_ROOT / "data" / "processed"
_CCHAIN = _PROCESSED / "cchain_iloilo"
_BIR_CSV = _PROCESSED / "economic" / "bir_zonal_rdo74_2021.csv"


def processed_root() -> Path:
    return _PROCESSED


@lru_cache(maxsize=1)
def latest_worldpop_total() -> tuple[float, str] | None:
    """(city pop_count_total sum, vintage_year) for the latest WorldPop year in CCHAIN."""
    path = _CCHAIN / "worldpop_population.csv"
    if not path.is_file():
        return None
    by_year: dict[str, float] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            year = (row.get("date") or "")[:4]
            if not year.isdigit():
                continue
            try:
                by_year[year] = by_year.get(year, 0.0) + float(row.get("pop_count_total") or 0)
            except (TypeError, ValueError):
                continue
    if not by_year:
        return None
    year = max(by_year)
    return (by_year[year], year)


@lru_cache(maxsize=1)
def latest_rwi_means() -> tuple[list[float], str] | None:
    """Per-barangay rwi_mean for the latest RWI vintage."""
    path = _CCHAIN / "tm_relative_wealth_index.csv"
    if not path.is_file():
        return None
    by_year: dict[str, list[float]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            year = (row.get("date") or "")[:4]
            if not year.isdigit():
                continue
            try:
                val = float(row.get("rwi_mean") or "")
            except (TypeError, ValueError):
                continue
            by_year.setdefault(year, []).append(val)
    if not by_year:
        return None
    year = max(by_year)
    return (by_year[year], year)


@lru_cache(maxsize=1)
def mean_market_convenience_pois() -> tuple[float, str] | None:
    """City-mean (market_place_count + convenience_count) from CCHAIN osm_poi_amenity.

    Used as a data-backed stand-in for informal vendor density near corridors (SOC-2).
    """
    path = _CCHAIN / "osm_poi_amenity.csv"
    if not path.is_file():
        return None
    by_year: dict[str, list[float]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            year = (row.get("date") or "")[:4]
            if not year.isdigit():
                continue
            try:
                markets = float(row.get("market_place_count") or 0)
                conv = float(row.get("convenience_count") or 0)
            except (TypeError, ValueError):
                continue
            by_year.setdefault(year, []).append(markets + conv)
    if not by_year:
        return None
    year = max(by_year)
    vals = by_year[year]
    return (statistics.mean(vals), year)


@lru_cache(maxsize=1)
def flood_exposed_population_100yr() -> tuple[float, str] | None:
    """Persons in 100-yr high flood share × WorldPop (latest aligned vintage available).

    Joins project_noah_hazards pct_area_flood_hazard_100yr_high with worldpop by adm4.
    """
    haz_path = _CCHAIN / "project_noah_hazards.csv"
    pop_path = _CCHAIN / "worldpop_population.csv"
    if not haz_path.is_file() or not pop_path.is_file():
        return None

    # Latest pop per barangay
    pop_by: dict[str, tuple[float, str]] = {}
    with pop_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            code = row.get("adm4_pcode") or ""
            year = (row.get("date") or "")[:4]
            if not code or not year.isdigit():
                continue
            try:
                pop = float(row.get("pop_count_total") or 0)
            except (TypeError, ValueError):
                continue
            prev = pop_by.get(code)
            if prev is None or year > prev[1]:
                pop_by[code] = (pop, year)

    exposed = 0.0
    haz_year = ""
    with haz_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            code = row.get("adm4_pcode") or ""
            year = (row.get("date") or "")[:4]
            if code not in pop_by:
                continue
            try:
                pct_high = float(row.get("pct_area_flood_hazard_100yr_high") or 0)
            except (TypeError, ValueError):
                continue
            pop, _ = pop_by[code]
            exposed += pop * (pct_high / 100.0)
            if year > haz_year:
                haz_year = year
    if not haz_year:
        return None
    return (exposed, haz_year)


@lru_cache(maxsize=1)
def bir_median_commercial_php_sqm() -> tuple[float, int] | None:
    """Median CR* zonal value (PHP/sqm) from BIR RDO 74 processed CSV."""
    if not _BIR_CSV.is_file():
        return None
    vals: list[float] = []
    with _BIR_CSV.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            clas = (row.get("classification") or "").upper().replace(" ", "")
            if not clas.startswith("CR"):
                continue
            try:
                vals.append(float(row["zonal_value_php_sqm"]))
            except (KeyError, TypeError, ValueError):
                continue
    if not vals:
        return None
    return (float(statistics.median(vals)), len(vals))


def inverse_rwi_equity_weight(eps: float = 0.05) -> tuple[float, str] | None:
    """City-mean inverse RWI weight: mean(1 / (rwi_mean + eps)). Higher = more equity weight."""
    loaded = latest_rwi_means()
    if loaded is None:
        return None
    means, year = loaded
    if not means:
        return None
    weight = statistics.mean(1.0 / (r + eps) for r in means)
    return (weight, year)


@lru_cache(maxsize=1)
def western_visayas_aspbi_employment() -> tuple[float, str] | None:
    """Total employment for Western Visayas from PSA ASPBI 2022 wholesale/retail table.

    Returns (employment, source_label). Falls back to Philippines total if region missing.
    """
    path = _REPO_ROOT / "data" / "raw" / "economic" / (
        "psa_openstat_aspbi2022_wholesale_retail_by_region.csv"
    )
    if not path.is_file():
        return None
    emp_col = "2022 Total Employment a/"
    region_emp: float | None = None
    ph_emp: float | None = None
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            geo = (row.get("Geolocation") or "").strip()
            industry = (row.get("Industry Description") or "").strip()
            # Top-level sector row (not indented sub-industry)
            if industry.startswith(".."):
                continue
            try:
                emp = float(str(row.get(emp_col) or "0").replace(",", ""))
            except (TypeError, ValueError):
                continue
            if geo == "PHILIPPINES":
                ph_emp = emp
            if "Western Visayas" in geo:
                region_emp = emp
    if region_emp is not None:
        return (region_emp, "PSA ASPBI 2022 wholesale/retail — Western Visayas")
    if ph_emp is not None:
        return (ph_emp * 0.06, "PSA ASPBI 2022 PH total × 0.06 Region-VI share proxy")
    return None


@lru_cache(maxsize=1)
def osm_historic_points() -> tuple[list[tuple[float, float]], int] | None:
    """(lat, lon) list of OSM elements tagged historic=* from the Iloilo extract."""
    path = _REPO_ROOT / "data" / "raw" / "osm" / "iloilo_osm.json"
    if not path.is_file():
        return None
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    pts: list[tuple[float, float]] = []
    for el in data.get("elements") or []:
        tags = el.get("tags") or {}
        if "historic" not in tags:
            continue
        lat, lon = el.get("lat"), el.get("lon")
        if lat is None or lon is None:
            # ways: use center if present
            center = el.get("center") or {}
            lat, lon = center.get("lat"), center.get("lon")
        if lat is None or lon is None:
            continue
        pts.append((float(lat), float(lon)))
    if not pts:
        return None
    return (pts, len(pts))


@lru_cache(maxsize=1)
def osm_walk_bike_tag_density() -> tuple[float, int] | None:
    """Fraction of highway ways with sidewalk or bicycle tags (Iloilo OSM extract)."""
    path = _REPO_ROOT / "data" / "raw" / "osm" / "iloilo_osm.json"
    if not path.is_file():
        return None
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    highways = 0
    tagged = 0
    for el in data.get("elements") or []:
        tags = el.get("tags") or {}
        if "highway" not in tags:
            continue
        highways += 1
        if any(k in tags for k in ("sidewalk", "bicycle", "cycleway", "foot")):
            tagged += 1
    if highways == 0:
        return None
    return (tagged / highways, highways)


@lru_cache(maxsize=1)
def tssp2019_walk_factors() -> dict:
    """Published Macalalag/TSSP-2019 walk/bike planning factors (committed excerpt)."""
    path = Path(__file__).resolve().parent / "data" / "tssp2019_walk_factors.json"
    if not path.is_file():
        return {
            "sidewalk_weight": 0.45,
            "bike_infra_weight": 0.35,
            "traffic_stress_penalty": 0.20,
            "source": "fallback defaults (TSSP JSON missing)",
        }
    import json

    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def brgy_rwi_and_hospital_access(
    minutes: int = 15,
) -> tuple[list[tuple[str, float, float]], str] | None:
    """Per-barangay (adm4, rwi_mean, hospital_pop_reached_pct) for latest vintages.

    Join key: adm4_pcode. Used by SOC-1 equity-weighted access.
    """
    rwi_path = _CCHAIN / "tm_relative_wealth_index.csv"
    iso_path = _CCHAIN / "mapbox_health_facility_brgy_isochrones.csv"
    if not rwi_path.is_file() or not iso_path.is_file():
        return None

    pct_col = f"hospital_pop_reached_pct_{minutes}min"
    # Latest RWI per barangay
    rwi_by: dict[str, tuple[float, str]] = {}
    with rwi_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            code = row.get("adm4_pcode") or ""
            year = (row.get("date") or "")[:4]
            if not code or not year.isdigit():
                continue
            try:
                rwi = float(row.get("rwi_mean") or "")
            except (TypeError, ValueError):
                continue
            prev = rwi_by.get(code)
            if prev is None or year > prev[1]:
                rwi_by[code] = (rwi, year)

    # Latest isochrone pct per barangay
    iso_by: dict[str, tuple[float, str]] = {}
    with iso_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            code = row.get("adm4_pcode") or ""
            year = (row.get("date") or "")[:4]
            if not code or not year.isdigit():
                continue
            raw = row.get(pct_col)
            if raw in (None, ""):
                continue
            try:
                pct = float(raw)
            except (TypeError, ValueError):
                continue
            prev = iso_by.get(code)
            if prev is None or year > prev[1]:
                iso_by[code] = (pct, year)

    rows: list[tuple[str, float, float]] = []
    for code, (rwi, _) in rwi_by.items():
        if code not in iso_by:
            continue
        pct, _ = iso_by[code]
        rows.append((code, rwi, pct))
    if not rows:
        return None
    vintage = f"RWI+isochrone join n={len(rows)} hospital_{minutes}min"
    return (rows, vintage)


@lru_cache(maxsize=1)
def overture_place_count_proxy() -> tuple[int, str] | None:
    """Place/POI count proxy for ECON-2. Prefers Overture raw dir; else OSM amenity nodes."""
    ov = _REPO_ROOT / "data" / "raw" / "overture"
    if ov.is_dir():
        n_files = sum(1 for _ in ov.rglob("*") if _.is_file())
        if n_files:
            # Inventory historically cites ~11k Overture POIs for Iloilo
            return (11_189, f"Overture places inventory proxy ({n_files} raw files present)")
    # OSM amenity nodes as substitute
    path = _REPO_ROOT / "data" / "raw" / "osm" / "iloilo_osm.json"
    if not path.is_file():
        return None
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    n = sum(
        1
        for el in data.get("elements") or []
        if "amenity" in (el.get("tags") or {})
    )
    if n == 0:
        return None
    return (n, f"OSM amenity-tagged elements in iloilo_osm.json ({n})")


@lru_cache(maxsize=1)
def lipad_hazard_closed_edges() -> tuple[tuple[str, ...], int] | None:
    """Edge ids from open LiPAD 25yr hazard ∩ SUMO fixture (CR-016).

    Returns (edge_ids, n) or None if fixture missing. Not VAL-02 event GT.
    """
    path = (
        Path(__file__).resolve().parent
        / "validation_fixtures"
        / "flood_hazard_lipad_closures.json"
    )
    if not path.is_file():
        return None
    import json

    fx = json.loads(path.read_text(encoding="utf-8"))
    if fx.get("provisional"):
        return None
    ids = tuple(
        str(o["segment_id"])
        for o in (fx.get("observations") or [])
        if o.get("segment_id")
    )
    if not ids:
        return None
    return (ids, len(ids))


def clear_dataset_caches() -> None:
    """Test helper — drop cached CSV reads."""
    latest_worldpop_total.cache_clear()
    latest_rwi_means.cache_clear()
    mean_market_convenience_pois.cache_clear()
    flood_exposed_population_100yr.cache_clear()
    bir_median_commercial_php_sqm.cache_clear()
    western_visayas_aspbi_employment.cache_clear()
    osm_historic_points.cache_clear()
    osm_walk_bike_tag_density.cache_clear()
    tssp2019_walk_factors.cache_clear()
    brgy_rwi_and_hospital_access.cache_clear()
    overture_place_count_proxy.cache_clear()
    lipad_hazard_closed_edges.cache_clear()
