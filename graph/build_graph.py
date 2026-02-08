"""Main orchestrator: CSV → NetworkX knowledge graph.

Pipeline steps:
  1. Load & clean CSV, parse JSON columns, normalize regions
  2. Deduplicate by pk_unique_id (merge multi-source rows)
  3. Normalize free-text fields to canonical nodes
  4. Construct base graph (Region, Facility, NGO nodes + HAS_* edges)
  5. Run inference (LACKS, COULD_SUPPORT) — see inference.py
  6. Run desert detection (DESERT_FOR) — see desert.py
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

import networkx as nx

from graph.schema import (
    NODE_REGION, NODE_FACILITY, NODE_NGO,
    NODE_CAPABILITY, NODE_EQUIPMENT, NODE_SPECIALTY,
    EDGE_LOCATED_IN, EDGE_HAS_CAPABILITY, EDGE_HAS_EQUIPMENT,
    EDGE_HAS_SPECIALTY, EDGE_OPERATES_IN,
    region_id, facility_id, ngo_id,
    capability_id, equipment_id, specialty_id,
)
from graph.normalize import (
    CANONICAL_EQUIPMENT, CANONICAL_CAPABILITIES,
    normalize_equipment_list, normalize_capability_list,
)
from graph.inference import add_lacks_edges, add_could_support_edges
from graph.desert import add_desert_edges

logger = logging.getLogger(__name__)

# JSON-encoded list columns in the CSV
JSON_LIST_COLUMNS = [
    "specialties", "procedure", "equipment", "capability",
    "phone_numbers", "websites", "affiliationTypeIds", "countries",
]


# ---------------------------------------------------------------------------
# Step 1: Load & Clean CSV
# ---------------------------------------------------------------------------

def _parse_json_list(value: str) -> list[str]:
    """Parse a JSON-encoded list column, handling nulls and edge cases."""
    if not value or value in ("null", "[]", ""):
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if item and str(item).strip()]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_int(value: str) -> int | None:
    if not value or value in ("null", ""):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _parse_float(value: str) -> float | None:
    if not value or value in ("null", ""):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def load_csv(csv_path: str | Path) -> list[dict[str, Any]]:
    """Load CSV and parse JSON columns. Returns list of cleaned row dicts."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse JSON list columns
            for col in JSON_LIST_COLUMNS:
                row[col] = _parse_json_list(row.get(col, ""))

            # Clean string columns
            for key in row:
                if key not in JSON_LIST_COLUMNS and isinstance(row[key], str):
                    if row[key] in ("null", ""):
                        row[key] = None

            # Parse numeric columns
            row["capacity"] = _parse_int(row.get("capacity", ""))
            row["numberDoctors"] = _parse_int(row.get("numberDoctors", ""))
            row["area"] = _parse_float(row.get("area", ""))
            row["yearEstablished"] = _parse_int(row.get("yearEstablished", ""))

            rows.append(row)

    logger.info("Loaded %d rows from %s", len(rows), csv_path)
    return rows


# ---------------------------------------------------------------------------
# Step 1b: Normalize regions using country config
# ---------------------------------------------------------------------------

def normalize_regions(rows: list[dict], country_config: Any) -> list[dict]:
    """Normalize address_stateOrRegion using country config mappings."""
    region_map = country_config.REGION_NORMALIZATION
    city_map = country_config.CITY_TO_REGION

    for row in rows:
        raw_region = row.get("address_stateOrRegion")
        raw_city = row.get("address_city")

        # Try region normalization
        normalized = None
        if raw_region:
            normalized = region_map.get(raw_region.lower().strip())

        # Fall back to city → region mapping
        if not normalized and raw_city:
            normalized = city_map.get(raw_city.lower().strip())

        row["_normalized_region"] = normalized

    return rows


# ---------------------------------------------------------------------------
# Step 2: Deduplicate by pk_unique_id
# ---------------------------------------------------------------------------

