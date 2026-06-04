#!/usr/bin/env python3
"""MATRIX — fetch Economic-dimension data for the Iloilo pilot.

Stdlib only (no pip installs). Idempotent: skips files already present.
    python data/fetch/fetch_economic.py

Sources acquired here:
  PSA-PVRTY  PSA OpenStat DB__3D  — Poverty thresholds + incidence by region/province (2006-2015)
               Includes Region VI and Iloilo province rows.
               Vintage: 2015 (latest in this OpenStat table; 2023 FIES not yet published here).
  PSA-TOUR   PSA OpenStat DB__2I  — National inbound tourism expenditure 2000-2024.
               National-level only (no regional breakdown in OpenStat).
               Best available proxy for tourism magnitude; Region VI share estimated separately.
  PSA-TRADE  PSA OpenStat DB__2D  — Wholesale/retail trade establishments 2015 (national).
               Partial ASPBI proxy — only Wholesale & Retail sector, 2015 vintage.
  PSA-GVA    PSA OpenStat DB__2B__NA — Gross Value Added: Accommodation & Food Service 2000-2025.
               National; use as activity proxy for tourism-linked economic sectors.
  WB-ECON    World Bank Open Data API — Philippines national economic indicators 2019-2024:
               GDP per capita (current USD), GINI index, poverty headcount,
               unemployment rate. Confidence: Medium (national — Iloilo gap widened by
               CCHAIN RWI which provides barangay-level relative wealth).

NOT scriptable (manual browser download required):
  BIR-ZV     BIR Zonal Values RDO 74 (Iloilo City) — the land-value baseline.
               bir-cdn.bir.gov.ph returns HTTP 403 to all scripted requests.
               The BIR website (bir.gov.ph/zonal-values) is a JavaScript SPA;
               PDF links are loaded dynamically and all CDN paths block non-browser clients.
               Manual path: https://www.bir.gov.ph/zonal-values
               → find "Region VI" → click "RDO 74 — Iloilo City" → save PDF to
               data/raw/economic/BIR_ZV_RDO74_IloiloCity.pdf
               (Confidence: Medium — zonal values are updated periodically, not annual)

  ASPBI-2023 PSA ASPBI 2023 (Annual Survey of Philippine Business & Industry) —
               establishments, employment, receipts by region.
               psa.gov.ph returns HTTP 403 to scripts even with browser UA + Referer.
               OpenStat has only the 2015 vintage of the wholesale/retail sector sub-table.
               Manual path: https://psa.gov.ph/statistics/establishments
               → "ASPBI 2023 Preliminary Results" or nearest available release
               → download Excel for Region VI / Western Visayas

  FIES-2023  PSA Family Income and Expenditure Survey 2023 — income/expenditure by region.
               psa.gov.ph returns HTTP 403.  OpenStat DB__3D has poverty thresholds to 2015;
               the 2021 and 2023 FIES releases are not yet in OpenStat.
               Manual path: https://psa.gov.ph/statistics/income-expenditure/fies
               → "2023 FIES" → Summary Statistics → Region VI

  DOT-TOUR   DOT tourism arrivals by region — visitor counts for Iloilo / Region VI 2024.
               tourism.gov.ph is a JavaScript SPA; file paths are not exposed via direct links.
               OpenStat DB__2I has national-level expenditure only (no regional arrivals).
               Manual path: https://tourism.gov.ph/tourism-statistics
               or https://tourism.gov.ph/tourism_dem_sup_pub.aspx
               → look for "Visitor Arrivals by Region" 2024 Excel

See INVENTORY.md for license, vintage, and confidence annotations.
"""
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "raw" / "economic"
UA = "Mozilla/5.0 (MATRIX/data-fetch; +https://github.com/delatorrecj/matrix)"
TIMEOUT = 120

results: dict[str, list] = {"ok": [], "skip": [], "fail": []}


# ---------------------------------------------------------------------------
# helpers (mirror fetch_open.py conventions)
# ---------------------------------------------------------------------------

