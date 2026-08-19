"""Named-corridor spans (no SUMO wheel). Duck-typed net; real Cuartero / Fajardo / El 98 ids."""
from matrix_kernel.span import (
    clip_named_span,
    extract_live_street,
    keyword_edges,
    normalize_street_name,
    peel_span_fields,
)


class FakeNode:
    def __init__(self, nid: str):
        self._id = nid

    def getID(self) -> str:
        return self._id


class FakeEdge:
    def __init__(self, eid: str, name: str, frm: str, to: str, shape=None):
        self._id = eid
        self._name = name
        self._from = frm
        self._to = to
        self._shape = list(shape or [(0.0, 0.0), (1.0, 1.0)])

    def getID(self) -> str:
        return self._id

    def getName(self) -> str:
        return self._name

    def getFromNode(self) -> FakeNode:
        return FakeNode(self._from)

    def getToNode(self) -> FakeNode:
        return FakeNode(self._to)

    def getShape(self, includeJunctions=False):
        return list(self._shape)


class FakeNet:
    def __init__(self, edges):
        self._edges = list(edges)
        self._by_id = {e.getID(): e for e in self._edges}

    def getEdges(self):
        return list(self._edges)

    def getEdge(self, edge_id: str):
        return self._by_id[edge_id]

    def convertXY2LonLat(self, x, y):
        return x, y


# Live SUMO topology from deploy/hf-space/iloilo.net.xml (way 154184307).
_FAJARDO = "627794383"
_EL98 = "cluster_767324203_8221271607_8221271609"

CUARTERO = [
    ("154184307#0", "4756044955", "7669363172"),
    ("154184307#3", "7669363172", "1817710584"),
    ("154184307#4", "1817710584", "cluster_1243907087_1657579859"),
    ("154184307#6", "cluster_1243907087_1657579859", "953527245"),
    ("154184307#7", "953527245", "1135567551"),
    ("154184307#8", "1135567551", "1135568012"),
    ("154184307#9", "1135568012", _FAJARDO),
    ("154184307#10", _FAJARDO, "6431479651"),
    ("154184307#11", "6431479651", "6431475161"),
    ("154184307#12", "6431475161", "1243907176"),
    ("154184307#13", "1243907176", "13467997573"),
    ("154184307#14", "13467997573", _EL98),
    ("-154184307#2", "7669363172", "4756044955"),
    ("-154184307#3", "1817710584", "7669363172"),
    ("-154184307#4", "cluster_1243907087_1657579859", "1817710584"),
    ("-154184307#6", "953527245", "cluster_1243907087_1657579859"),
    ("-154184307#7", "1135567551", "953527245"),
    ("-154184307#8", "1135568012", "1135567551"),
    ("-154184307#9", _FAJARDO, "1135568012"),
    ("-154184307#10", "6431479651", _FAJARDO),
    ("-154184307#11", "6431475161", "6431479651"),
    ("-154184307#12", "1243907176", "6431475161"),
    ("-154184307#13", "13467997573", "1243907176"),
    ("-154184307#14", _EL98, "13467997573"),
]

SPAN_IDS = {
    "154184307#10",
    "154184307#11",
    "154184307#12",
    "154184307#13",
    "154184307#14",
    "-154184307#10",
    "-154184307#11",
    "-154184307#12",
    "-154184307#13",
    "-154184307#14",
}


def cuartero_net() -> FakeNet:
    edges = [
        FakeEdge(eid, "Cuartero Street", frm, to) for eid, frm, to in CUARTERO
    ]
    edges += [
        FakeEdge("152996971#2", "Fajardo Street", "1657579868", _FAJARDO),
        FakeEdge("-152996971#2", "Fajardo Street", _FAJARDO, "1657579868"),
        FakeEdge("921365604#0", "Fajardo Street", _FAJARDO, "5750751725"),
        FakeEdge("689794397#0", "El 98 Street", _EL98, "13467997558"),
        FakeEdge("884002266", "El 98 Street", "663951803", _EL98),
        FakeEdge("busy-1", "Lopez Jaena Street", "n1", "n2"),
    ]
    return FakeNet(edges)


def test_normalize_expands_st_and_el98():
    assert normalize_street_name("Fajardo St.") == "fajardo street"
    assert normalize_street_name("EL98 st.") == "el 98 street"
    assert normalize_street_name("EL 98") == "el 98"
    assert normalize_street_name("El98") == "el 98"
    assert normalize_street_name("Cuartero Street") == "cuartero street"


def test_peel_span_fields_splits_stuffed_location():
    loc, frm, to = peel_span_fields(
        "Cuartero Street, segment from Fajardo St. to EL98 st.", "", ""
    )
    assert loc == "Cuartero Street"
    assert frm == "Fajardo Street"
    assert to == "El 98 Street"


def test_peel_leaves_whole_street_when_no_crosses():
    loc, frm, to = peel_span_fields("Cuartero Street", "", "")
    assert loc == "Cuartero Street"
    assert frm == ""
    assert to == ""


def test_peel_does_not_invent_crosses_over_explicit_fields():
    loc, frm, to = peel_span_fields("Cuartero Street", "Fajardo Street", "El 98 Street")
    assert (loc, frm, to) == ("Cuartero Street", "Fajardo Street", "El 98 Street")


def test_keyword_edges_matches_canonical_name():
    net = cuartero_net()
    ids = keyword_edges(net, "Cuartero Street")
    assert set(ids) == {row[0] for row in CUARTERO}
    assert len(ids) == 24


def test_keyword_edges_stuffed_phrase_is_not_a_match():
    net = cuartero_net()
    assert keyword_edges(net, "Cuartero Street, segment from Fajardo St. to EL98 st.") == []


def test_extract_live_street_from_stuffed_phrase():
    net = cuartero_net()
    assert extract_live_street(net, "Cuartero Street, segment from Fajardo St. to EL98 st.") == (
        "Cuartero Street"
    )


def test_clip_fajardo_to_el98_is_segments_10_to_14_both_ways():
    net = cuartero_net()
    corridor = keyword_edges(net, "Cuartero Street")
    clip = clip_named_span(net, corridor, "Fajardo Street", "El 98 Street")
    assert clip.method == "keyword-span"
    assert set(clip.edges) == SPAN_IDS
    assert clip.assumption == ""
    assert _FAJARDO in clip.span_nodes
    assert _EL98 in clip.span_nodes


def test_clip_open_from_fajardo_is_span_open():
    net = cuartero_net()
    corridor = keyword_edges(net, "Cuartero Street")
    clip = clip_named_span(net, corridor, "Fajardo Street", "")
    assert clip.method == "keyword-span-open"
    assert set(clip.edges) < set(corridor)
    assert any(eid.endswith("#10") or eid.endswith("#9") for eid in clip.edges)


def test_clip_unknown_cross_keeps_whole_street():
    net = cuartero_net()
    corridor = keyword_edges(net, "Cuartero Street")
    clip = clip_named_span(net, corridor, "No Such Avenue", "Also Missing Rd")
    assert clip.method == "keyword-match"
    assert clip.assumption == "span_crosses_off_corridor"
    assert set(clip.edges) == set(corridor)