def _merge_list_fields(existing: list, new: list) -> list:
    """Union two lists, preserving order of first appearance."""
    seen = set()
    merged = []
    for item in existing + new:
        key = item.lower() if isinstance(item, str) else item
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return merged


def deduplicate_rows(rows: list[dict]) -> list[dict]:
    """Deduplicate rows by pk_unique_id, merging multi-source rows."""
    by_pk: dict[str, dict] = {}
    source_counts: dict[str, set] = {}

    for row in rows:
        pk = row.get("pk_unique_id")
        if not pk:
            continue

        source_url = row.get("source_url", "")

        if pk not in by_pk:
            by_pk[pk] = dict(row)
            source_counts[pk] = {source_url} if source_url else set()
            continue

        existing = by_pk[pk]
        source_counts[pk].add(source_url)

        # Merge list fields
        for col in JSON_LIST_COLUMNS:
            existing[col] = _merge_list_fields(existing[col], row[col])

        # Keep richest non-null scalar fields
        for key in row:
            if key in JSON_LIST_COLUMNS:
                continue
            if existing.get(key) is None and row.get(key) is not None:
                existing[key] = row[key]
            # For region, prefer the one that normalized successfully
            if key == "_normalized_region" and row.get(key) and not existing.get(key):
                existing[key] = row[key]

    # Add source_count
    for pk, entity in by_pk.items():
        entity["_source_count"] = len(source_counts.get(pk, set()))

    result = list(by_pk.values())
    logger.info("Deduplicated %d rows → %d unique entities", len(rows), len(result))
    return result


# ---------------------------------------------------------------------------
# Step 3: Build the graph
# ---------------------------------------------------------------------------

def build_graph(
    csv_path: str | Path,
    country_config: Any,
    *,
    skip_inference: bool = False,
    skip_deserts: bool = False,
) -> nx.MultiDiGraph:
    """Build the full knowledge graph from a CSV file.

    Args:
        csv_path: Path to the FDR CSV file.
        country_config: Country-specific config module (e.g., graph.config.ghana).
        skip_inference: If True, skip LACKS/COULD_SUPPORT edges.
        skip_deserts: If True, skip DESERT_FOR edges.
    """
    G = nx.MultiDiGraph()

    # --- Load & clean ---
    rows = load_csv(csv_path)
    rows = normalize_regions(rows, country_config)
    entities = deduplicate_rows(rows)

    # --- Create Region nodes ---
    for region_key, meta in country_config.REGION_METADATA.items():
        rid = region_id(region_key)
        G.add_node(
            rid,
            node_type=NODE_REGION,
            name=meta["display_name"],
            population=meta["population"],
            capital=meta["capital"],
            lat=meta["lat"],
            lng=meta["lng"],
        )
    logger.info("Created %d region nodes", len(country_config.REGION_METADATA))

    # --- Create Equipment nodes (from canonical vocab) ---
    for key, meta in CANONICAL_EQUIPMENT.items():
        eid = equipment_id(key)
        if not G.has_node(eid):
            G.add_node(
                eid,
                node_type=NODE_EQUIPMENT,
                display_name=meta["display"],
                category=meta["category"],
            )

    # --- Create Capability nodes (from canonical vocab) ---
    for key, meta in CANONICAL_CAPABILITIES.items():
        cid = capability_id(key)
        if not G.has_node(cid):
            G.add_node(
                cid,
                node_type=NODE_CAPABILITY,
                display_name=meta["display"],
                category=meta.get("category", "general"),
                complexity=meta.get("complexity", "medium"),
            )

    # --- Process entities ---
    facility_count = 0
    ngo_count = 0

    for entity in entities:
        pk = entity.get("pk_unique_id")
        org_type = entity.get("organization_type", "").lower()

        if org_type == "ngo":
            _add_ngo(G, entity, country_config)
            ngo_count += 1
        else:
            _add_facility(G, entity, country_config)
            facility_count += 1

    logger.info("Created %d facility nodes, %d NGO nodes", facility_count, ngo_count)

    # --- Inference edges ---
    if not skip_inference:
        lacks_count = add_lacks_edges(G)
        could_support_count = add_could_support_edges(G)
        logger.info("Added %d LACKS edges, %d COULD_SUPPORT edges", lacks_count, could_support_count)

    # --- Desert edges ---
    if not skip_deserts:
        desert_count = add_desert_edges(G, country_config)
        logger.info("Added %d DESERT_FOR edges", desert_count)

    # --- Summary ---
    node_type_counts: dict[str, int] = {}
    for _, data in G.nodes(data=True):
        nt = data.get("node_type", "unknown")
        node_type_counts[nt] = node_type_counts.get(nt, 0) + 1

    edge_type_counts: dict[str, int] = {}
    for _, _, data in G.edges(data=True):
        et = data.get("edge_type", "unknown")
        edge_type_counts[et] = edge_type_counts.get(et, 0) + 1

    logger.info(
        "Graph built: %d nodes (%s), %d edges (%s)",
        G.number_of_nodes(),
        node_type_counts,
        G.number_of_edges(),
        edge_type_counts,
    )

    return G


