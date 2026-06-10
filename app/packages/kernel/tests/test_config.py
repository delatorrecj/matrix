"""Tests for the per-city config layer (config.py; MATRIX.md §6 "API-level scaling").

Stdlib-only — no SUMO/Redis needed, so this whole module runs in the bare
`python -m pytest` mode. The one test that imports baseline.py guards on `sumo`
(baseline imports sumo_env at module top, which needs eclipse-sumo).
"""
import json
from pathlib import Path

import pytest

from matrix_kernel.config import (
    ILOILO,
    ILOILO_MODE_SHARE,
    CityConfig,
    get_city_config,
    load_city_config,
)

# A plausible second city — values are test fixtures, not a calibrated anchor.
CEBU_SHARE = {"jeepney": 0.40, "private_car": 0.25, "motorcycle": 0.20,
              "walk": 0.10, "bicycle": 0.05}


# --- Default: Iloilo, byte-identical to the pre-config hardcoded constants ----------

def test_default_is_iloilo_with_exact_legacy_values():
    cfg = load_city_config(env={})
    assert cfg == ILOILO
    assert cfg.name == "Iloilo City"
    assert cfg.slug == "iloilo"
    assert cfg.bbox == (10.65, 122.50, 10.78, 122.61)
    assert cfg.net_path.name == "iloilo.net.xml"
    assert cfg.rou_path.name == "iloilo.rou.xml"
    assert cfg.baseline_key == "baseline:iloilo:latest"
    assert cfg.persona_pool_key == "personas:iloilo:v1"
    assert cfg.mode_share == {
        "jeepney": 0.55,
        "private_car": 0.15,
        "motorcycle": 0.15,
        "walk": 0.10,
        "bicycle": 0.05,
    }


def test_personas_constants_derive_from_config():
    from matrix_kernel.personas import ILOILO_MODE_SHARE as anchor
    from matrix_kernel.personas import PERSONA_POOL_KEY

    assert anchor == ILOILO_MODE_SHARE
    assert PERSONA_POOL_KEY == "personas:iloilo:v1"


def test_baseline_constants_derive_from_config():
    pytest.importorskip("sumo")  # baseline.py imports sumo_env at module top
    from matrix_kernel.baseline import BASELINE_KEY, NET, ROU

    assert BASELINE_KEY == "baseline:iloilo:latest"
    assert NET == ILOILO.net_path
    assert ROU == ILOILO.rou_path


# --- Env-var overrides ----------------------------------------------------------------

def test_env_overrides_all_fields():
    env = {
        "MATRIX_CITY": "Cebu City",
        "MATRIX_NET_PATH": "/data/cebu.net.xml",
        "MATRIX_ROU_PATH": "/data/cebu.rou.xml",
        "MATRIX_BBOX": "10.25,123.77,10.40,123.95",
        "MATRIX_MODE_SHARE": json.dumps(CEBU_SHARE),
    }
    cfg = load_city_config(env=env)
    assert cfg.name == "Cebu City"
    assert cfg.slug == "cebu-city"  # auto-derived from the name
    assert cfg.bbox == (10.25, 123.77, 10.40, 123.95)
    assert cfg.net_path == Path("/data/cebu.net.xml")
    assert cfg.rou_path == Path("/data/cebu.rou.xml")
    assert cfg.mode_share == CEBU_SHARE
    # Redis keys re-derive from the new slug (the historical key shapes).
    assert cfg.baseline_key == "baseline:cebu-city:latest"
    assert cfg.persona_pool_key == "personas:cebu-city:v1"


def test_explicit_slug_beats_derived_slug():
    cfg = load_city_config(env={"MATRIX_CITY": "Cebu City", "MATRIX_CITY_SLUG": "cebu"})
    assert cfg.name == "Cebu City"
    assert cfg.slug == "cebu"
    assert cfg.baseline_key == "baseline:cebu:latest"
    assert cfg.persona_pool_key == "personas:cebu:v1"


def test_partial_env_override_keeps_iloilo_for_the_rest():
    cfg = load_city_config(env={"MATRIX_BBOX": "1.0,2.0,3.0,4.0"})
    assert cfg.bbox == (1.0, 2.0, 3.0, 4.0)
    assert cfg.slug == "iloilo"
    assert cfg.mode_share == ILOILO.mode_share
    assert cfg.net_path == ILOILO.net_path


def test_bad_slug_raises():
    # The slug namespaces Redis keys — ":"/spaces/uppercase would corrupt them.
    for bad in ("Davao City", "davao:2026", "UPPER"):
        with pytest.raises(ValueError, match="slug"):
            load_city_config(env={"MATRIX_CITY_SLUG": bad})


def test_bad_bbox_raises():
    with pytest.raises(ValueError, match="4 numbers"):
        load_city_config(env={"MATRIX_BBOX": "10.65,122.50,10.78"})
    with pytest.raises(ValueError, match="numeric"):
        load_city_config(env={"MATRIX_BBOX": "a,b,c,d"})
    with pytest.raises(ValueError, match="lat_min<lat_max"):
        load_city_config(env={"MATRIX_BBOX": "10.78,122.50,10.65,122.61"})


