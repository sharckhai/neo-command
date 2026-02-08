"""Runtime query functions for agents.

These functions power the VERIFY, PLAN, and EXPLORE modes of VirtueCommand.
They will be wrapped as LangGraph tools for agent tool-calling.
"""

from __future__ import annotations

import math
from typing import Any

import networkx as nx

from graph.config.ghana import REGION_ADJACENCY, REGION_METADATA
from graph.medical_requirements import CAPABILITY_REQUIREMENTS
from graph.schema import (
    NODE_FACILITY, NODE_REGION, NODE_SPECIALTY, NODE_CAPABILITY, NODE_EQUIPMENT,
    EDGE_HAS_CAPABILITY, EDGE_HAS_EQUIPMENT, EDGE_HAS_SPECIALTY,
    EDGE_LACKS, EDGE_COULD_SUPPORT, EDGE_DESERT_FOR, EDGE_LOCATED_IN,
    EDGE_OPERATES_IN,
    facility_id, region_id, specialty_id, capability_id, equipment_id,
)


# ---------------------------------------------------------------------------
# VERIFY mode
# ---------------------------------------------------------------------------

def get_facility_mismatches(G: nx.MultiDiGraph, fid: str) -> dict[str, Any]:
    """Get all LACKS edges + context for a single facility.

    Returns:
        {
            "facility_id": str,
            "facility_name": str,
            "lacks": [
                {
                    "equipment": str,
                    "equipment_display": str,
                    "required_by": [str],
                    "evidence_status": str,
                }
            ],
            "claimed_capabilities": [str],
            "confirmed_equipment": [str],
            "mismatch_ratio": float,  # lacks / (lacks + confirmed)
        }
    """
    if not G.has_node(fid):
        return {"error": f"Facility {fid} not found"}

    fdata = G.nodes[fid]
    lacks = []
    confirmed_equipment = []
    claimed_capabilities = []

    for _, target, edata in G.edges(fid, data=True):
        etype = edata.get("edge_type")

        if etype == EDGE_LACKS:
            eq_key = target.split("::", 1)[1] if "::" in target else target
            eq_display = G.nodes[target].get("display_name", eq_key) if G.has_node(target) else eq_key
            lacks.append({
                "equipment": eq_key,
                "equipment_display": eq_display,
                "required_by": edata.get("required_by", []),
                "evidence_status": edata.get("evidence_status", "unknown"),
            })
        elif etype == EDGE_HAS_EQUIPMENT:
            eq_key = target.split("::", 1)[1] if "::" in target else target
            confirmed_equipment.append(eq_key)
        elif etype == EDGE_HAS_CAPABILITY:
            cap_key = target.split("::", 1)[1] if "::" in target else target
            claimed_capabilities.append(cap_key)

    total = len(lacks) + len(confirmed_equipment)
    ratio = len(lacks) / total if total > 0 else 0.0

    return {
        "facility_id": fid,
        "facility_name": fdata.get("name", "Unknown"),
        "region": fdata.get("region"),
        "lacks": lacks,
        "claimed_capabilities": list(set(claimed_capabilities)),
        "confirmed_equipment": list(set(confirmed_equipment)),
        "mismatch_ratio": round(ratio, 3),
    }


# ---------------------------------------------------------------------------
# PLAN mode
# ---------------------------------------------------------------------------

def get_deserts_for_specialty(G: nx.MultiDiGraph, specialty_key: str) -> list[dict[str, Any]]:
    """Get all regions that are deserts for a given specialty.

    Returns list sorted by severity (worst first).
    """
    sid = specialty_id(specialty_key)
    results = []

    for source, target, edata in G.edges(data=True):
        if edata.get("edge_type") != EDGE_DESERT_FOR:
            continue
        if target != sid:
            continue

        region_key = source.split("::", 1)[1] if "::" in source else source
        rdata = G.nodes.get(source, {})

        results.append({
            "region": region_key,
            "region_name": rdata.get("name", region_key),
            "population": edata.get("population", 0),
            "facility_count": edata.get("facility_count", 0),
            "severity": edata.get("severity", 0),
            "nearest_region_with_service": edata.get("nearest_region_with_service"),
        })

    results.sort(key=lambda x: x["severity"], reverse=True)
    return results