# ---------------------------------------------------------------------------
# Internal: Add a facility to the graph
# ---------------------------------------------------------------------------

def _add_facility(G: nx.MultiDiGraph, entity: dict, country_config: Any) -> None:
    pk = entity["pk_unique_id"]
    fid = facility_id(pk)

    # Facility node
    G.add_node(
        fid,
        node_type=NODE_FACILITY,
        name=entity.get("name", "Unknown"),
        facility_type=entity.get("facilityTypeId"),
        operator_type=entity.get("operatorTypeId"),
        capacity=entity.get("capacity"),
        number_doctors=entity.get("numberDoctors"),
        area=entity.get("area"),
        year_established=entity.get("yearEstablished"),
        city=entity.get("address_city"),
        region=entity.get("_normalized_region"),
        source_count=entity.get("_source_count", 1),
        email=entity.get("email"),
        phone_numbers=entity.get("phone_numbers", []),
        websites=entity.get("websites", []),
        description=entity.get("description"),
        raw_procedures=entity.get("procedure", []),
        raw_equipment=entity.get("equipment", []),
        raw_capabilities=entity.get("capability", []),
    )

    # LOCATED_IN edge
    region = entity.get("_normalized_region")
    if region:
        rid = region_id(region)
        if G.has_node(rid):
            G.add_edge(
                fid, rid,
                edge_type=EDGE_LOCATED_IN,
                city=entity.get("address_city"),
            )

    # HAS_SPECIALTY edges
    for spec in entity.get("specialties", []):
        if spec:
            sid = specialty_id(spec)
            if not G.has_node(sid):
                G.add_node(sid, node_type=NODE_SPECIALTY, display_name=spec)
            G.add_edge(
                fid, sid,
                edge_type=EDGE_HAS_SPECIALTY,
                source="structured",
                confidence=0.9,
            )

    # HAS_EQUIPMENT edges (normalize free text)
    raw_equipment = entity.get("equipment", [])
    if raw_equipment:
        equipment_matches = normalize_equipment_list(raw_equipment)
        for canonical_key, confidence, raw_text in equipment_matches:
            eid = equipment_id(canonical_key)
            G.add_edge(
                fid, eid,
                edge_type=EDGE_HAS_EQUIPMENT,
                confidence=confidence,
                raw_text=raw_text,
            )

    # Also extract equipment mentions from capability and description fields
    extra_text_sources = []
    for cap in entity.get("capability", []):
        if cap:
            extra_text_sources.append(cap)
    desc = entity.get("description")
    if desc:
        extra_text_sources.append(desc)

    if extra_text_sources:
        combined = " ".join(extra_text_sources)
        from graph.normalize import match_equipment
        eq_from_text = match_equipment(combined)
        for canonical_key, confidence in eq_from_text:
            eid = equipment_id(canonical_key)
            # Only add if not already linked
            existing = [
                d for _, _, d in G.edges(fid, data=True)
                if d.get("edge_type") == EDGE_HAS_EQUIPMENT
            ]
            existing_keys = {equipment_id(k) for _, t, d in G.edges(fid, data=True) if d.get("edge_type") == EDGE_HAS_EQUIPMENT for k in [t]}
            if eid not in existing_keys:
                G.add_edge(
                    fid, eid,
                    edge_type=EDGE_HAS_EQUIPMENT,
                    confidence=confidence * 0.8,  # slightly lower confidence from text extraction
                    raw_text="[extracted from description/capability]",
                )

    # HAS_CAPABILITY edges (normalize procedures + capabilities)
    raw_procedures = entity.get("procedure", [])
    raw_capabilities = entity.get("capability", [])

    if raw_procedures:
        proc_matches = normalize_capability_list(raw_procedures, source_field="procedure")
        for canonical_key, confidence, raw_text, src in proc_matches:
            cid = capability_id(canonical_key)
            G.add_edge(
                fid, cid,
                edge_type=EDGE_HAS_CAPABILITY,
                confidence=confidence,
                raw_text=raw_text,
                source_field=src,
            )

    if raw_capabilities:
        cap_matches = normalize_capability_list(raw_capabilities, source_field="capability")
        for canonical_key, confidence, raw_text, src in cap_matches:
            cid = capability_id(canonical_key)
            G.add_edge(
                fid, cid,
                edge_type=EDGE_HAS_CAPABILITY,
                confidence=confidence,
                raw_text=raw_text,
                source_field=src,
            )

    # Also extract capabilities from description
    if desc:
        desc_caps = normalize_capability_list([desc], source_field="description")
        for canonical_key, confidence, raw_text, src in desc_caps:
            cid = capability_id(canonical_key)
            G.add_edge(
                fid, cid,
                edge_type=EDGE_HAS_CAPABILITY,
                confidence=confidence * 0.7,  # lower confidence from description
                raw_text=raw_text,
                source_field=src,
            )


