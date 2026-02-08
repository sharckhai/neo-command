# Tool Reference — VirtueCommand Self-RAG Agent

## query_graph

**Purpose**: Structured retrieval from the knowledge graph. Dispatches to one of 12 query functions.

**Parameters**:
- `query_type` (str, required): One of the query types below
- `params` (str, required): JSON-encoded dict of parameters for the chosen query

**Query types and their params**:

| query_type | params | returns |
|---|---|---|
| `facility_details` | `{"fid": "facility::123"}` | Full facility dump with all edges |
| `facility_mismatches` | `{"fid": "facility::123"}` | LACKS edges + mismatch_ratio |
| `suspicious_facilities` | `{"min_ratio": 0.3}` | Facilities with high mismatch ratios |
| `deserts_for_specialty` | `{"specialty_key": "ophthalmology"}` | Regions with no coverage |
| `could_support` | `{"capability_key": "cataract_surgery"}` | Upgrade-ready facilities |
| `regional_comparison` | `{"specialty_key": "ophthalmology"}` | All regions ranked |
| `facilities_by_capability` | `{"capability_key": "cataract_surgery", "region": "northern"}` | Facility search (region optional) |
| `facilities_by_equipment` | `{"equipment_key": "ultrasound", "region": "northern"}` | Equipment search (region optional) |
| `specialty_distribution` | `{}` | Counts per specialty per region |
| `nearest_facilities` | `{"lat": 5.6, "lng": -0.19, "capability_key": "...", "specialty_key": "...", "limit": 10}` | Geospatial search (filters optional) |
| `list_specialties` | `{}` | All specialties with facility counts |
| `graph_summary` | `{}` | Node/edge count stats |

**When to use**: For any query about capabilities, equipment, specialties, or facilities that uses terms from the graph's canonical vocabulary (35 capabilities, 48 equipment types).

**When NOT to use**: For terms that failed `check_vocabulary_coverage` (coverage_ratio < 0.3). Use `search_raw_text` instead.

---

## list_vocabulary

**Purpose**: Show the graph's canonical vocabulary so the agent (or user) knows what the graph can express.

**Parameters**:
- `domain` (str, required): Either `"capabilities"` or `"equipment"`

**Returns**: List of dicts with `key`, `display`, `category`, and `aliases` for each canonical term.

**When to use**: When you need to understand what terms the graph recognizes, help reformulate a query, or explain a vocabulary gap to the user.

**When NOT to use**: On every query. Only call when debugging or educating.

---

## check_vocabulary_coverage

**Purpose**: Detect whether query terms fall within the graph's vocabulary boundary. This is the critical first step in the Self-RAG reflection loop.

**Parameters**:
- `terms` (list[str], required): Medical terms extracted from the user's query

**Returns**:
```json
{
  "mapped": [{"term": "cataract surgery", "key": "cataract_surgery", "confidence": 0.8, "domain": "capabilities"}],
  "unmapped": ["audiometry", "hearing test"],
  "coverage_ratio": 0.33
}
```

**When to use**: ALWAYS call this first on every query containing medical terms. The `coverage_ratio` determines your retrieval strategy.

**When NOT to use**: For purely geographic queries ("list all regions") or metadata queries ("how many facilities total?").

---

## search_raw_text

**Purpose**: Escape hatch for queries that fall outside the graph's vocabulary. Searches across raw facility text fields using case-insensitive substring matching.

**Parameters**:
- `terms` (list[str], required): Search terms
- `fields` (list[str] | None, optional): Which fields to search. Defaults to all: `["raw_procedures", "raw_capabilities", "raw_equipment", "description"]`
- `region` (str | None, optional): Filter by region key (e.g., `"northern"`)

**Returns**: List of matching facilities with the matched snippets per field.

**When to use**:
- When `check_vocabulary_coverage` returns `coverage_ratio < 0.3`
- When you need to verify graph claims against raw text
- When searching for concepts not in the canonical vocabulary

**When NOT to use**: As the first choice for queries the graph CAN answer. The graph provides structured, confidence-scored results; raw text search is a fallback.

---

## get_facility_raw_text

**Purpose**: Read all raw text fields for a specific facility. Used for cross-validation after graph queries.

**Parameters**:
- `facility_id` (str, required): The facility node ID (e.g., `"facility::123"`)

**Returns**: Dict with `facility_id`, `name`, `region`, `raw_procedures`, `raw_capabilities`, `raw_equipment`, `description`.

**When to use**:
- After `query_graph` returns facility results, to verify specific claims
- When checking for referral patterns, visiting specialists, or other caveats
- When a facility's graph data seems suspicious (high mismatch ratio, unexpected capabilities)

**When NOT to use**: For bulk searching — use `search_raw_text` for that.

---

## query_absence

**Purpose**: Query the graph's absence-encoding edges (LACKS, DESERT_FOR, COULD_SUPPORT). This is information that raw text search CANNOT provide — the graph infers what's missing.

