# CI SUMO fixture (Iloilo City Proper)

Tiny OSM extract used by GitHub Actions to build `iloilo.net.xml` + `iloilo.rou.xml`
so kernel tests that skip on a missing net actually run. Not a substitute for the
full ~42 MB pilot network.

- **Bbox** (lat_min, lon_min, lat_max, lon_max): `10.690, 122.548, 10.732, 122.576`
  — City Proper / inner Diversion, not the full OSM-ILO bbox.
- **Source:** subset of `data/raw/osm/iloilo_osm.json` (OSM-ILO, ODbL).
- **Regenerate** (needs the gitignored Overpass dump):

  ```
  python app/packages/data/extract_ci_osm.py
  ```

`old_name=Iznart Street` is folded into `name` so the Iznart keyword test resolves.
`Diversion Road` is appended on Benigno S. Aquino Jr. Avenue (VAL-01 / Calderon
corridor alias in `build_validation_report.py`).