def _open(url, data=None, extra_headers=None):
    """Open URL with browser UA; retry once without TLS verification."""
    headers = {"User-Agent": UA}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        return urllib.request.urlopen(req, timeout=TIMEOUT)
    except (ssl.SSLError, urllib.error.URLError) as e:
        if isinstance(e, urllib.error.HTTPError):
            raise
        return urllib.request.urlopen(
            req, timeout=TIMEOUT, context=ssl._create_unverified_context())


def grab(key, url, fname):
    """Download url → RAW/fname; skip if file already present and non-empty."""
    dest = RAW / fname
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  skip  {key}: exists ({dest.stat().st_size:,} B)")
        results["skip"].append(key)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _open(url) as r:
            payload = r.read()
        dest.write_bytes(payload)
        print(f"  OK    {key}: {len(payload):,} B -> raw/economic/{fname}")
        results["ok"].append(key)
    except Exception as e:
        code = getattr(e, "code", "")
        print(f"  FAIL  {key}: {code} {e}  ({url})")
        results["fail"].append(key)


def pxweb_csv(key, table_path, fname, query_filter=None):
    """POST a PX-Web v1 query to PSA OpenStat and save as CSV.

    table_path: path segment after /api/v1/en/  e.g. 'DB/DB__3D/'
    query_filter: list of {"code": "VarCode", "selection": {"filter": "item", "values": [...]}}
                  Pass None to select all values (creates a larger but complete file).
    """
    dest = RAW / fname
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  skip  {key}: exists ({dest.stat().st_size:,} B)")
        results["skip"].append(key)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    base = "https://openstat.psa.gov.ph/PXWeb/api/v1/en/"
    url = base + table_path + "?outputFormat=csv"
    body = json.dumps({
        "query": query_filter or [],
        "response": {"format": "csv"},
    }).encode()
    try:
        with _open(url, data=body,
                   extra_headers={"Content-Type": "application/json"}) as r:
            payload = r.read()
        dest.write_bytes(payload)
        # basic sanity: CSV should start with a quote character
        first = payload[:1]
        if first not in (b'"', b',', b'\xef'):  # UTF-8 BOM also OK
            print(f"  WARN  {key}: unexpected first byte {first!r} — may not be CSV")
        print(f"  OK    {key}: {len(payload):,} B -> raw/economic/{fname}")
        results["ok"].append(key)
    except Exception as e:
        code = getattr(e, "code", "")
        print(f"  FAIL  {key}: {code} {e}")
        results["fail"].append(key)


def worldbank_json(key, indicator, fname, country="PH", mrv=8):
    """Fetch World Bank indicator time-series as JSON and save."""
    dest = RAW / fname
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  skip  {key}: exists ({dest.stat().st_size:,} B)")
        results["skip"].append(key)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = (f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
           f"?format=json&mrv={mrv}&per_page=50")
    try:
        with _open(url) as r:
            payload = r.read()
        # validate: should be a JSON array
        parsed = json.loads(payload)
        if not isinstance(parsed, list) or len(parsed) < 2:
            raise ValueError(f"unexpected WB response structure: {payload[:200]}")
        records = [r for r in (parsed[1] or []) if r.get("value") is not None]
        dest.write_bytes(payload)
        print(f"  OK    {key}: {len(records)} obs -> raw/economic/{fname}")
        results["ok"].append(key)
    except Exception as e:
        print(f"  FAIL  {key}: {e}")
        results["fail"].append(key)


# ---------------------------------------------------------------------------
# fetch tasks
# ---------------------------------------------------------------------------