def test_bad_mode_share_raises():
    with pytest.raises(ValueError, match="not valid JSON"):
        load_city_config(env={"MATRIX_MODE_SHARE": "{not json"})
    with pytest.raises(ValueError, match="sum to ~1.0"):
        load_city_config(env={"MATRIX_MODE_SHARE": '{"jeepney": 0.5}'})
    with pytest.raises(ValueError, match="non-empty"):
        load_city_config(env={"MATRIX_MODE_SHARE": "{}"})
    with pytest.raises(ValueError, match=">= 0"):
        load_city_config(env={"MATRIX_MODE_SHARE": '{"jeepney": 1.5, "walk": -0.5}'})


# --- Config-file loading (MATRIX_CITY_CONFIG) ------------------------------------------

def test_json_config_file(tmp_path):
    p = tmp_path / "davao.json"
    p.write_text(json.dumps({
        "name": "Davao City",
        "slug": "davao",
        "bbox": [6.95, 125.45, 7.25, 125.70],
        "net_path": "davao.net.xml",  # relative -> resolves against the file's dir
        "rou_path": str(tmp_path / "davao.rou.xml"),
        "mode_share": CEBU_SHARE,
    }), encoding="utf-8")
    cfg = load_city_config(env={"MATRIX_CITY_CONFIG": str(p)})
    assert cfg.name == "Davao City"
    assert cfg.slug == "davao"
    assert cfg.bbox == (6.95, 125.45, 7.25, 125.70)
    assert cfg.net_path == (tmp_path / "davao.net.xml").resolve()
    assert cfg.rou_path == tmp_path / "davao.rou.xml"
    assert cfg.mode_share == CEBU_SHARE
    assert cfg.baseline_key == "baseline:davao:latest"
    assert cfg.persona_pool_key == "personas:davao:v1"


def test_toml_config_file(tmp_path):
    p = tmp_path / "davao.toml"
    p.write_text(
        'name = "Davao City"\n'
        "bbox = [6.95, 125.45, 7.25, 125.70]\n"
        "mode_share = { jeepney = 0.5, private_car = 0.2, motorcycle = 0.2, walk = 0.1 }\n",
        encoding="utf-8",
    )
    cfg = load_city_config(env={"MATRIX_CITY_CONFIG": str(p)})
    assert cfg.name == "Davao City"
    assert cfg.slug == "davao-city"  # derived from name when the file omits slug
    assert cfg.baseline_key == "baseline:davao-city:latest"
    assert cfg.mode_share["jeepney"] == 0.5
    assert cfg.net_path == ILOILO.net_path  # unset keys keep Iloilo defaults


def test_json_config_file_with_bom(tmp_path):
    # Windows editors/PowerShell often prepend a UTF-8 BOM — must still parse.
    p = tmp_path / "bom.json"
    p.write_text(json.dumps({"slug": "davao"}), encoding="utf-8-sig")
    assert load_city_config(env={"MATRIX_CITY_CONFIG": str(p)}).slug == "davao"


def test_non_iterable_bbox_in_file_raises(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"bbox": 5}), encoding="utf-8")
    with pytest.raises(ValueError, match="bbox"):
        load_city_config(env={"MATRIX_CITY_CONFIG": str(p)})


def test_config_file_explicit_keys_override_derivation(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({
        "slug": "davao",
        "baseline_key": "baseline:davao:2026-06",
        "persona_pool_key": "personas:davao:v2",
    }), encoding="utf-8")
    cfg = load_city_config(env={"MATRIX_CITY_CONFIG": str(p)})
    assert cfg.baseline_key == "baseline:davao:2026-06"
    assert cfg.persona_pool_key == "personas:davao:v2"


def test_env_beats_config_file(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"name": "Davao City", "slug": "davao"}), encoding="utf-8")
    cfg = load_city_config(env={"MATRIX_CITY_CONFIG": str(p), "MATRIX_CITY_SLUG": "cebu"})
    assert cfg.name == "Davao City"  # file value survives where env is silent
    assert cfg.slug == "cebu"        # env wins where both speak
    assert cfg.baseline_key == "baseline:cebu:latest"


def test_missing_config_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_city_config(env={"MATRIX_CITY_CONFIG": str(tmp_path / "nope.json")})


def test_unknown_config_file_key_raises(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"slug": "davao", "bbx": [1, 2, 3, 4]}), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown keys"):
        load_city_config(env={"MATRIX_CITY_CONFIG": str(p)})


# --- get_city_config (cached process-env entry point) ----------------------------------

def test_get_city_config_reads_process_env(monkeypatch):
    monkeypatch.setenv("MATRIX_CITY_SLUG", "envtest")
    get_city_config.cache_clear()
    try:
        assert get_city_config().slug == "envtest"
        assert get_city_config().baseline_key == "baseline:envtest:latest"
    finally:
        monkeypatch.undo()
        get_city_config.cache_clear()  # don't leak the test city to other tests


def test_cityconfig_key_derivation_from_slug():
    cfg = CityConfig(name="X", slug="x", bbox=(0.0, 0.0, 1.0, 1.0),
                     net_path=Path("x.net.xml"), rou_path=Path("x.rou.xml"),
                     mode_share={"walk": 1.0})
    assert cfg.baseline_key == "baseline:x:latest"
    assert cfg.persona_pool_key == "personas:x:v1"