# ---------------------------------------------------------------------------
# Internal: Add an NGO to the graph
# ---------------------------------------------------------------------------

def _add_ngo(G: nx.MultiDiGraph, entity: dict, country_config: Any) -> None:
    pk = entity["pk_unique_id"]
    nid = ngo_id(pk)

    G.add_node(
        nid,
        node_type=NODE_NGO,
        name=entity.get("name", "Unknown"),
        countries=entity.get("countries", []),
        mission_summary=entity.get("missionStatement"),
        description=entity.get("organizationDescription") or entity.get("description"),
        email=entity.get("email"),
        phone_numbers=entity.get("phone_numbers", []),
        websites=entity.get("websites", []),
        source_count=entity.get("_source_count", 1),
    )

    # OPERATES_IN via region
    region = entity.get("_normalized_region")
    if region:
        rid = region_id(region)
        if G.has_node(rid):
            G.add_edge(
                nid, rid,
                edge_type=EDGE_OPERATES_IN,
                source="address",
            )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Build the graph from command line."""
    import argparse
    import importlib

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Build knowledge graph from FDR CSV")
    parser.add_argument("csv_path", help="Path to FDR CSV file")
    parser.add_argument(
        "--country", default="ghana",
        help="Country config module name (default: ghana)",
    )
    parser.add_argument("--skip-inference", action="store_true", help="Skip LACKS/COULD_SUPPORT edges")
    parser.add_argument("--skip-deserts", action="store_true", help="Skip DESERT_FOR edges")
    parser.add_argument("--output-dir", default="data", help="Output directory (default: data)")
    args = parser.parse_args()

    # Import country config
    config_module = importlib.import_module(f"graph.config.{args.country}")

    G = build_graph(
        args.csv_path,
        config_module,
        skip_inference=args.skip_inference,
        skip_deserts=args.skip_deserts,
    )

    # Export
    from graph.export import save_graph
    save_graph(G, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