def fetch_psa_openstat():
    """PSA OpenStat PX-Web API (public, no auth required, returns CSV/JSON)."""
    print("== PSA OpenStat PX-Web ==")

    # --- Poverty thresholds + incidence by region/province (FIES proxy, up to 2015) ---
    # DB__3D = Annual Per Capita Poverty Threshold, Poverty Incidence and Magnitude
    # of Poor Families, by Region/Province. Includes "Region VI" and "..Iloilo" rows.
    # Note: this is the FIES-derived poverty table; the 2021/2023 FIES releases are not
    # yet available in OpenStat — see manual access notes at top of this file.
    pxweb_csv(
        "PSA-PVRTY",
        "DB/DB__3D/",
        "psa_openstat_poverty_threshold_by_region.csv",
        query_filter=None,  # all rows — file is ~50 KB
    )

    # --- National inbound tourism expenditure 2000-2024 ---
    # DB__2I = Inbound Tourism Expenditure by Product at Current Prices.
    # National-level only. Useful as denominator for tourism share estimation.
    # DOT regional visitor arrivals are not in OpenStat (manual download required).
    pxweb_csv(
        "PSA-TOUR",
        "DB/DB__2I/",
        "psa_openstat_tourism_expenditure_national.csv",
        query_filter=None,
    )

    # --- Wholesale & Retail trade establishments 2015 ---
    # DB__2D = Summary Statistics for Wholesale and Retail Trade Establishments.
    # Partial ASPBI proxy — 2015 vintage, national totals, no regional breakdown.
    # Full 2023 ASPBI is not available via OpenStat (manual access required).
    pxweb_csv(
        "PSA-TRADE",
        "DB/DB__2D/",
        "psa_openstat_trade_establishments_2015.csv",
        query_filter=None,
    )

    # --- GVA in Accommodation & Food Service (tourism-linked sectors) 2000-2025 ---
    # DB__2B__NA = Gross Value Added in Accommodation and Food Service Activities.
    # National; 2000-2025. Useful tourism-sector economic activity proxy.
    pxweb_csv(
        "PSA-GVA",
        "DB/DB__2B__NA/",
        "psa_openstat_gva_accommodation_food_service.csv",
        query_filter=None,
    )

    # --- FIES 2023 — income & expenditure by Region/Province/HUC (incl. City of Iloilo) ---
    # DB 1E (Income and Consumption) -> IE (Family Income and Expenditure Survey).
    # The full 2023 release IS on OpenStat (the older "not in OpenStat" note was stale):
    # Table 1 has Region VI, Iloilo province, and a City-of-Iloilo HUC row.
    pxweb_csv(
        "FIES2023-IE",
        "DB/1E/IE/001E3ANIE0.px",
        "psa_openstat_fies2023_income_expenditure_by_region.csv",
        query_filter=None,
    )
    pxweb_csv(
        "FIES2023-GINI",
        "DB/1E/IE/0051E3AGCF0.px",
        "psa_openstat_fies2023_gini_by_region.csv",
        query_filter=None,
    )

    # --- ASPBI 2022 — establishments & employment by region & sector ---
    # DB 2D (Services Statistics) -> 2022 ASPBI. 2022 is the latest on OpenStat
    # (2023 not yet published there). Geolocation includes "Western Visayas".
    # Far richer than the 2015 wholesale/retail subset previously in hand.
    pxweb_csv(
        "ASPBI2022-WRT",
        "DB/2D/2022/0222D4BAG00.px",
        "psa_openstat_aspbi2022_wholesale_retail_by_region.csv",
        query_filter=None,
    )
    pxweb_csv(
        "ASPBI2022-ACC",
        "DB/2D/2022/0222D4BAI00.px",
        "psa_openstat_aspbi2022_accommodation_food_by_region.csv",
        query_filter=None,
    )


