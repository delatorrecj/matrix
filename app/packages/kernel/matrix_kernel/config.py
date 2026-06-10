"""Per-city kernel configuration (CityConfig) — the city-agnostic seam (MATRIX.md §6).

MATRIX scales geographically at the API level: swap the OSM bbox + SUMO net/demand
files and reweight the persona mode-share anchor — the engine itself stays
city-agnostic. This module is the single source of those per-city facts. **Iloilo
(the pilot) is the zero-behavior-change default**: with no env vars and no config
file, the values below are exactly the constants that previously lived hardcoded in
baseline.py and personas.py.

Resolution precedence (highest wins), all stdlib:

  1. Env vars      MATRIX_CITY        display name; slug auto-derived unless ...
                   MATRIX_CITY_SLUG   Redis-key slug (baseline:{slug}:latest,
                                      personas:{slug}:v1)
                   MATRIX_NET_PATH    SUMO network file
                   MATRIX_ROU_PATH    SUMO demand/route file
                   MATRIX_BBOX        "lat_min,lon_min,lat_max,lon_max"
                   MATRIX_MODE_SHARE  JSON dict {mode: fraction}, must sum to ~1.0
  2. Config file   MATRIX_CITY_CONFIG=path to a JSON or TOML file (keys: name, slug,
                   bbox, net_path, rou_path, mode_share, baseline_key,
                   persona_pool_key; relative paths resolve against the file's dir)
  3. Iloilo defaults (below)

Consumers bind module constants at import time (baseline.py: NET/ROU/BASELINE_KEY;
personas.py: ILOILO_MODE_SHARE/PERSONA_POOL_KEY), so set MATRIX_* in the process
environment *before* importing the kernel. The API/orchestrator should read
``get_city_config()`` directly for name/slug/bbox.
"""
from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

KERNEL_DATA = Path(__file__).resolve().parent.parent / "data"

# Iloilo mode-share ANCHOR — the ground truth the bias auditor enforces to +/-3%.
# Literature-derived (Calderon 2014 BRT study + Enhanced LPTRP jeepney-dominant
# context); best-available estimate, NOT a live survey -> Behavioral *behavior*
# confidence = M (the documented "soft spot" in READINESS.md; methods §3.1, §4).
# Glass-box note: per-city anchors are bias-audit inputs — any replacement anchor
# (env/file override) MUST document its source the same way.
ILOILO_MODE_SHARE: dict[str, float] = {
    "jeepney": 0.55,
    "private_car": 0.15,
    "motorcycle": 0.15,
    "walk": 0.10,
    "bicycle": 0.05,
}

# Iloilo City Proper pilot bbox (lat_min, lon_min, lat_max, lon_max) — the OSM
# Overpass bbox from MATRIX_Iloilo_Data_Sources.md (mirrored in app/.env.example).
ILOILO_BBOX: tuple[float, float, float, float] = (10.65, 122.50, 10.78, 122.61)

_CONFIG_FILE_KEYS = frozenset(
    {"name", "slug", "bbox", "net_path", "rou_path", "mode_share",
     "baseline_key", "persona_pool_key"}
)


@dataclass(frozen=True)
class CityConfig:
    """Everything the kernel needs to know about one city.

    ``baseline_key`` / ``persona_pool_key`` derive from ``slug`` when left empty
    (``baseline:{slug}:latest`` / ``personas:{slug}:v1`` — the historical Iloilo key
    shapes), but an explicit override (config file) wins.
    """

    name: str
    slug: str
    bbox: tuple[float, float, float, float]  # (lat_min, lon_min, lat_max, lon_max)
    net_path: Path
    rou_path: Path
    mode_share: dict[str, float]
    baseline_key: str = ""
    persona_pool_key: str = ""

    def __post_init__(self) -> None:
        # The slug namespaces Redis keys — reject shapes that would corrupt them
        # (":" is the key separator; whitespace/uppercase invite typo'd duplicates).
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", self.slug):
            raise ValueError(
                f"city slug {self.slug!r} must be lowercase [a-z0-9-] (got it from "
                "MATRIX_CITY_SLUG / config file? try a plain slug like 'iloilo')"
            )
        if not self.baseline_key:
            object.__setattr__(self, "baseline_key", f"baseline:{self.slug}:latest")
        if not self.persona_pool_key:
            object.__setattr__(self, "persona_pool_key", f"personas:{self.slug}:v1")


# The pilot default. Values are byte-identical to the pre-config hardcoded constants
# (zero behavior change with no MATRIX_* env vars / config file set).
ILOILO = CityConfig(
    name="Iloilo City",
    slug="iloilo",
    bbox=ILOILO_BBOX,
    net_path=KERNEL_DATA / "iloilo.net.xml",
    rou_path=KERNEL_DATA / "iloilo.rou.xml",
    mode_share=dict(ILOILO_MODE_SHARE),
)


