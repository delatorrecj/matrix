#!/usr/bin/env python3
"""MATRIX — fetch direct, open, contact-free data for the Iloilo pilot.

Stdlib only (no pip installs). Idempotent: skips files already present.
    python fetch/fetch_open.py
See INVENTORY.md for the full manifest, licenses, and vintages.
"""
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "raw"
UA = "Mozilla/5.0 (MATRIX/data-fetch; +https://github.com/delatorrecj/matrix)"
TIMEOUT = 180

# Iloilo City Proper bounding box (S, W, N, E)
BBOX = "10.65,122.50,10.78,122.61"

# (key, url, path under raw/) — high-confidence direct HTTP downloads
DIRECT = [
    ("LIT-CALDERON",
     "https://ncts.upd.edu.ph/tssp/wp-content/uploads/2018/08/Calderon14.pdf",
     "literature/Calderon2014_Iloilo_BRT.pdf"),
    ("LIT-BIKE19",
     "https://ncts.upd.edu.ph/tssp/wp-content/uploads/2019/09/"
     "TSSP2019-04_Factors-Influencing-Bicycle-Use-in-a-Medium-Sized-City-the-Case-of-Iloilo-1-City-Philippines.pdf",
     "literature/TSSP2019_Iloilo_bicycle_use.pdf"),
    ("LIT-POPGIS",
     "https://isprs-archives.copernicus.org/articles/XLVI-4-W6-2021/185/2021/"
     "isprs-archives-XLVI-4-W6-2021-185-2021.pdf",
     "literature/ISPRS2021_Iloilo_pop_forecast.pdf"),
]

# MANUAL (browser) — confirmed not programmatically fetchable; see INVENTORY.md:
#   CENSUS20  psa.gov.ph returns 403 to scripts/curl even with UA+Referer.
#             Substitute: CCHAIN worldpop_population.csv + POPCEN24 (2024, current).
#   LIT-CDP   the published CDP PDF URL 404s; get the current link from the CPDO
#             page https://iloilocity.gov.ph/main/city-planning-and-development-office-2/

results = {"ok": [], "skip": [], "fail": []}


def _open(url, data=None, extra_headers=None):
    """Open a URL with a browser UA; retry once without TLS verification
    (several PH gov sites ship incomplete certificate chains)."""
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


def grab(key, url, relpath):
    dest = RAW / relpath
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  skip  {key}: exists ({dest.stat().st_size:,} B)")
        results["skip"].append(key)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _open(url) as r:
            payload = r.read()
        dest.write_bytes(payload)
        print(f"  OK    {key}: {len(payload):,} B -> raw/{relpath}")
        results["ok"].append(key)
    except Exception as e:
        code = getattr(e, "code", "")
        print(f"  FAIL  {key}: {code} {e}  ({url})")
        results["fail"].append(key)


def overpass():
    key, dest = "OSM-ILO", RAW / "osm/iloilo_osm.json"
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  skip  {key}: exists ({dest.stat().st_size:,} B)")
        results["skip"].append(key)
        return
    query = f"""
[out:json][timeout:240];
(
  way["highway"]({BBOX});
  relation["route"~"bus|jeepney|share_taxi|minibus|tram"]({BBOX});
  node["public_transport"]({BBOX});
  way["public_transport"]({BBOX});
  node["amenity"~"school|hospital|clinic|marketplace|university|townhall|ferry_terminal"]({BBOX});
  way["amenity"~"marketplace|school|hospital|university"]({BBOX});
  node["historic"]({BBOX});
  way["historic"]({BBOX});
  way["landuse"]({BBOX});
  way["leisure"~"park|pitch|garden"]({BBOX});
);
out body geom;
"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = urllib.parse.urlencode({"data": query}).encode()
        # overpass-api.de returns 406 for browser-like UAs and without an Accept header
        with _open("https://overpass-api.de/api/interpreter", data=data,
                   extra_headers={"Accept": "application/json",
                                  "User-Agent": "overpass-matrix-fetch"}) as r:
            payload = r.read()
        obj = json.loads(payload)
        n = len(obj.get("elements", []))
        dest.write_bytes(payload)
        print(f"  OK    {key}: {n:,} elements, {len(payload):,} B -> raw/osm/iloilo_osm.json")
        results["ok"].append(key) if n else results["fail"].append(key)
    except Exception as e:
        print(f"  FAIL  {key}: {e}")
        results["fail"].append(key)


def ckan(key, base, dataset_id, subdir, max_bytes=None):
    """Download a CKAN dataset's resources (HDX, data.gov.ph).

    max_bytes: skip resources larger than this (national bulk dumps we'd only
    subset to Iloilo anyway). The full files remain available on the portal.
    Re-downloads any local file whose size doesn't match the remote size
    (recovers from interrupted runs).
    """
    api = f"{base}/api/3/action/package_show?id={dataset_id}"
    try:
        with _open(api) as r:
            pkg = json.loads(r.read())
        resources = pkg["result"]["resources"]
    except Exception as e:
        print(f"  FAIL  {key}: CKAN lookup failed ({e})")
        results["fail"].append(key)
        return
    for res in resources:
        url = res.get("url")
        if not url:
            continue
        try:
            size = int(res.get("size") or 0)
        except (TypeError, ValueError):
            size = 0
        name = res.get("name") or url.rsplit("/", 1)[-1]
        ext = (res.get("format") or "").lower()
        fname = name if "." in name else (f"{name}.{ext}" if ext else name)
        fname = "".join(c if c.isalnum() or c in "._- " else "_" for c in fname).strip()
        if max_bytes and size and size > max_bytes:
            print(f"  skip  {key}:{fname[:28]} - {size/1e6:.0f} MB bulk dump (full file on portal)")
            continue
        dest = RAW / subdir / fname
        if dest.exists() and size and dest.stat().st_size != size:
            dest.unlink()  # partial/interrupted — redo
        grab(f"{key}:{fname[:28]}", url, f"{subdir}/{fname}")


def main():
    print("== direct HTTP ==")
    for key, url, path in DIRECT:
        grab(key, url, path)
    print("== OpenStreetMap (Overpass) ==")
    overpass()
    print("== HDX / CKAN ==")
    # Project CCHAIN: keep the ~25 barangay-level / derived tables; skip the 5
    # national hourly climate dumps (~1.8 GB) — subset those from HDX only if needed.
    ckan("CCHAIN", "https://data.humdata.org", "project-cchain", "hdx", max_bytes=60_000_000)
    print("\n== summary ==")
    print(f"  fetched: {len(results['ok'])}  skipped: {len(results['skip'])}  failed: {len(results['fail'])}")
    if results["fail"]:
        print("  failed keys:", ", ".join(results["fail"]))
        print("  (see INVENTORY.md for landing pages / alternate access)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
