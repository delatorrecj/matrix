"""Named-corridor spans: street-name match + graph clip (no SUMO import).

The live net already names streets. The LLM emits corridor + optional bounding
cross names; this module resolves those names to SUMO edge ids. Geometry
(lon/lat predicates) stays in ``geometry.py``.
"""
from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field


def normalize_street_name(raw: str) -> str:
    """Compare form: EL98 → el 98, St./St → street, collapsed lowercase."""
    s = (raw or "").strip()
    if not s:
        return ""
    s = re.sub(r"\b[Ee][Ll]\s*-?\s*98\b", "El 98", s)
    s = re.sub(r"\bSt\.?(?!\w)", "Street", s, flags=re.I)
    s = re.sub(r"[.,]+", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def _label(raw: str) -> str:
    """Display form: expand abbreviations, keep the caller's capitalization."""
    s = (raw or "").strip().strip(".,")
    if not s:
        return ""
    s = re.sub(r"\b[Ee][Ll]\s*-?\s*98\b", "El 98", s)
    s = re.sub(r"\bSt\.?(?!\w)", "Street", s, flags=re.I)
    s = re.sub(r"[.,]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


_FROM_TO = re.compile(
    r"^(?P<loc>.+?)"
    r"(?:,\s*)?"
    r"(?:(?:the\s+)?segment\s+)?"
    r"(?:starting\s+)?"
    r"from\s+(?P<frm>.+?)"
    r"\s+(?:up\s+to|to)\s+"
    r"(?P<to>.+)$",
    re.I,
)


def peel_span_fields(location: str, from_cross: str = "", to_cross: str = "") -> tuple[str, str, str]:
    """Corridor-only location + bounding crosses. Never invent crosses."""
    loc, frm, to = _label(location), _label(from_cross), _label(to_cross)
    if frm or to:
        return loc, frm, to
    m = _FROM_TO.match(loc)
    if not m:
        return loc, "", ""
    return _label(m.group("loc")), _label(m.group("frm")), _label(m.group("to"))


_GENERIC_TOKENS = frozenset({"street", "road", "avenue", "ave", "blvd", "drive", "lane"})


def _name_hits(query: str, street: str) -> bool:
    q = normalize_street_name(query)
    n = normalize_street_name(street)
    if not q or not n:
        return False
    if n == q:
        return True
    q_toks, n_toks = q.split(), n.split()
    if len(q_toks) == 1 and q_toks[0] in _GENERIC_TOKENS:
        return False
    k = len(q_toks)
    return any(n_toks[i : i + k] == q_toks for i in range(len(n_toks) - k + 1))


def keyword_edges(net, corridor: str) -> list[str]:
    """Edge ids whose SUMO name matches the corridor keyword. Honest miss → []."""
    key = normalize_street_name(corridor)
    if not key:
        return []
    return [
        e.getID()
        for e in net.getEdges()
        if _name_hits(key, e.getName() or "")
    ]


def extract_live_street(net, text: str) -> str:
    """Longest live ``edge.getName()`` that is a substring of ``text`` (normalized)."""
    hay = normalize_street_name(text)
    if not hay:
        return ""
    best = ""
    best_n = ""
    for e in net.getEdges():
        name = (e.getName() or "").strip()
        n = normalize_street_name(name)
        if not n or n not in hay:
            continue
        if " " not in n and n != hay:
            continue
        if len(n) > len(best_n):
            best = name
            best_n = n
    return best


def junction_nodes(net, cross_name: str) -> set[str]:
    """Nodes incident to at least one edge named like ``cross_name``."""
    if not normalize_street_name(cross_name):
        return set()
    nodes: set[str] = set()
    for e in net.getEdges():
        if _name_hits(cross_name, e.getName() or ""):
            nodes.add(e.getFromNode().getID())
            nodes.add(e.getToNode().getID())
    return nodes


@dataclass
class SpanClip:
    edges: list[str]
    method: str
    span_nodes: list[str] = field(default_factory=list)
    assumption: str = ""


def _undirected(corridor_edges) -> dict[str, dict[str, set[str]]]:
    adj: dict[str, dict[str, set[str]]] = {}
    for e in corridor_edges:
        a, b, eid = e.getFromNode().getID(), e.getToNode().getID(), e.getID()
        adj.setdefault(a, {}).setdefault(b, set()).add(eid)
        adj.setdefault(b, {}).setdefault(a, set()).add(eid)
    return adj


def _bfs_dist(adj: dict[str, dict[str, set[str]]], sources: set[str]) -> dict[str, int]:
    dist: dict[str, int] = {}
    q: deque[str] = deque()
    for s in sources:
        dist[s] = 0
        q.append(s)
    while q:
        u = q.popleft()
        for v in adj.get(u, {}):
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


def _edges_on_shortest_paths(
    adj: dict[str, dict[str, set[str]]],
    sources: set[str],
    targets: set[str],
) -> tuple[list[str], list[str]]:
    dist = _bfs_dist(adj, sources)
    reached = [t for t in targets if t in dist]
    if not reached:
        return [], []
    goal_d = min(dist[t] for t in reached)
    goals = {t for t in reached if dist[t] == goal_d}
    keep_edges: set[str] = set()
    on_path = set(goals)
    by_d: dict[int, list[str]] = {}
    for n, d in dist.items():
        by_d.setdefault(d, []).append(n)
    for d in range(goal_d, 0, -1):
        for v in by_d.get(d, []):
            if v not in on_path:
                continue
            for u, eids in adj.get(v, {}).items():
                if dist.get(u) == d - 1:
                    keep_edges.update(eids)
                    keep_edges.update(adj.get(u, {}).get(v, ()))
                    on_path.add(u)
    return list(keep_edges), list(on_path)


def _open_span(
    adj: dict[str, dict[str, set[str]]], seeds: set[str]
) -> tuple[list[str], list[str]]:
    dist = _bfs_dist(adj, seeds)
    if not dist:
        return [], []
    max_d = max(dist.values())
    if max_d == 0:
        return [], []
    far = {n for n, d in dist.items() if d == max_d}
    return _edges_on_shortest_paths(adj, seeds, far)


def clip_named_span(
    net,
    corridor_ids: list[str],
    from_cross: str = "",
    to_cross: str = "",
) -> SpanClip:
    """Clip a named-street edge set to the span between bounding crosses.

    Whole-street is the default when crosses are unset or miss the corridor.
    """
    idset = set(corridor_ids)
    corridor_edges = [e for e in net.getEdges() if e.getID() in idset]
    adj = _undirected(corridor_edges)
    corridor_nodes = set(adj)
    whole = SpanClip(list(corridor_ids), "keyword-match")

    from_x, to_x = (from_cross or "").strip(), (to_cross or "").strip()
    if not from_x and not to_x:
        return whole

    from_nodes = (junction_nodes(net, from_x) & corridor_nodes) if from_x else set()
    to_nodes = (junction_nodes(net, to_x) & corridor_nodes) if to_x else set()

    if from_x and to_x:
        if not from_nodes or not to_nodes:
            return SpanClip(list(corridor_ids), "keyword-match", [], "span_crosses_off_corridor")
        edges, nodes = _edges_on_shortest_paths(adj, from_nodes, to_nodes)
        if not edges:
            return SpanClip([], "miss", list(from_nodes | to_nodes), "")
        return SpanClip(sorted(edges), "keyword-span", sorted(nodes), "")

    seeds = from_nodes or to_nodes
    if not seeds:
        return SpanClip(list(corridor_ids), "keyword-match", [], "span_crosses_off_corridor")
    edges, nodes = _open_span(adj, seeds)
    if not edges:
        return SpanClip([], "miss", sorted(seeds), "")
    return SpanClip(sorted(edges), "keyword-span-open", sorted(nodes), "")