def _slugify(name: str) -> str:
    """Lowercase, non-alphanumerics -> '-' ('Cebu City' -> 'cebu-city')."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError(f"city name {name!r} produces an empty slug")
    return slug


def _parse_bbox(raw: object) -> tuple[float, float, float, float]:
    """Accept 'lat_min,lon_min,lat_max,lon_max' (env) or a 4-number list (file)."""
    try:
        parts = [p.strip() for p in raw.split(",")] if isinstance(raw, str) else list(raw)  # type: ignore[arg-type]
    except TypeError as e:
        raise ValueError(f"bbox must be a comma string or 4-number list, got {raw!r}") from e
    if len(parts) != 4:
        raise ValueError(f"bbox needs 4 numbers (lat_min,lon_min,lat_max,lon_max), got {raw!r}")
    try:
        lat_min, lon_min, lat_max, lon_max = (float(p) for p in parts)
    except (TypeError, ValueError) as e:
        raise ValueError(f"bbox values must be numeric, got {raw!r}") from e
    if not (lat_min < lat_max and lon_min < lon_max):
        raise ValueError(f"bbox must satisfy lat_min<lat_max and lon_min<lon_max, got {raw!r}")
    return (lat_min, lon_min, lat_max, lon_max)


def _parse_mode_share(raw: object) -> dict[str, float]:
    """Accept a JSON string (env) or a dict (file); validate it is a distribution.

    The anchor feeds the bias auditor (±3% enforcement), so a malformed anchor is a
    glass-box violation — fail loudly here, not downstream.
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"mode share is not valid JSON: {e}") from e
    if not isinstance(raw, dict) or not raw:
        raise ValueError(f"mode share must be a non-empty {{mode: fraction}} dict, got {raw!r}")
    try:
        share = {str(mode): float(frac) for mode, frac in raw.items()}
    except (TypeError, ValueError) as e:
        raise ValueError(f"mode-share fractions must be numeric, got {raw!r}") from e
    if any(frac < 0.0 for frac in share.values()):
        raise ValueError(f"mode-share fractions must be >= 0, got {share!r}")
    total = sum(share.values())
    if abs(total - 1.0) > 0.01:
        raise ValueError(f"mode share must sum to ~1.0 (bias-audit anchor), got {total:.3f}")
    return share


def _resolve_path(base_dir: Path, raw: object) -> Path:
    """Config-file paths may be relative — resolve them against the file's directory."""
    p = Path(str(raw))
    return p if p.is_absolute() else (base_dir / p).resolve()


def _read_config_file(path: Path) -> dict:
    """Load a JSON (default) or TOML (.toml) city-config file; reject unknown keys."""
    if not path.is_file():
        raise FileNotFoundError(f"MATRIX_CITY_CONFIG={path} does not exist")
    if path.suffix.lower() == ".toml":
        import tomllib  # stdlib (requires-python >=3.12)

        data = tomllib.loads(path.read_text(encoding="utf-8"))
    else:
        # utf-8-sig: tolerate the BOM that Windows editors/PowerShell often prepend.
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"city config {path} must be a JSON object / TOML table")
    unknown = set(data) - _CONFIG_FILE_KEYS
    if unknown:
        raise ValueError(f"unknown keys in {path}: {sorted(unknown)} "
                         f"(allowed: {sorted(_CONFIG_FILE_KEYS)})")
    return data


def load_city_config(env: Mapping[str, str] | None = None) -> CityConfig:
    """Resolve the active CityConfig: env vars > MATRIX_CITY_CONFIG file > Iloilo.

    Pure resolver (no caching) — tests pass an explicit ``env`` mapping; production
    callers go through ``get_city_config()``.
    """
    if env is None:
        env = os.environ

    name, slug = ILOILO.name, ILOILO.slug
    bbox = ILOILO.bbox
    net_path, rou_path = ILOILO.net_path, ILOILO.rou_path
    mode_share = dict(ILOILO.mode_share)
    baseline_key = persona_pool_key = ""  # "" -> derive from slug in __post_init__

    cfg_file = env.get("MATRIX_CITY_CONFIG")
    if cfg_file:
        path = Path(cfg_file)
        data = _read_config_file(path)
        if "name" in data:
            name = str(data["name"])
            slug = _slugify(name)
        if "slug" in data:
            slug = str(data["slug"])
        if "bbox" in data:
            bbox = _parse_bbox(data["bbox"])
        if "net_path" in data:
            net_path = _resolve_path(path.parent, data["net_path"])
        if "rou_path" in data:
            rou_path = _resolve_path(path.parent, data["rou_path"])
        if "mode_share" in data:
            mode_share = _parse_mode_share(data["mode_share"])
        baseline_key = str(data.get("baseline_key", ""))
        persona_pool_key = str(data.get("persona_pool_key", ""))

    if city := env.get("MATRIX_CITY"):
        name = city
        slug = _slugify(city)
    if env_slug := env.get("MATRIX_CITY_SLUG"):
        slug = env_slug
    if env_net := env.get("MATRIX_NET_PATH"):
        net_path = Path(env_net)
    if env_rou := env.get("MATRIX_ROU_PATH"):
        rou_path = Path(env_rou)
    if env_bbox := env.get("MATRIX_BBOX"):
        bbox = _parse_bbox(env_bbox)
    if env_share := env.get("MATRIX_MODE_SHARE"):
        mode_share = _parse_mode_share(env_share)

    return CityConfig(
        name=name,
        slug=slug,
        bbox=bbox,
        net_path=net_path,
        rou_path=rou_path,
        mode_share=mode_share,
        baseline_key=baseline_key,
        persona_pool_key=persona_pool_key,
    )


@lru_cache(maxsize=1)
def get_city_config() -> CityConfig:
    """The active city, resolved once from the process environment (cached).

    baseline.py and personas.py bind module constants from this at import time, so
    the whole kernel sees one consistent city per process.
    """
    return load_city_config()
