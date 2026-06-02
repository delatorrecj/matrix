#!/usr/bin/env python3
"""MATRIX — subset CCHAIN (and any *_pcode keyed table) to Iloilo City.

CCHAIN ships 8 cities in one file; we only need Iloilo. This filters every
barangay-keyed CSV in raw/hdx/ to Iloilo City barangays (PSGC adm4 prefix
PH063022...) and writes analysis-ready, git-tracked CSVs to processed/cchain_iloilo/.
Tables without a *_pcode column (small lookups: calendar, disease, location) are
copied whole. Stdlib only.

    python fetch/subset_iloilo.py
"""
import csv
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "raw" / "hdx"
DST = ROOT / "processed" / "cchain_iloilo"
PREFIX = "PH063022"          # Iloilo City (region 06, prov 30, city 22)

csv.field_size_limit(10 ** 7)  # WKT geometry fields can be large


def pcode_col(header):
    """First column whose name contains 'pcode' (adm4 preferred over adm3)."""
    cands = [h for h in header if "pcode" in h.lower()]
    cands.sort(key=lambda h: ("adm4" not in h.lower(), h))  # adm4 first
    return cands[0] if cands else None


def main():
    if not SRC.exists():
        print(f"no source dir {SRC} — run fetch_open.py first")
        return 1
    DST.mkdir(parents=True, exist_ok=True)
    total_kept = total_files = copied = 0
    for path in sorted(SRC.glob("*.csv")):
        out = DST / path.name
        with path.open(encoding="utf-8", newline="") as fh:
            reader = csv.reader(fh)
            try:
                header = next(reader)
            except StopIteration:
                continue
            col = pcode_col(header)
            if col is None:
                fh.close()
                shutil.copy2(path, out)
                print(f"  copy  {path.name} (no pcode column - kept whole)")
                copied += 1
                continue
            idx = header.index(col)
            kept = 0
            with out.open("w", encoding="utf-8", newline="") as w:
                writer = csv.writer(w)
                writer.writerow(header)
                for row in reader:
                    if len(row) > idx and row[idx].startswith(PREFIX):
                        writer.writerow(row)
                        kept += 1
        total_files += 1
        total_kept += kept
        print(f"  {path.name:<46} {kept:>7} Iloilo rows  (key: {col})")
    print(f"\nfiltered {total_files} tables ({total_kept:,} Iloilo rows) + {copied} lookups "
          f"-> processed/cchain_iloilo/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
