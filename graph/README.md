# graph/ — Knowledge Graph Pipeline

Builds a pre-computed knowledge graph from FDR (Foundational Data Refresh) CSV data so agents can do multi-hop reasoning and detect gaps in healthcare coverage.

**Input:** Any FDR CSV file (987 rows / 797 unique entities for Ghana)
**Output:** A NetworkX `MultiDiGraph` with 6 node types and 8 edge types

---

## Files

### `schema.py`
Constants and ID helpers for the graph schema.

- **6 node types:** Region, Facility, NGO, Capability, Equipment, Specialty
- **8 edge types:** LOCATED_IN, HAS_CAPABILITY, HAS_EQUIPMENT, HAS_SPECIALTY, LACKS, COULD_SUPPORT, DESERT_FOR, OPERATES_IN
- ID constructor functions (e.g. `facility_id("42")` → `"facility::42"`)
- Category/complexity enums for capabilities and equipment

### `config/ghana.py`
Ghana-specific data that makes the pipeline work for this country. Swap this file to support a different country.

- **REGION_NORMALIZATION** — Maps 54 raw `address_stateOrRegion` variants to 16 official regions
- **CITY_TO_REGION** — Fallback mapping for rows where region is null but city is known
- **REGION_METADATA** — Population (2021 census), capital city, lat/lng centroid per region
- **REGION_ADJACENCY** — Which regions border each other (used by BFS in desert detection)
- **CITY_GEOCODING** — Approximate lat/lng for common cities

### `normalize.py`
Converts messy free-text equipment and capability strings into canonical graph node IDs.

- **48 canonical equipment entries** (e.g. "Ultra-modern operating theatre" → `operating_theatre`)
- **35 canonical capability entries** (e.g. "Performs cataract surgeries including micro-incision" → `cataract_surgery`)
- **Pass 1 (regex/keyword):** Matches against alias lists using word-boundary regexes, longest-first
- **Pass 2 (LLM batch):** Sends unmatched items to GPT-4o-mini in batches of 20 for classification. Results cached to `data/normalization_cache.json` so the LLM is only called once

### `medical_requirements.py`
Static dictionary mapping each capability to required and recommended equipment.

- 35 capabilities mapped (e.g. `cataract_surgery` requires operating theatre, operating microscope, autoclave, anesthesia machine)
- **No LLM at runtime** — deterministic, auditable, sub-millisecond lookup
- Used by `inference.py` to compute LACKS and COULD_SUPPORT edges

### `build_graph.py`
Main orchestrator that runs the full pipeline: CSV → NetworkX graph.

1. **Load & clean CSV** — Parses JSON-encoded list columns, cleans nulls, parses numeric fields
2. **Normalize regions** — Uses country config to map raw region strings to canonical keys
3. **Deduplicate** — Merges rows with the same `pk_unique_id` (union of lists, richest scalar wins)
4. **Construct base graph** — Creates Region, Facility, NGO, Equipment, Capability, Specialty nodes and HAS_* edges
5. **Run inference** — Calls `inference.py` for LACKS/COULD_SUPPORT edges
6. **Run desert detection** — Calls `desert.py` for DESERT_FOR edges

CLI: `python -m graph.build_graph data/some_fdr.csv --country ghana`

### `inference.py`
Computes two inferred edge types from the base graph.

- **LACKS:** For each facility, compares claimed capabilities against confirmed equipment. Missing required equipment gets a LACKS edge with `evidence_status="no_evidence"` (absence from web scrape ≠ confirmed absence)
- **COULD_SUPPORT:** Inverse — finds capabilities a facility doesn't claim but has ≥60% of required equipment for. Attaches a `readiness_score` and list of missing items

### `desert.py`
Identifies "medical deserts" — regions lacking facilities for a given specialty.

- For each (region, specialty) pair: counts facilities with `HAS_SPECIALTY` where confidence ≥ 0.5
- If count < 1: creates a `DESERT_FOR` edge with `severity = population / (count + 1)`
- Uses BFS on the region adjacency graph to find the nearest region that does have the specialty

### `queries.py`
Runtime query functions that agents call. Designed for three interaction modes:

| Mode | Function | What it does |
|------|----------|-------------|
| **VERIFY** | `get_facility_mismatches(G, fid)` | All LACKS edges + context for one facility |
| **VERIFY** | `find_suspicious_facilities(G)` | Batch scan for high mismatch-ratio facilities |
| **PLAN** | `get_deserts_for_specialty(G, spec)` | Regions with DESERT_FOR, sorted by severity |
| **PLAN** | `get_facilities_that_could_support(G, cap)` | COULD_SUPPORT targets, sorted by readiness |
| **PLAN** | `get_regional_comparison(G, spec)` | All 16 regions ranked by facility count |
| **EXPLORE** | `search_facilities_by_capability(G, cap)` | Facilities with a capability, filterable by region |
| **EXPLORE** | `search_facilities_by_equipment(G, equip)` | Facilities with equipment, filterable by region |
| **EXPLORE** | `get_specialty_distribution(G)` | Counts per specialty per region |
| — | `get_facility_details(G, fid)` | Full detail dump for a single facility |
| — | `get_graph_summary(G)` | Node/edge count summary |

### `export.py`
Saves and loads the graph in multiple formats.

- **`knowledge_graph.gpickle`** — Pickle for fast runtime loading
- **`knowledge_graph.graphml`** — GraphML for visualization in Gephi or similar tools
- **`knowledge_graph_meta.json`** — Node/edge counts and build timestamp

---

## Graph Stats (Ghana dataset)

| Metric | Count |
|--------|-------|
| Nodes | 1,014 |
| Edges | 6,223 |
| Facilities | 742 |
| NGOs | 55 |
| Regions | 16 |
| Specialties | 118 |
| Equipment types | 48 |
| Capability types | 35 |
