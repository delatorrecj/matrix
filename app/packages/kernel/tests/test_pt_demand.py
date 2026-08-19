"""Independent OSM-PT / LPTRP headways — not fitted to Calderon VAL-01 maxima."""
from inspect import signature

from matrix_kernel.pt_demand import (
    corridor_transit_veh_h,
    interval_to_veh_per_hour,
    lptrp_corridor_veh_h,
    lptrp_val01_veh_h,
    parse_lptrp_page,
)


def test_interval_hhmm_and_minutes():
    assert interval_to_veh_per_hour("02:00") == 0.5  # Ceres-style 2 h
    assert interval_to_veh_per_hour("00:10") == 6.0
    assert interval_to_veh_per_hour("10") == 6.0  # 10 minutes
    assert interval_to_veh_per_hour("") is None
    assert interval_to_veh_per_hour("n/a") is None


def test_urban_corridor_without_interval_is_zero():
    # Live Iloilo OSM: jeepney relations exist; interval is almost never tagged.
    # Matching Lopez Jaena without a headway must not invent f=22 veh/h (Calderon).
    elements = [
        {
            "type": "relation",
            "tags": {
                "route": "bus",
                "name": "Jeepney via Lopez Jaena Street",
                "from": "Jaro",
                "to": "City Proper",
            },
        }
    ]
    assert corridor_transit_veh_h(elements, ["Lopez Jaena"]) == 0.0


def test_tagged_intercity_interval_counts_without_calderon_targets():
    elements = [
        {
            "type": "relation",
            "tags": {
                "route": "bus",
                "name": "Ceres Liner: Roxas City -> Iloilo City",
                "interval": "02:00",
                "ref": "P-ICRC",
            },
        }
    ]
    assert corridor_transit_veh_h(elements, ["Iloilo City"]) == 0.5


def test_api_has_no_calderon_fit_knob():
    # Circularity guard: this helper must not take passenger_flow_max / 90 / 275.
    params = signature(corridor_transit_veh_h).parameters
    assert "passenger_flow_max" not in params
    assert "target_pax" not in params
    assert "calderon" not in {name.casefold() for name in params}


# Real LPTRP excerpts (ilonggoengineer.com/iloiloroutes-03 and -04, fetched 2026-08-20).
# Street tables only — no published headway.
_LPTRP_03 = """
03 Ungka to Iloilo City Proper via CPU
Jaro Diversion Road Christ the King Memorial Park
Lopez Jaena Street Carmelite Monastery Central Philippine University
Rizal Street (Jaro Plaza) Jaro Cathedral
Fort San Pedro Drive Fort San Pedro
"""

_LPTRP_04 = """
04 Ungka to Iloilo City Proper via Aquino Avenue / Festive Walk
Jaro Diversion Road University of San Agustin – Sambag Campus
Mandurriao Diversion Road SM City Iloilo
City Proper Infante Street University of the Philippines Visayas
"""


def test_lptrp_parses_val01_streets_without_inventing_headway():
    r3 = parse_lptrp_page(_LPTRP_03, title="Ungka via CPU")
    r4 = parse_lptrp_page(_LPTRP_04, title="Ungka via Aquino")
    streets3 = " ".join(r3.streets).casefold()
    streets4 = " ".join(r4.streets).casefold()
    assert "lopez jaena" in streets3
    assert "diversion" in streets3
    assert "diversion" in streets4
    assert r3.interval is None
    assert r4.interval is None
    assert lptrp_corridor_veh_h([r3], ["Lopez Jaena"]) == 0.0
    assert lptrp_corridor_veh_h([r4], ["Diversion", "Aquino"]) == 0.0


def test_lptrp_headway_only_when_page_states_it():
    tagged = _LPTRP_03 + "\nHeadway: 10 minutes\n"
    r = parse_lptrp_page(tagged, title="Ungka via CPU")
    assert r.interval == "10"
    assert lptrp_corridor_veh_h([r], ["Lopez Jaena"]) == 6.0


def test_lptrp_fleet_count_is_not_a_headway():
    # PNA citywide fleet (520 modern / 1,692 traditional) is not a corridor frequency.
    text = _LPTRP_04 + "\nA total of 520 modernized jeepneys and 1,692 consolidated traditional jeepneys.\n"
    r = parse_lptrp_page(text, title="Ungka via Aquino")
    assert r.interval is None
    assert lptrp_corridor_veh_h([r], ["Diversion"]) == 0.0


def test_lptrp_api_has_no_calderon_fit_knob():
    params = signature(lptrp_corridor_veh_h).parameters
    assert "passenger_flow_max" not in params
    assert "target_pax" not in params
    assert "calderon" not in {name.casefold() for name in params}


def test_lptrp_val01_corridors_stay_zero_without_published_headway():
    routes = [
        parse_lptrp_page(_LPTRP_03, title="Ungka via CPU"),
        parse_lptrp_page(_LPTRP_04, title="Ungka via Aquino"),
    ]
    out = lptrp_val01_veh_h(routes)
    assert set(out) == {"lopez_jaena", "diversion"}
    assert out["lopez_jaena"] == 0.0
    assert out["diversion"] == 0.0
    # Presence of Calderon maxima in the call would be circularity — they are not inputs.
    assert signature(lptrp_val01_veh_h).parameters.keys() == {"routes"}