**Parameters**:
- `query_type` (str, required): One of `"facility_lacks"`, `"region_deserts"`, `"could_support"`
- `target` (str, required): The target identifier:
  - For `facility_lacks`: facility ID (e.g., `"facility::123"`)
  - For `region_deserts`: specialty key (e.g., `"ophthalmology"`)
  - For `could_support`: capability key (e.g., `"cataract_surgery"`)

**Returns**:
- `facility_lacks`: Missing equipment, claimed capabilities, mismatch ratio
- `region_deserts`: Regions with no coverage, sorted by severity
- `could_support`: Facilities ranked by readiness score with missing equipment lists

**When to use**: For gap analysis, mission planning, and "what's missing?" questions. This is the graph's unique value — no other tool can answer these questions.

**When NOT to use**: For "what exists?" questions — use `query_graph` for that.

---

## explore_regions

**Purpose**: List all 16 regions of Ghana with population, facility count, and desert count. Entry point for understanding the healthcare landscape.

**Parameters**: None.

**Returns**: List of dicts sorted by population descending:
```json
[{"region_key": "greater_accra", "display_name": "Greater Accra", "population": 5455692, "facility_count": 180, "desert_count": 2}, ...]
```

**When to use**: As a first step in desert analysis, mission planning, or any query that needs a national overview. Also useful when the user asks "which regions..." or "compare regions."

**When NOT to use**: When you already know the specific region to investigate — use `explore_region` directly.

---

## explore_region

**Purpose**: Deep-dive into a specific region showing facilities, specialty distribution, deserts, NGOs, and neighbouring regions.

**Parameters**:
- `region_key` (str, required): Canonical region key. One of: `greater_accra`, `ashanti`, `western`, `western_north`, `central`, `eastern`, `volta`, `oti`, `northern`, `savannah`, `north_east`, `upper_east`, `upper_west`, `bono`, `bono_east`, `ahafo`.

**Returns**: Dict with region metadata, facility list, specialty counts, desert list, NGO list, and neighbour keys.

**When to use**: For "tell me about region X" queries, or as part of mission planning to understand regional context (existing facilities, NGO presence, accessibility via neighbours).

**When NOT to use**: When you only need a facility list — use `explore_facilities` instead. When you only need desert info — use `query_absence(region_deserts, ...)`.

---

## explore_facilities

**Purpose**: List facilities in a region with optional specialty filtering. More flexible than `facilities_by_capability` for browsing.

**Parameters**:
- `region_key` (str, required): Canonical region key (e.g. `"northern"`).
- `specialty_key` (str | None, optional): Filter by specialty (e.g. `"ophthalmology"`).
- `limit` (int, optional): Max results (default 50).

**Returns**: List of facility dicts with capabilities, sorted by capability count descending.

**When to use**: When browsing what's available in a region, especially when filtering by specialty rather than specific capability. Good for "what facilities are in Northern Region?" or "ophthalmology facilities in Ashanti?"

**When NOT to use**: For capability-specific searches — use `query_graph(facilities_by_capability, ...)`. For equipment searches — use `query_graph(facilities_by_equipment, ...)`.

---

## get_equipment_requirements

**Purpose**: Look up required and recommended equipment for a medical capability. Essential for gap analysis.

**Parameters**:
- `capability_key` (str, required): Canonical capability key (e.g. `"cataract_surgery"`, `"cesarean_section"`, `"dialysis"`).

**Returns**:
```json
{"capability": "cataract_surgery", "required": ["operating_theatre", "operating_microscope", "autoclave", "anesthesia_machine"], "recommended": ["phacoemulsification_machine", "a_scan_biometry", "slit_lamp", "keratometer"]}
```

**When to use**: After finding a facility's equipment (via `facility_details`) to determine what's missing. Key for mission planning ("what would we need to bring?") and verification ("does this facility really have everything needed?").

**When NOT to use**: To find what equipment a facility HAS — use `query_graph(facility_details, ...)` for that. This tool shows what's NEEDED, not what's present.

---

## get_specialty_overview

**Purpose**: Bridge between specialties and capabilities. Shows which capabilities facilities of a given specialty actually have, with counts and percentages.

**Parameters**:
- `specialty_key` (str, required): Canonical specialty key (e.g. `"ophthalmology"`, `"gynecologyAndObstetrics"`, `"surgery"`, `"dentistry"`).

**Returns**:
```json
{"specialty": "ophthalmology", "facility_count": 45, "capabilities": [{"capability": "eye_examination", "count": 30, "percentage": 66.7}, {"capability": "cataract_surgery", "count": 12, "percentage": 26.7}]}
```

**When to use**: To understand what a specialty actually means in terms of capabilities. Useful before desert analysis (to know which capabilities to check) and for "what do ophthalmology facilities typically offer?" questions.

**When NOT to use**: To find facilities with a specific capability — use `query_graph(facilities_by_capability, ...)` instead.