def get_facilities_that_could_support(
    G: nx.MultiDiGraph,
    capability_key: str,
) -> list[dict[str, Any]]:
    """Find facilities that COULD_SUPPORT a given capability.

    Sorted by readiness_score descending (most ready first).
    """
    cid = capability_id(capability_key)
    results = []

    for source, target, edata in G.edges(data=True):
        if edata.get("edge_type") != EDGE_COULD_SUPPORT:
            continue
        if target != cid:
            continue

        fdata = G.nodes.get(source, {})
        results.append({
            "facility_id": source,
            "facility_name": fdata.get("name", "Unknown"),
            "region": fdata.get("region"),
            "readiness_score": edata.get("readiness_score", 0),
            "existing_equipment": edata.get("existing_equipment", []),
            "missing_equipment": edata.get("missing_equipment", []),
        })

    results.sort(key=lambda x: x["readiness_score"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# EXPLORE mode
# ---------------------------------------------------------------------------

def get_facility_details(G: nx.MultiDiGraph, fid: str) -> dict[str, Any]:
    """Get comprehensive details about a facility including all edges."""
    if not G.has_node(fid):
        return {"error": f"Facility {fid} not found"}

    fdata = dict(G.nodes[fid])
    result = {
        "facility_id": fid,
        **fdata,
        "specialties": [],
        "capabilities": [],
        "equipment": [],
        "lacks": [],
        "could_support": [],
    }

    for _, target, edata in G.edges(fid, data=True):
        etype = edata.get("edge_type")
        target_data = G.nodes.get(target, {})
        target_key = target.split("::", 1)[1] if "::" in target else target

        if etype == EDGE_HAS_SPECIALTY:
            result["specialties"].append({
                "key": target_key,
                "display_name": target_data.get("display_name", target_key),
                "confidence": edata.get("confidence", 0),
                "source": edata.get("source"),
            })
        elif etype == EDGE_HAS_CAPABILITY:
            result["capabilities"].append({
                "key": target_key,
                "display_name": target_data.get("display_name", target_key),
                "confidence": edata.get("confidence", 0),
                "source_field": edata.get("source_field"),
                "raw_text": edata.get("raw_text"),
            })
        elif etype == EDGE_HAS_EQUIPMENT:
            result["equipment"].append({
                "key": target_key,
                "display_name": target_data.get("display_name", target_key),
                "confidence": edata.get("confidence", 0),
                "raw_text": edata.get("raw_text"),
            })
        elif etype == EDGE_LACKS:
            result["lacks"].append({
                "equipment": target_key,
                "display_name": target_data.get("display_name", target_key),
                "required_by": edata.get("required_by", []),
                "evidence_status": edata.get("evidence_status"),
            })
        elif etype == EDGE_COULD_SUPPORT:
            result["could_support"].append({
                "capability": target_key,
                "display_name": target_data.get("display_name", target_key),
                "readiness_score": edata.get("readiness_score", 0),
                "missing_equipment": edata.get("missing_equipment", []),
            })

    return result


def get_graph_summary(G: nx.MultiDiGraph) -> dict[str, Any]:
    """Get summary statistics about the graph."""
    node_counts: dict[str, int] = {}
    for _, data in G.nodes(data=True):
        nt = data.get("node_type", "unknown")
        node_counts[nt] = node_counts.get(nt, 0) + 1

    edge_counts: dict[str, int] = {}
    for _, _, data in G.edges(data=True):
        et = data.get("edge_type", "unknown")
        edge_counts[et] = edge_counts.get(et, 0) + 1

    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "node_counts": node_counts,
        "edge_counts": edge_counts,
    }


# ---------------------------------------------------------------------------
# Specialty discovery
# ---------------------------------------------------------------------------

def list_specialties(G: nx.MultiDiGraph) -> list[dict]:
    """List all specialty nodes with their facility counts.

    Returns list of dicts sorted by facility_count descending:
        [{"key": "gynecologyAndObstetrics", "display_name": "...", "facility_count": 108}, ...]
    """
    specialty_counts: dict[str, dict] = {}

    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_SPECIALTY:
            continue
        key = nid.split("::", 1)[1] if "::" in nid else nid
        specialty_counts[key] = {
            "key": key,
            "display_name": ndata.get("display_name", key),
            "facility_count": 0,
        }

    # Count facilities per specialty
    for source, target, edata in G.edges(data=True):
        if edata.get("edge_type") != EDGE_HAS_SPECIALTY:
            continue
        sdata = G.nodes.get(source, {})
        if sdata.get("node_type") != NODE_FACILITY:
            continue
        key = target.split("::", 1)[1] if "::" in target else target
        if key in specialty_counts:
            specialty_counts[key]["facility_count"] += 1

    results = list(specialty_counts.values())
    results.sort(key=lambda x: x["facility_count"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# Geospatial queries
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km between two lat/lng points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Region exploration
# ---------------------------------------------------------------------------

def list_regions(G: nx.MultiDiGraph) -> list[dict]:
    """List all 16 regions with population, facility count, and desert count.

    Returns list sorted by population descending.
    """
    region_stats: dict[str, dict] = {}

    # Initialize from region nodes
    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_REGION:
            continue
        key = nid.split("::", 1)[1] if "::" in nid else nid
        region_stats[key] = {
            "region_key": key,
            "display_name": ndata.get("name", key),
            "population": ndata.get("population", 0),
            "facility_count": 0,
            "desert_count": 0,
        }

    # Count facilities per region
    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue
        region = ndata.get("region")
        if region and region in region_stats:
            region_stats[region]["facility_count"] += 1

    # Count deserts per region
    for source, _, edata in G.edges(data=True):
        if edata.get("edge_type") != EDGE_DESERT_FOR:
            continue
        key = source.split("::", 1)[1] if "::" in source else source
        if key in region_stats:
            region_stats[key]["desert_count"] += 1

    results = list(region_stats.values())
    results.sort(key=lambda x: x["population"], reverse=True)
    return results


def get_region_details(G: nx.MultiDiGraph, region_key: str) -> dict:
    """Deep-dive into a region: facilities, specialties, deserts, NGOs, neighbours.

    Args:
        region_key: Canonical region key (e.g. "northern", "greater_accra").
    """
    rid = region_id(region_key)
    if not G.has_node(rid):
        return {"error": f"Region '{region_key}' not found"}

    rdata = G.nodes[rid]

    # Facilities in this region
    facilities = []
    specialty_counts: dict[str, int] = {}
    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue
        if ndata.get("region") != region_key:
            continue
        facilities.append({
            "facility_id": nid,
            "name": ndata.get("name", "Unknown"),
            "city": ndata.get("city"),
            "facility_type": ndata.get("facility_type"),
        })
        # Count specialties
        for _, target, edata in G.edges(nid, data=True):
            if edata.get("edge_type") == EDGE_HAS_SPECIALTY and edata.get("confidence", 0) >= 0.5:
                skey = target.split("::", 1)[1] if "::" in target else target
                specialty_counts[skey] = specialty_counts.get(skey, 0) + 1

    # Deserts for this region
    deserts = []
    for _, target, edata in G.edges(rid, data=True):
        if edata.get("edge_type") != EDGE_DESERT_FOR:
            continue
        skey = target.split("::", 1)[1] if "::" in target else target
        deserts.append({
            "specialty": skey,
            "severity": edata.get("severity", 0),
            "nearest_region_with_service": edata.get("nearest_region_with_service"),
        })
    deserts.sort(key=lambda x: x["severity"], reverse=True)

    # NGOs operating in this region
    ngos = []
    for source, target, edata in G.edges(data=True):
        if edata.get("edge_type") != EDGE_OPERATES_IN:
            continue
        if target != rid:
            continue
        ngo_data = G.nodes.get(source, {})
        ngos.append({
            "ngo_id": source,
            "name": ngo_data.get("name", "Unknown"),
        })

    # Neighbours from adjacency config
    neighbours = REGION_ADJACENCY.get(region_key, [])

    return {
        "region_key": region_key,
        "display_name": rdata.get("name", region_key),
        "population": rdata.get("population", 0),
        "capital": REGION_METADATA.get(region_key, {}).get("capital"),
        "facility_count": len(facilities),
        "facilities": facilities,
        "specialty_counts": specialty_counts,
        "deserts": deserts,
        "ngos": ngos,
        "neighbours": neighbours,
    }


# ---------------------------------------------------------------------------
# Equipment & capability analysis
# ---------------------------------------------------------------------------

def get_capability_requirements(capability_key: str) -> dict:
    """Get required and recommended equipment for a capability.

    Args:
        capability_key: Canonical capability key (e.g. "cataract_surgery").

    Returns dict with required, recommended lists and the capability key.
    Returns error if capability not found in CAPABILITY_REQUIREMENTS.
    """
    reqs = CAPABILITY_REQUIREMENTS.get(capability_key)
    if reqs is None:
        return {
            "error": f"Unknown capability: '{capability_key}'",
            "available_capabilities": sorted(CAPABILITY_REQUIREMENTS.keys()),
        }
    return {
        "capability": capability_key,
        "required": reqs.get("required", []),
        "recommended": reqs.get("recommended", []),
    }


def get_specialty_capabilities(G: nx.MultiDiGraph, specialty_key: str) -> dict:
    """Which capabilities do facilities of a specialty have, with counts and percentages.

    Args:
        specialty_key: Canonical specialty key (e.g. "ophthalmology").
    """
    sid = specialty_id(specialty_key)
    if not G.has_node(sid):
        return {"error": f"Specialty '{specialty_key}' not found"}

    # Find all facilities with this specialty
    facility_ids = []
    for source, target, edata in G.edges(data=True):
        if edata.get("edge_type") != EDGE_HAS_SPECIALTY:
            continue
        if target != sid:
            continue
        if edata.get("confidence", 0) < 0.5:
            continue
        sdata = G.nodes.get(source, {})
        if sdata.get("node_type") == NODE_FACILITY:
            facility_ids.append(source)

    total = len(facility_ids)
    if total == 0:
        return {
            "specialty": specialty_key,
            "facility_count": 0,
            "capabilities": [],
        }

    # Count capabilities across these facilities
    cap_counts: dict[str, int] = {}
    for fid in facility_ids:
        for _, target, edata in G.edges(fid, data=True):
            if edata.get("edge_type") == EDGE_HAS_CAPABILITY:
                ckey = target.split("::", 1)[1] if "::" in target else target
                cap_counts[ckey] = cap_counts.get(ckey, 0) + 1

    capabilities = [
        {
            "capability": key,
            "count": count,
            "percentage": round(count / total * 100, 1),
        }
        for key, count in cap_counts.items()
    ]
    capabilities.sort(key=lambda x: x["count"], reverse=True)

    return {
        "specialty": specialty_key,
        "facility_count": total,
        "capabilities": capabilities,
    }


# ---------------------------------------------------------------------------
# New composable query functions (v2)
# ---------------------------------------------------------------------------

def _extract_key(node_id: str) -> str:
    """Extract the key portion from a namespaced node ID like 'facility::123'."""
    return node_id.split("::", 1)[1] if "::" in node_id else node_id


def _get_facility_edges(G: nx.MultiDiGraph, fid: str) -> dict[str, list]:
    """Collect all edges for a facility, grouped by edge type."""
    edges: dict[str, list] = {
        "specialties": [],
        "capabilities": [],
        "equipment": [],
        "lacks": [],
        "could_support": [],
    }
    for _, target, edata in G.edges(fid, data=True):
        etype = edata.get("edge_type")
        key = _extract_key(target)
        if etype == EDGE_HAS_SPECIALTY:
            edges["specialties"].append((key, edata))
        elif etype == EDGE_HAS_CAPABILITY:
            edges["capabilities"].append((key, edata))
        elif etype == EDGE_HAS_EQUIPMENT:
            edges["equipment"].append((key, edata))
        elif etype == EDGE_LACKS:
            edges["lacks"].append((key, edata))
        elif etype == EDGE_COULD_SUPPORT:
            edges["could_support"].append((key, edata))
    return edges


def _facility_matches_filters(
    G: nx.MultiDiGraph,
    fid: str,
    fdata: dict,
    *,
    capability: str | None = None,
    equipment: str | None = None,
    specialty: str | None = None,
    region: str | None = None,
    facility_type: str | None = None,
    min_capacity: int | None = None,
) -> tuple[bool, list[str]]:
    """Check if a facility matches all provided filters.

    Returns (matches: bool, matched_criteria: list[str]).
    """
    matched = []

    if region and fdata.get("region") != region:
        return False, []
    if region:
        matched.append(f"region={region}")

    if facility_type:
        ft = fdata.get("facility_type", "")
        if ft and facility_type.lower() not in ft.lower():
            return False, []
        elif not ft:
            return False, []
        matched.append(f"facility_type={facility_type}")

    if min_capacity is not None:
        cap = fdata.get("capacity") or fdata.get("number_beds") or 0
        if isinstance(cap, str):
            try:
                cap = int(cap)
            except ValueError:
                cap = 0
        if cap < min_capacity:
            return False, []
        matched.append(f"capacity>={min_capacity}")

    if capability:
        cid = capability_id(capability)
        has = any(
            edata.get("edge_type") == EDGE_HAS_CAPABILITY and target == cid
            for _, target, edata in G.edges(fid, data=True)
        )
        if not has:
            return False, []
        matched.append(f"capability={capability}")

    if equipment:
        eid = equipment_id(equipment)
        has = any(
            edata.get("edge_type") == EDGE_HAS_EQUIPMENT and target == eid
            for _, target, edata in G.edges(fid, data=True)
        )
        if not has:
            return False, []
        matched.append(f"equipment={equipment}")

    if specialty:
        sid = specialty_id(specialty)
        has = any(
            edata.get("edge_type") == EDGE_HAS_SPECIALTY
            and target == sid
            for _, target, edata in G.edges(fid, data=True)
        )
        if not has:
            return False, []
        matched.append(f"specialty={specialty}")

    return True, matched


# 1. fuzzy_find_facility
def fuzzy_find_facility(
    G: nx.MultiDiGraph,
    name: str,
    region: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Fuzzy-match a user-provided facility name to graph facility IDs.

    Uses case-insensitive substring match then token overlap scoring.
    """
    query_lower = name.lower().strip()
    query_tokens = set(query_lower.split())
    matches: list[dict] = []

    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue
        if region and ndata.get("region") != region:
            continue

        fname = ndata.get("name", "")
        fname_lower = fname.lower()

        # Score: substring match gets base score, then token overlap
        score = 0.0
        if query_lower in fname_lower:
            score = 0.8
        elif fname_lower in query_lower:
            score = 0.7
        else:
            # Token overlap
            fname_tokens = set(fname_lower.split())
            overlap = query_tokens & fname_tokens
            if overlap:
                score = len(overlap) / max(len(query_tokens), len(fname_tokens))
                score = round(score * 0.6, 3)  # cap token-only matches

        if score > 0:
            matches.append({
                "facility_id": nid,
                "name": fname,
                "region": ndata.get("region"),
                "city": ndata.get("city"),
                "facility_type": ndata.get("facility_type"),
                "match_score": round(score, 3),
            })

    matches.sort(key=lambda x: x["match_score"], reverse=True)
    return {
        "query": name,
        "matches": matches[:limit],
    }


# 2. search_facilities_multi
def search_facilities_multi(
    G: nx.MultiDiGraph,
    *,
    capability: str | None = None,
    equipment: str | None = None,
    specialty: str | None = None,
    region: str | None = None,
    facility_type: str | None = None,
    min_capacity: int | None = None,
    near_lat: float | None = None,
    near_lng: float | None = None,
    radius_km: float | None = None,
    limit: int = 25,
    sort_by: str = "relevance",
) -> dict[str, Any]:
    """Multi-criteria facility search with optional geospatial filtering."""
    results: list[dict] = []

    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue

        matches, matched_criteria = _facility_matches_filters(
            G, nid, ndata,
            capability=capability, equipment=equipment, specialty=specialty,
            region=region, facility_type=facility_type, min_capacity=min_capacity,
        )
        if not matches:
            continue

        # Geospatial filter
        distance_km = None
        if near_lat is not None and near_lng is not None:
            flat = ndata.get("lat")
            flng = ndata.get("lng")
            if flat is None or flng is None:
                continue
            distance_km = round(_haversine_km(near_lat, near_lng, flat, flng), 2)
            if radius_km is not None and distance_km > radius_km:
                continue

        entry = {
            "facility_id": nid,
            "name": ndata.get("name", "Unknown"),
            "region": ndata.get("region"),
            "city": ndata.get("city"),
            "facility_type": ndata.get("facility_type"),
            "capacity": ndata.get("capacity"),
            "matched_criteria": matched_criteria,
        }
        if distance_km is not None:
            entry["distance_km"] = distance_km

        results.append(entry)

    # Sort
    if sort_by == "distance" and near_lat is not None:
        results.sort(key=lambda x: x.get("distance_km", 99999))
    elif sort_by == "capacity":
        results.sort(key=lambda x: x.get("capacity") or 0, reverse=True)
    else:
        results.sort(key=lambda x: len(x.get("matched_criteria", [])), reverse=True)

    total = len(results)
    return {
        "total_matches": total,
        "facilities": results[:limit],
    }


# 3. count_and_group_facilities
def count_and_group_facilities(
    G: nx.MultiDiGraph,
    group_by: str,
    *,
    capability: str | None = None,
    equipment: str | None = None,
    specialty: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """Count facilities grouped by a dimension, with optional filters.

    Args:
        group_by: One of "region", "specialty", "capability", "facility_type", "equipment".
    """
    counts: dict[str, int] = {}
    total = 0

    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue

        matches, _ = _facility_matches_filters(
            G, nid, ndata,
            capability=capability, equipment=equipment,
            specialty=specialty, region=region,
        )
        if not matches:
            continue

        total += 1

        if group_by == "region":
            key = ndata.get("region", "unknown")
            counts[key] = counts.get(key, 0) + 1

        elif group_by == "facility_type":
            key = ndata.get("facility_type", "unknown") or "unknown"
            counts[key] = counts.get(key, 0) + 1

        elif group_by == "specialty":
            for _, target, edata in G.edges(nid, data=True):
                if edata.get("edge_type") == EDGE_HAS_SPECIALTY:
                    skey = _extract_key(target)
                    counts[skey] = counts.get(skey, 0) + 1

        elif group_by == "capability":
            for _, target, edata in G.edges(nid, data=True):
                if edata.get("edge_type") == EDGE_HAS_CAPABILITY:
                    ckey = _extract_key(target)
                    counts[ckey] = counts.get(ckey, 0) + 1

        elif group_by == "equipment":
            for _, target, edata in G.edges(nid, data=True):
                if edata.get("edge_type") == EDGE_HAS_EQUIPMENT:
                    ekey = _extract_key(target)
                    counts[ekey] = counts.get(ekey, 0) + 1

    # Build display names
    groups = []
    for key, count in counts.items():
        display_name = key
        if group_by == "region":
            meta = REGION_METADATA.get(key, {})
            display_name = meta.get("display_name", key)
        elif group_by in ("specialty", "capability", "equipment"):
            nid_lookup = f"{group_by}::{key}"
            nd = G.nodes.get(nid_lookup, {})
            display_name = nd.get("display_name", key)

        groups.append({
            "key": key,
            "display_name": display_name,
            "count": count,
            "percentage": round(count / total * 100, 1) if total else 0,
        })

    groups.sort(key=lambda x: x["count"], reverse=True)

    return {
        "total_matching": total,
        "group_by": group_by,
        "groups": groups,
    }


# 4. detect_procedure_size_anomalies
def detect_procedure_size_anomalies(
    G: nx.MultiDiGraph,
    region: str | None = None,
    threshold: float = 0.6,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Flag facilities claiming many procedures relative to their size/capacity."""
    results: list[dict] = []

    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue
        if region and ndata.get("region") != region:
            continue

        cap = ndata.get("capacity") or ndata.get("number_beds") or 0
        if isinstance(cap, str):
            try:
                cap = int(cap)
            except ValueError:
                cap = 0

        # Count high-complexity capabilities
        capabilities = []
        high_complexity = 0
        for _, target, edata in G.edges(nid, data=True):
            if edata.get("edge_type") == EDGE_HAS_CAPABILITY:
                ckey = _extract_key(target)
                capabilities.append(ckey)
                tdata = G.nodes.get(target, {})
                if tdata.get("complexity") == "high":
                    high_complexity += 1

        if not capabilities:
            continue

        # Anomaly: small facility with many high-complexity procedures
        # Or: very many capabilities relative to capacity
        anomaly_score = 0.0
        explanation = ""

        if cap > 0 and cap <= 50 and high_complexity >= 3:
            anomaly_score = min(1.0, high_complexity / 3 * 0.5 + (50 - cap) / 50 * 0.5)
            explanation = f"Capacity {cap} beds but claims {high_complexity} high-complexity procedures"
        elif cap == 0 and high_complexity >= 2:
            anomaly_score = 0.7
            explanation = f"Unknown capacity but claims {high_complexity} high-complexity procedures"
        elif cap > 0 and len(capabilities) > cap * 0.5 and len(capabilities) >= 8:
            anomaly_score = min(1.0, len(capabilities) / (cap * 0.5) * 0.4)
            explanation = f"Capacity {cap} beds but claims {len(capabilities)} total capabilities"

        if anomaly_score >= threshold:
            results.append({
                "facility_id": nid,
                "name": ndata.get("name", "Unknown"),
                "region": ndata.get("region"),
                "anomaly_score": round(anomaly_score, 3),
                "details": {
                    "explanation": explanation,
                    "capacity": cap,
                    "total_capabilities": len(capabilities),
                    "high_complexity_count": high_complexity,
                },
            })

    results.sort(key=lambda x: x["anomaly_score"], reverse=True)
    return results[:limit]


# 5. detect_equipment_claim_anomalies
def detect_equipment_claim_anomalies(
    G: nx.MultiDiGraph,
    region: str | None = None,
    threshold: float = 0.4,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Flag facilities with many capabilities but few equipment items (high LACKS ratio)."""
    results: list[dict] = []

    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue
        if region and ndata.get("region") != region:
            continue

        edges = _get_facility_edges(G, nid)
        num_caps = len(edges["capabilities"])
        num_equip = len(edges["equipment"])
        num_lacks = len(edges["lacks"])

        if num_caps == 0:
            continue

        # Anomaly: many capabilities, few equipment, many lacks
        total_equip = num_equip + num_lacks
        lacks_ratio = num_lacks / total_equip if total_equip > 0 else 0
        cap_to_equip = num_caps / (num_equip + 1)

        anomaly_score = 0.0
        explanation = ""

        if lacks_ratio >= 0.5 and num_lacks >= 2:
            anomaly_score = lacks_ratio * 0.6 + min(cap_to_equip / 5, 0.4)
            explanation = (
                f"Claims {num_caps} capabilities but lacks {num_lacks}/{total_equip} "
                f"equipment items (lacks ratio {lacks_ratio:.0%})"
            )
        elif cap_to_equip >= 3 and num_caps >= 4:
            anomaly_score = min(1.0, cap_to_equip / 6)
            explanation = (
                f"Claims {num_caps} capabilities but only {num_equip} equipment items "
                f"(ratio {cap_to_equip:.1f}:1)"
            )

        if anomaly_score >= threshold:
            results.append({
                "facility_id": nid,
                "name": ndata.get("name", "Unknown"),
                "region": ndata.get("region"),
                "anomaly_score": round(min(anomaly_score, 1.0), 3),
                "details": {
                    "explanation": explanation,
                    "capabilities_count": num_caps,
                    "equipment_count": num_equip,
                    "lacks_count": num_lacks,
                    "lacks_ratio": round(lacks_ratio, 3),
                },
            })

    results.sort(key=lambda x: x["anomaly_score"], reverse=True)
    return results[:limit]


# 6. detect_feature_correlations
def detect_feature_correlations(
    G: nx.MultiDiGraph,
    region: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Flag facilities where expected correlated features don't appear together.

    E.g., has surgery capabilities but no operating_theatre, or has ICU but no ventilator.
    """
    EXPECTED_CORRELATIONS = [
        (["general_surgery", "cesarean_section", "orthopedic_surgery", "cardiac_surgery",
          "neurosurgery", "laparoscopic_surgery", "plastic_surgery", "urology_surgery"],
         ["operating_theatre"], "Surgery capability without operating theatre"),
        (["icu_services"], ["ventilator", "patient_monitor"], "ICU without ventilator or patient monitor"),
        (["emergency_services"], ["defibrillator", "oxygen_supply"], "Emergency services without defibrillator or oxygen"),
        (["cesarean_section"], ["blood_bank"], "Cesarean section without blood bank"),
        (["dialysis"], ["dialysis_machine"], "Dialysis service without dialysis machine"),
        (["ct_imaging"], ["ct_scanner"], "CT imaging without CT scanner"),
        (["mri_imaging"], ["mri_scanner"], "MRI imaging without MRI scanner"),
    ]

    results: list[dict] = []

    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue
        if region and ndata.get("region") != region:
            continue

        edges = _get_facility_edges(G, nid)
        cap_keys = {k for k, _ in edges["capabilities"]}
        equip_keys = {k for k, _ in edges["equipment"]}

        violations = []
        for trigger_caps, expected_equip, desc in EXPECTED_CORRELATIONS:
            has_trigger = cap_keys & set(trigger_caps)
            if not has_trigger:
                continue
            missing = set(expected_equip) - equip_keys
            if missing:
                violations.append({
                    "trigger": list(has_trigger),
                    "missing_equipment": list(missing),
                    "description": desc,
                })

        if violations:
            results.append({
                "facility_id": nid,
                "name": ndata.get("name", "Unknown"),
                "region": ndata.get("region"),
                "anomaly_score": round(min(len(violations) / 3, 1.0), 3),
                "details": {
                    "violations": violations,
                    "total_violations": len(violations),
                },
            })

    results.sort(key=lambda x: x["anomaly_score"], reverse=True)
    return results[:limit]


# 7. detect_bed_or_anomalies
def detect_bed_or_anomalies(
    G: nx.MultiDiGraph,
    region: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Flag facilities with unusual bed-to-surgical-capability ratios."""
    results: list[dict] = []
    surgical_caps = {
        "general_surgery", "cesarean_section", "orthopedic_surgery",
        "cardiac_surgery", "neurosurgery", "laparoscopic_surgery",
        "cataract_surgery", "eye_surgery", "plastic_surgery", "urology_surgery",
    }

    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue
        if region and ndata.get("region") != region:
            continue

        beds = ndata.get("capacity") or ndata.get("number_beds") or 0
        if isinstance(beds, str):
            try:
                beds = int(beds)
            except ValueError:
                beds = 0
        if beds == 0:
            continue

        edges = _get_facility_edges(G, nid)
        cap_keys = {k for k, _ in edges["capabilities"]}
        surg_count = len(cap_keys & surgical_caps)

        has_ot = any(k == "operating_theatre" for k, _ in edges["equipment"])

        anomaly_score = 0.0
        explanation = ""

        # High beds but no surgical capability at all
        if beds >= 50 and surg_count == 0 and has_ot:
            anomaly_score = 0.6
            explanation = f"{beds} beds with operating theatre but zero surgical capabilities claimed"
        # Few beds, many surgeries
        elif beds <= 20 and surg_count >= 4:
            anomaly_score = min(1.0, surg_count / 4 * 0.7)
            explanation = f"Only {beds} beds but claims {surg_count} surgical capabilities"
        # Very high beds to surgery ratio
        elif surg_count > 0 and beds / surg_count > 100:
            anomaly_score = 0.5
            explanation = f"{beds} beds for {surg_count} surgical capabilities (ratio {beds/surg_count:.0f}:1)"

        if anomaly_score > 0.3:
            results.append({
                "facility_id": nid,
                "name": ndata.get("name", "Unknown"),
                "region": ndata.get("region"),
                "anomaly_score": round(anomaly_score, 3),
                "details": {
                    "explanation": explanation,
                    "beds": beds,
                    "surgical_capabilities": surg_count,
                    "has_operating_theatre": has_ot,
                },
            })

    results.sort(key=lambda x: x["anomaly_score"], reverse=True)
    return results[:limit]


# 8. find_geographic_cold_spots
def find_geographic_cold_spots(
    G: nx.MultiDiGraph,
    capability: str | None = None,
    specialty: str | None = None,
    radius_km: float = 100.0,
) -> dict[str, Any]:
    """Identify regions where a capability/specialty is absent within radius_km.

    Checks each region centroid for nearest facility with the specified service.
    """
    if not capability and not specialty:
        return {"error": "Provide either capability or specialty"}

    cid = capability_id(capability) if capability else None
    sid = specialty_id(specialty) if specialty else None

    # Find all facilities offering the service, with their coords
    service_facilities: list[tuple[float, float, str]] = []
    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue
        flat = ndata.get("lat")
        flng = ndata.get("lng")
        if flat is None or flng is None:
            continue

        has_service = False
        for _, target, edata in G.edges(nid, data=True):
            if cid and edata.get("edge_type") == EDGE_HAS_CAPABILITY and target == cid:
                has_service = True
                break
            if sid and edata.get("edge_type") == EDGE_HAS_SPECIALTY and target == sid and edata.get("confidence", 0) >= 0.5:
                has_service = True
                break
        if has_service:
            service_facilities.append((flat, flng, ndata.get("region", "")))

    cold_spots: list[dict] = []
    total_pop_covered = 0
    total_pop_uncovered = 0
    regions_covered = 0
    regions_uncovered = 0

    for rkey, rmeta in REGION_METADATA.items():
        rlat = rmeta.get("lat", 0)
        rlng = rmeta.get("lng", 0)
        pop = rmeta.get("population", 0)

        nearest_km = float("inf")
        for flat, flng, _ in service_facilities:
            d = _haversine_km(rlat, rlng, flat, flng)
            if d < nearest_km:
                nearest_km = d

        if nearest_km > radius_km:
            cold_spots.append({
                "region": rkey,
                "display_name": rmeta.get("display_name", rkey),
                "population": pop,
                "nearest_facility_km": round(nearest_km, 1) if nearest_km < float("inf") else None,
                "severity_score": round(pop / 100000 * (nearest_km / radius_km), 2) if nearest_km < float("inf") else round(pop / 100000 * 5, 2),
            })
            total_pop_uncovered += pop
            regions_uncovered += 1
        else:
            total_pop_covered += pop
            regions_covered += 1

    cold_spots.sort(key=lambda x: x["severity_score"], reverse=True)

    return {
        "cold_spots": cold_spots,
        "coverage_summary": {
            "regions_covered": regions_covered,
            "regions_uncovered": regions_uncovered,
            "population_covered": total_pop_covered,
            "population_uncovered": total_pop_uncovered,
        },
    }


# 9. analyze_ngo_coverage
def analyze_ngo_coverage(G: nx.MultiDiGraph) -> dict[str, Any]:
    """Analyze NGO coverage gaps and overlaps across regions."""
    # Build region → NGO mapping
    region_ngos: dict[str, list[str]] = {}
    ngo_names: dict[str, str] = {}

    for source, target, edata in G.edges(data=True):
        if edata.get("edge_type") != EDGE_OPERATES_IN:
            continue
        ngo_data = G.nodes.get(source, {})
        rkey = _extract_key(target)
        region_ngos.setdefault(rkey, []).append(source)
        ngo_names[source] = ngo_data.get("name", "Unknown")

    # Build region desert counts for "need" metric
    region_deserts: dict[str, int] = {}
    for source, _, edata in G.edges(data=True):
        if edata.get("edge_type") == EDGE_DESERT_FOR:
            rkey = _extract_key(source)
            region_deserts[rkey] = region_deserts.get(rkey, 0) + 1

    gaps: list[dict] = []
    overlaps: list[dict] = []

    for rkey, rmeta in REGION_METADATA.items():
        ngos = region_ngos.get(rkey, [])
        desert_count = region_deserts.get(rkey, 0)
        pop = rmeta.get("population", 0)

        if desert_count >= 2 and len(ngos) == 0:
            gaps.append({
                "region": rkey,
                "display_name": rmeta.get("display_name", rkey),
                "population": pop,
                "desert_count": desert_count,
                "ngo_count": 0,
                "need_score": round(desert_count * pop / 1_000_000, 2),
            })

        if len(ngos) >= 2:
            overlaps.append({
                "region": rkey,
                "display_name": rmeta.get("display_name", rkey),
                "ngo_count": len(ngos),
                "ngos": [ngo_names.get(n, "Unknown") for n in ngos],
                "desert_count": desert_count,
            })

    gaps.sort(key=lambda x: x["need_score"], reverse=True)
    overlaps.sort(key=lambda x: x["ngo_count"], reverse=True)

    return {
        "gaps": gaps,
        "overlaps": overlaps,
        "summary": {
            "regions_with_ngos": len([r for r in REGION_METADATA if region_ngos.get(r)]),
            "regions_without_ngos": len([r for r in REGION_METADATA if not region_ngos.get(r)]),
            "total_ngos": len(ngo_names),
        },
    }


# 10. compute_equipment_compliance
def compute_equipment_compliance(
    G: nx.MultiDiGraph,
    capability: str | None = None,
    region: str | None = None,
) -> dict[str, Any]:
    """For each capability (or a specific one), compute % of facilities
    claiming it that have the required equipment."""
    caps_to_check = [capability] if capability else list(CAPABILITY_REQUIREMENTS.keys())
    results: list[dict] = []

    for cap_key in caps_to_check:
        reqs = CAPABILITY_REQUIREMENTS.get(cap_key)
        if not reqs:
            continue
        required_equip = reqs.get("required", [])
        if not required_equip:
            continue

        cid = capability_id(cap_key)
        claiming_facilities = 0
        fully_compliant = 0
        partial_compliant = 0
        non_compliant = 0

        for source, target, edata in G.edges(data=True):
            if edata.get("edge_type") != EDGE_HAS_CAPABILITY or target != cid:
                continue
            fdata = G.nodes.get(source, {})
            if fdata.get("node_type") != NODE_FACILITY:
                continue
            if region and fdata.get("region") != region:
                continue

            claiming_facilities += 1

            # Check equipment
            fac_equip = set()
            for _, t2, ed2 in G.edges(source, data=True):
                if ed2.get("edge_type") == EDGE_HAS_EQUIPMENT:
                    fac_equip.add(_extract_key(t2))

            has_count = len(set(required_equip) & fac_equip)
            if has_count == len(required_equip):
                fully_compliant += 1
            elif has_count > 0:
                partial_compliant += 1
            else:
                non_compliant += 1

        if claiming_facilities > 0:
            results.append({
                "capability": cap_key,
                "claiming_facilities": claiming_facilities,
                "fully_compliant": fully_compliant,
                "partially_compliant": partial_compliant,
                "non_compliant": non_compliant,
                "compliance_rate": round(fully_compliant / claiming_facilities * 100, 1),
                "required_equipment": required_equip,
            })

    results.sort(key=lambda x: x["compliance_rate"])

    return {
        "results": results,
        "summary": f"Checked {len(results)} capabilities across facilities" + (f" in {region}" if region else ""),
    }
