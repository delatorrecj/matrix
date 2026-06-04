#!/usr/bin/env python3
"""MATRIX — parse BIR zonal values RDO 74 (Iloilo) into a clean CSV.

Input : data/raw/economic/BIR_ZV_RDO74_IloiloCity.xls   (manual download — see INVENTORY.md)
Output: data/processed/economic/bir_zonal_rdo74_2021.csv

The .xls is a 10-sheet revision archive. Sheet 9 (DO17-2021) is the CURRENT
schedule (4th revision, effective 2021-09-09). It is laid out as a legal
document: a ~110-row preamble + classification legend, then a 4-column table:

  col0 = street / location   (sparse -> forward-filled downward)
  col1 = vicinity / boundary description
  col2 = classification code (RR, CR, RC, I, CR*, ...)  -- per the sheet legend
  col3 = zonal value, PHP per square metre

This skips the preamble and emits one row per priced entry. Idempotent
(overwrites the CSV). stdlib + pandas/xlrd.

    python data/fetch/parse_bir_zonal.py
"""
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    sys.exit("needs: pip install pandas xlrd")

ROOT = Path(__file__).resolve().parents[1]            # .../data
SRC = ROOT / "raw" / "economic" / "BIR_ZV_RDO74_IloiloCity.xls"
DST = ROOT / "processed" / "economic" / "bir_zonal_rdo74_2021.csv"
SHEET = "Sheet 9 (DO17-2021)"


def realnum(x):
    """Return float(x) for a genuine number, else None (NaN/blank/text -> None)."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    try:
        return float(str(x).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _txt(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return str(x).strip()


def main():
    if not SRC.exists():
        sys.exit(f"missing {SRC}\n  -> download per INVENTORY.md (BIR-ZV): "
                 f"bir.gov.ph/zonal-values -> RR 11 -> RDO 74 -> 'View RDO excel'")
    df = pd.read_excel(SRC, sheet_name=SHEET, header=None)

    rows = []
    street = ""
    for i in range(len(df)):
        c0, c1, c2, c3 = (df.iloc[i, j] for j in range(4))
        # carry the most recent street label down (col0 is sparse in the source)
        if _txt(c0):
            street = _txt(c0)
        zv = realnum(c3)
        cls = _txt(c2)
        if zv is None or not cls:
            continue  # a real value row needs both a price and a classification code
        rows.append({
            "street": street,
            "vicinity": _txt(c1),
            "classification": cls,
            "zonal_value_php_sqm": zv,
        })

    out = pd.DataFrame(rows, columns=["street", "vicinity", "classification",
                                      "zonal_value_php_sqm"])
    DST.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(DST, index=False, encoding="utf-8")

    rel = DST.relative_to(ROOT.parent)
    print(f"OK  {len(out):,} priced entries -> {rel}")
    if len(out):
        lo, hi = out.zonal_value_php_sqm.min(), out.zonal_value_php_sqm.max()
        print(f"    PHP/m^2 range: {lo:,.0f} - {hi:,.0f}")
        print("    classifications present:")
        print("      " + out.classification.value_counts().head(10)
              .to_string().replace("\n", "\n      "))
        print("    sample rows:")
        print(out.head(6).to_string(index=False, max_colwidth=34))


if __name__ == "__main__":
    main()
