# Tool Reference — VirtueCommand Analyst Agent

## 1. resolve_terms

**Purpose**: Map user's natural-language medical terms to canonical graph keys. Determines retrieval strategy (graph, raw_text, or mixed). This is the Self-RAG vocabulary gate.

**Parameters**:
- `terms` (list[str], required): Medical terms extracted from the user's query.
- `show_all_vocabulary` (bool, optional): If True, include the full canonical vocabulary for relevant domains. Default False.
- `domain` (str | None, optional): Filter to "capabilities", "equipment", or "specialties". Default None (all).

**Returns**:
```json
{
  "mapped": [{"term": "cataract surgery", "key": "cataract_surgery", "confidence": 0.8, "domain": "capabilities"}],
  "unmapped": ["audiometry"],
  "coverage_ratio": 0.5,
  "strategy": "mixed"
}
```

**When to use**: ALWAYS call this first on every query containing medical terms. The `strategy` field tells you what to do next:
- `"graph"` → use graph tools (search_facilities, count_facilities, etc.)
- `"raw_text"` → skip graph, go to search_raw_text
- `"mixed"` → use both

**When NOT to use**: For purely geographic queries ("list all regions") or metadata queries ("how many facilities total?"). Use `explore_overview` directly.

---

## 2. find_facility

**Purpose**: Fuzzy-match a user-provided facility name to graph facility IDs. Essential bridge between natural language and graph node IDs.

**Parameters**:
- `name` (str, required): User-provided facility name (e.g. "Korle Bu", "Tamale Teaching").
- `region` (str | None, optional): Narrow search to a region.
- `limit` (int, optional): Max results (default 5).

**Returns**:
```json
{
  "query": "Korle Bu",
  "matches": [{"facility_id": "facility::123", "name": "Korle Bu Teaching Hospital", "region": "greater_accra", "city": "Accra", "facility_type": "Teaching Hospital", "match_score": 0.8}]
}
```

**When to use**: Whenever the user references a facility by name. Use the returned `facility_id` with `inspect_facility` or `get_requirements`.

---

## 3. search_facilities

**Purpose**: Universal multi-criteria facility search with optional geospatial radius. Finds facilities matching any combination of filters.

**Parameters** (all optional, but provide at least one filter):
- `capability` (str): Canonical capability key (e.g. "cataract_surgery").
- `equipment` (str): Canonical equipment key (e.g. "ultrasound").
- `specialty` (str): Canonical specialty key (e.g. "ophthalmology").
- `region` (str): Region key (e.g. "northern").
- `facility_type` (str): Facility type filter (substring match).
- `min_capacity` (int): Minimum bed/capacity count.
- `near_lat` (float): Latitude for geospatial search.
- `near_lng` (float): Longitude for geospatial search.
- `radius_km` (float): Max distance in km (requires near_lat/near_lng).
- `limit` (int): Max results (default 25).
- `sort_by` (str): "relevance" (default), "distance", or "capacity".

**Returns**:
```json
{
  "total_matches": 12,
  "facilities": [{"facility_id": "facility::42", "name": "...", "region": "northern", "city": "Tamale", "facility_type": "Hospital", "capacity": 200, "distance_km": 15.3, "matched_criteria": ["capability=cesarean_section", "region=northern"], "confidence": 0.85}]
}
```

**When to use**: For "which facilities have X?", "hospitals near Y that do Z", or any multi-filter search.

---

## 4. count_facilities

**Purpose**: Count facilities grouped by a dimension. Returns distributions with counts and percentages. Essential for "how many" questions.

**Parameters**:
- `group_by` (str, required): One of: "region", "specialty", "capability", "facility_type", "equipment".
- `capability` (str, optional): Filter to facilities with this capability.
- `equipment` (str, optional): Filter to facilities with this equipment.
- `specialty` (str, optional): Filter to facilities with this specialty.
- `region` (str, optional): Filter to this region.
- `min_confidence` (float, optional): Minimum edge confidence (default 0.5).

**Returns**:
```json
{
  "total_matching": 742,
  "group_by": "region",
  "groups": [{"key": "greater_accra", "display_name": "Greater Accra", "count": 180, "percentage": 24.3}]
}
```

**When to use**: For counting questions: "How many hospitals have cardiology?", "Which region has the most surgical facilities?", "Distribution of equipment across regions".

---

## 5. search_raw_text

