# MATRIX — 90s Technology Demo Script

| Segment | Time | Duration | On-Screen Action | Voiceover |
|---------|------|----------|------------------|-----------|
| **1. Query Input** | 0:00–0:13 | 13s | Iloilo map loads, cursor types `Add RDT station on Diversion Road`, hits Run | I type a plain question: "Add RDT station on Diversion Road." Let's run it. |
| **2. NL Parsing** | 0:13–0:26 | 13s | WebSocket shows `ACCEPTED`, structured scenario JSON visible | Azure OpenAI GPT-5.4 turns that sentence into a real simulation plan. Location, intervention type, parameters. `It never makes up a number.` |
| **3. SUMO Simulation** | 0:26–0:40 | 14s | Deck.gl TripsLayer animates agent trails across Iloilo road network | This is Eclipse SUMO running live. One simulation kernel produces a single trajectory dataset that all five modules score against. Hundreds of commuter agents routing through the real road network right now. |
| **4. Results Stream In** | 0:40–0:54 | 14s | 5 dimension cards appear: Behavioral (High), Ecological (High), Social (Med), Economic (Med), Societal (Low-Med) | Results come in across all five dimensions. Behavioral and Ecological first, then Social, Economic, Societal. Every card shows a range and a confidence level. `Nothing is made up.` |
| **5. Glass-Box Inspect** | 0:54–1:08 | 14s | Click Behavioral card, Inspect drawer opens, pan across equation_id, dataset IDs, confidence | Click any result and the glass box opens. Equation ID, input datasets, computed confidence. Our ChromaDB knowledge base with bge-small embeddings keeps every answer grounded. |
| **6. Provenance** | 1:08–1:20 | 12s | Hold on Inspect drawer, cursor highlights each field  `Insert the AI-generated DFD` | The language model writes the summary but cannot invent a number. If a figure doesn't trace back to an equation and a dataset, it never appears on screen. |
| **7. End Card** | 1:20–1:30 | 10s | Map zooms out to ASEAN view, end card fades in | MATRIX. Five dimensions, one simulation. Decide before you build. |

## Production Notes

**Two AI technologies to name on camera:**
- Azure OpenAI GPT-5.4 (segment 2)
- ChromaDB with bge-small embeddings (segment 5)

**Voiceover:** Record separately. Read at 125 wpm with natural pauses.

**Recording checklist:**
- Pre-warm persona pool and trajectory cache
- Verify Inspect drawer resolves equation_id, dataset IDs, confidence
- OBS at 1080p60 with click highlighting
- Clean browser profile, no notifications
