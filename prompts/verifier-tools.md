# Tool Reference — VirtueCommand Verifier Agent

## 1. resolve_terms

**Purpose**: Map user's natural-language medical terms to canonical graph keys. Determines retrieval strategy (graph, raw_text, or mixed). This is the vocabulary gate.

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
- `"graph"` → use graph tools
- `"raw_text"` → skip graph, go to search_raw_text
- `"mixed"` → use both

---

## 2. detect_anomalies

**Purpose**: Flag facilities with suspicious data patterns for quality review.

**Parameters**:
- `check_type` (str, required): One of:
  - `"procedure_vs_size"` — many high-complexity procedures relative to bed capacity.
  - `"equipment_vs_claims"` — many capabilities but few equipment items.
  - `"feature_correlation"` — expected equipment missing for claimed capabilities.
  - `"bed_or_ratio"` — unusual bed-to-surgical-capability ratios.
- `region` (str, optional): Region filter.
- `threshold` (float, optional): Sensitivity (0-1, lower = more sensitive).
- `limit` (int, optional): Max flagged facilities (default 20).

**Returns**: Flagged facilities with anomaly scores and explanations.

**When to use**: For data quality questions: "Which facilities claim unrealistic procedures?", "Where do capabilities not match equipment?", "What correlations seem wrong?"

---

## 3. inspect_facility

**Purpose**: Deep dive into a single facility — all graph edges, raw text, and equipment gap analysis in one call.

**Parameters**:
- `facility_id` (str, required): The facility node ID (e.g. "facility::123").
- `include_raw_text` (bool, optional): Include raw text for cross-validation (default True).
- `include_gap_analysis` (bool, optional): Include LACKS edges and mismatch ratio (default True).

**Returns**: Complete facility profile with specialties, capabilities, equipment, lacks, could_support, mismatch_ratio, and raw text.

**When to use**: After detecting anomalies, inspect flagged facilities for detailed verification. For "What services does X offer?", verification, and facility-level gap analysis.

---

## 4. search_raw_text

**Purpose**: Free-text substring search across raw facility text fields. Escape hatch when the graph's vocabulary doesn't cover the query.

**Parameters**:
- `terms` (list[str], required): Search terms.
- `fields` (list[str] | None, optional): Fields to search. Default: all raw text fields.
- `region` (str | None, optional): Region filter.
- `limit` (int, optional): Max results (default 50).

**Returns**: List of matching facilities with matched text snippets per field.

**When to use**:
- For cross-validation of graph claims against raw source text
- For concepts not in the canonical vocabulary
- For workforce/staffing questions ("visiting specialists", "surgical camps")

---

## 5. get_requirements

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

**When to use**: For equipment compliance checks — "does this facility have what it needs for the capability it claims?"