**Purpose**: Free-text substring search across raw facility text fields. Escape hatch when the graph's vocabulary doesn't cover the query.

**Parameters**:
- `terms` (list[str], required): Search terms.
- `fields` (list[str] | None, optional): Fields to search. Default: all raw text fields.
- `region` (str | None, optional): Region filter.
- `limit` (int, optional): Max results (default 50).

**Returns**: List of matching facilities with matched text snippets per field.

**When to use**:
- When `resolve_terms` returns `strategy: "raw_text"` or `"mixed"`
- For concepts not in the canonical vocabulary
- For cross-validation of graph claims
- For workforce/staffing questions ("visiting specialists", "surgical camps")

---

## 6. inspect_facility

**Purpose**: Deep dive into a single facility — all graph edges, raw text, and equipment gap analysis in one call.

**Parameters**:
- `facility_id` (str, required): The facility node ID (e.g. "facility::123").
- `include_raw_text` (bool, optional): Include raw text for cross-validation (default True).
- `include_gap_analysis` (bool, optional): Include LACKS edges and mismatch ratio (default True).

**Returns**: Complete facility profile with specialties, capabilities, equipment, lacks, could_support, mismatch_ratio, and raw text.

**When to use**: After `find_facility` resolves a name to an ID. For "What services does X offer?", verification, and facility-level gap analysis.

---

## 7. get_requirements

**Purpose**: Look up required/recommended equipment for a capability, optionally comparing against a specific facility.

**Parameters**:
- `capability` (str, required): Canonical capability key.
- `facility_id` (str | None, optional): Facility ID for comparison.

**Returns**:
```json
{
  "capability": "cataract_surgery",
  "required": ["operating_theatre", "operating_microscope", "autoclave", "anesthesia_machine"],
  "recommended": ["phacoemulsification_machine", "a_scan_biometry"],
  "facility_comparison": {"facility_id": "facility::42", "has_required": ["operating_theatre"], "missing_required": ["operating_microscope", "autoclave", "anesthesia_machine"], "compliance_score": 0.25}
}
```

**When to use**: For gap analysis, mission planning ("what equipment would we need to bring?"), and verification ("does this facility have what it needs?").

---

## 8. find_gaps

**Purpose**: Discover what is MISSING — the graph's unique value over raw text.

**Parameters**:
- `gap_type` (str, required): One of:
  - `"deserts"` — regions lacking a specialty (requires `specialty`).
  - `"could_support"` — facilities ready for capability upgrade (requires `capability`).
  - `"ngo_gaps"` — regions with high need but no NGO presence.
  - `"equipment_compliance"` — % of facilities with required equipment for a capability.
- `specialty` (str, optional): Required for "deserts".
- `capability` (str, optional): Required for "could_support", optional for "equipment_compliance".
- `region` (str, optional): Region filter for "equipment_compliance".
- `min_readiness` (float, optional): Minimum readiness for "could_support" (default 0.6).

**When to use**: For gap analysis, mission planning, and "what's missing?" questions. ALWAYS use this for absence-related queries — `search_raw_text` cannot answer what's missing.

---

## 9. find_cold_spots

**Purpose**: Geographic coverage analysis — identify regions where a capability/specialty is absent within a given radius.

**Parameters**:
- `capability` (str | None): Canonical capability key. Provide either this or specialty.
- `specialty` (str | None): Canonical specialty key. Provide either this or capability.
- `radius_km` (float, optional): Maximum acceptable distance (default 100 km).
- `population_weighted` (bool, optional): Sort by population-weighted severity (default True).

**Returns**: Cold spots with severity scores plus coverage summary (regions/population covered vs uncovered).

**When to use**: For "where are the largest gaps in coverage for X within Y km?", geographic equity analysis.

---

## 10. explore_overview

**Purpose**: High-level landscape exploration — national overview, region deep-dive, or specialty breakdown.

**Parameters**:
- `scope` (str, required): One of:
  - `"national"` — graph stats, all regions with population/facility/desert counts, top specialties. No key needed.
  - `"region"` — deep-dive: facilities, specialty counts, deserts, NGOs, neighbours. Requires key.
  - `"specialty"` — capabilities, facility count. Requires key.
- `key` (str | None): Required for "region" (e.g. "northern") and "specialty" (e.g. "ophthalmology") scopes.

**When to use**: For orientation queries: "Tell me about region X", "What's the national landscape?", "What capabilities does ophthalmology encompass?"
