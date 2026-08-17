# 04 — Named places hit real network edges

**What to build:** Colloquial and canonical Iloilo place names used in the demo resolve to verified SUMO edges (and OSM ids where the gazetteer carries them). If the name does not resolve, the product says so. It must not silently hash the string onto a busy baseline edge and present that as the user’s location.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Gazetteer entries for the demo corridors are verified against the deployed net (not placeholder ids flagged provisional-as-truth).
- [ ] Edge-resolution method is visible on the run (playback/edge-counts / Inspect): geometry, gazetteer, street name, or unresolved — never a silent busiest-edge stand-in sold as a hit.
- [ ] Unresolved locations do not produce a misleading map marker on a hashed corridor; the planner gets an explicit resolve failure or confirm-to-retry.
- [ ] A reviewer can demo: “Lopez Jaena” / Diversion hits the named edges; a nonsense barangay does not look like a real closure there.