def fetch_worldbank():
    """World Bank Open Data API — Philippines national economic indicators.

    These are national-level series. Barangay-level relative wealth for Iloilo
    is better captured by CCHAIN tm_relative_wealth_index.csv (already fetched).
    These provide the macro context (GDP per capita, poverty, inequality) that
    the economic module uses for confidence calibration.

    Confidence: Medium — national proxies for a city-level model.
    """
    print("== World Bank Open Data ==")
    indicators = [
        # (WB indicator code, filename, description for log)
        ("NY.GDP.PCAP.CD",
         "wb_ph_gdp_per_capita_usd.json",
         "GDP per capita current USD"),
        ("SI.POV.GINI",
         "wb_ph_gini_index.json",
         "GINI index"),
        ("SI.POV.DDAY",
         "wb_ph_poverty_headcount_215usd.json",
         "Poverty headcount at $2.15/day (%)"),
        ("SL.UEM.TOTL.NE.ZS",
         "wb_ph_unemployment_rate.json",
         "Unemployment rate (national modelled estimate)"),
        ("NY.GNP.PCAP.CD",
         "wb_ph_gni_per_capita_atlas.json",
         "GNI per capita Atlas method current USD"),
        ("SP.URB.TOTL.IN.ZS",
         "wb_ph_urban_population_pct.json",
         "Urban population (% of total)"),
        ("NY.GDP.MKTP.KD.ZG",
         "wb_ph_gdp_growth_rate.json",
         "GDP growth rate (annual %)"),
    ]
    for ind_code, fname, _desc in indicators:
        worldbank_json(f"WB-{ind_code[:12]}", ind_code, fname, country="PH", mrv=8)


def fetch_hdx_poverty():
    """HDX — Philippines poverty statistics (NSCB income by region, older vintage).

    This XLSX file from the HDX Philippines poverty package includes annual
    per-capita poverty thresholds by region — similar to OpenStat DB__3D but
    in Excel format and from an earlier release. Kept as a cross-reference.
    HDX S3 links use signed URLs — the CKAN redirect follows correctly.
    """
    print("== HDX — Poverty statistics XLSX ==")
    # Using the CKAN redirect URL (not the signed S3 URL, which changes each request)
    grab(
        "HDX-PVRTY",
        ("https://data.humdata.org/dataset/172bc2ba-2318-4b50-9c15-d5c5d3cd5186"
         "/resource/d8eb16a9-81ed-4375-974e-05eb99004c13/download/"
         "200604_updated-annual-per-capita-poverty-threshold-poverty-incidence-"
         "and-magnitude-of-poor-fami.xlsx"),
        "hdx_ph_poverty_threshold_by_region.xlsx",
    )


def manual_access_reminder():
    """Print a clear reminder of what still needs manual download."""
    print("""
== STATUS OF THE FOUR ONCE-MANUAL ECONOMIC SETS (updated 2026-06-03) ==

[DONE manually] BIR-ZV  Zonal Values RDO 74, DO 17-2021 (4th rev) -- .xls in hand at
   data/raw/economic/BIR_ZV_RDO74_IloiloCity.xls (10 sheets; Sheet 9 = current schedule).
   Parse to a clean CSV with:  python data/fetch/parse_bir_zonal.py
   Source: bir.gov.ph/zonal-values -> RR 11 -> RDO 74 -> "View RDO excel".
   (Manual because bir.gov.ph SPA + bir-cdn 403 to scripts.)

[NOW SCRIPTED] FIES 2023 + ASPBI 2022 -- fetched above from OpenStat. The 403 wall is on
   psa.gov.ph, NOT openstat.psa.gov.ph. FIES 2023 (DB 1E/IE) includes a City-of-Iloilo
   HUC row; ASPBI 2022 (DB 2D/2022) is by region & sector. (2023 ASPBI not yet on
   OpenStat -> 2022 is the latest available.) No manual step required.

[UNAVAILABLE on OpenStat] DOT-TOUR  Visitor Arrivals BY REGION 2024.
   OpenStat 2I carries tourism EXPENDITURE only (national) -- already in hand as
   psa_openstat_tourism_expenditure_national.csv. Regional ARRIVALS exist only on
   tourism.gov.ph (a JS SPA). Browser-download only if the fidelity is needed:
   tourism.gov.ph/tourism-statistics -> "Visitor Arrivals by Region" 2024 ->
   save to data/raw/economic/DOT_VisitorArrivals_Region_2024.xlsx
""")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {RAW}\n")

    fetch_psa_openstat()
    fetch_worldbank()
    fetch_hdx_poverty()
    manual_access_reminder()

    print("== summary ==")
    print(f"  fetched: {len(results['ok'])}"
          f"  skipped: {len(results['skip'])}"
          f"  failed:  {len(results['fail'])}")
    if results["fail"]:
        print("  failed keys:", ", ".join(results["fail"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
