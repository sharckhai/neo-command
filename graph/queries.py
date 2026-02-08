"""Runtime query functions for agents.

These functions power the VERIFY, PLAN, and EXPLORE modes of VirtueCommand.
They will be wrapped as LangGraph tools for agent tool-calling.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from graph.schema import (
    NODE_FACILITY, NODE_REGION, NODE_SPECIALTY, NODE_CAPABILITY, NODE_EQUIPMENT,
    EDGE_HAS_CAPABILITY, EDGE_HAS_EQUIPMENT, EDGE_HAS_SPECIALTY,
    EDGE_LACKS, EDGE_COULD_SUPPORT, EDGE_DESERT_FOR, EDGE_LOCATED_IN,
    facility_id, region_id, specialty_id, capability_id,
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


def find_suspicious_facilities(
    G: nx.MultiDiGraph,
    min_ratio: float = 0.3,
) -> list[dict[str, Any]]:
    """Find facilities with a high ratio of LACKS edges to total equipment links.

    Useful for batch scanning in VERIFY mode.
    """
    results = []

    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue

        info = get_facility_mismatches(G, nid)
        if info.get("mismatch_ratio", 0) >= min_ratio and info.get("lacks"):
            results.append(info)

    results.sort(key=lambda x: x["mismatch_ratio"], reverse=True)
    return results


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


def get_regional_comparison(G: nx.MultiDiGraph, specialty_key: str) -> list[dict[str, Any]]:
    """Compare all regions for a specialty. Returns all regions ranked by facility count."""
    sid = specialty_id(specialty_key)
    region_data: dict[str, dict] = {}

    # Initialize all regions
    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_REGION:
            continue
        region_key = nid.split("::", 1)[1] if "::" in nid else nid
        region_data[region_key] = {
            "region": region_key,
            "region_name": ndata.get("name", region_key),
            "population": ndata.get("population", 0),
            "facility_count": 0,
            "facilities": [],
            "is_desert": False,
        }

    # Count facilities per region with this specialty
    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue
        region = ndata.get("region")
        if not region or region not in region_data:
            continue

        has_specialty = False
        for _, target, edata in G.edges(nid, data=True):
            if edata.get("edge_type") == EDGE_HAS_SPECIALTY and target == sid:
                if edata.get("confidence", 0) >= 0.5:
                    has_specialty = True
                    break

        if has_specialty:
            region_data[region]["facility_count"] += 1
            region_data[region]["facilities"].append({
                "id": nid,
                "name": ndata.get("name", "Unknown"),
            })

    # Mark deserts
    for source, target, edata in G.edges(data=True):
        if edata.get("edge_type") == EDGE_DESERT_FOR and target == sid:
            region_key = source.split("::", 1)[1] if "::" in source else source
            if region_key in region_data:
                region_data[region_key]["is_desert"] = True

    results = list(region_data.values())
    results.sort(key=lambda x: x["facility_count"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# EXPLORE mode
# ---------------------------------------------------------------------------

def search_facilities_by_capability(
    G: nx.MultiDiGraph,
    capability_key: str,
    region: str | None = None,
) -> list[dict[str, Any]]:
    """Find all facilities with a given capability, optionally filtered by region."""
    cid = capability_id(capability_key)
    results = []

    for source, target, edata in G.edges(data=True):
        if edata.get("edge_type") != EDGE_HAS_CAPABILITY:
            continue
        if target != cid:
            continue

        fdata = G.nodes.get(source, {})
        if fdata.get("node_type") != NODE_FACILITY:
            continue

        fac_region = fdata.get("region")
        if region and fac_region != region:
            continue

        results.append({
            "facility_id": source,
            "facility_name": fdata.get("name", "Unknown"),
            "region": fac_region,
            "city": fdata.get("city"),
            "facility_type": fdata.get("facility_type"),
            "confidence": edata.get("confidence", 0),
            "source_field": edata.get("source_field"),
        })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def search_facilities_by_equipment(
    G: nx.MultiDiGraph,
    equipment_key: str,
    region: str | None = None,
) -> list[dict[str, Any]]:
    """Find all facilities with a given equipment, optionally filtered by region."""
    eid = equipment_id(equipment_key)
    results = []

    for source, target, edata in G.edges(data=True):
        if edata.get("edge_type") != EDGE_HAS_EQUIPMENT:
            continue
        if target != eid:
            continue

        fdata = G.nodes.get(source, {})
        if fdata.get("node_type") != NODE_FACILITY:
            continue

        fac_region = fdata.get("region")
        if region and fac_region != region:
            continue

        results.append({
            "facility_id": source,
            "facility_name": fdata.get("name", "Unknown"),
            "region": fac_region,
            "city": fdata.get("city"),
            "confidence": edata.get("confidence", 0),
        })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results


def get_specialty_distribution(G: nx.MultiDiGraph) -> dict[str, dict[str, int]]:
    """Get facility counts per specialty per region.

    Returns:
        {
            "ophthalmology": {"greater_accra": 5, "ashanti": 3, ...},
            "dentistry": {...},
            ...
        }
    """
    distribution: dict[str, dict[str, int]] = {}

    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue

        region = ndata.get("region")
        if not region:
            continue

        for _, target, edata in G.edges(nid, data=True):
            if edata.get("edge_type") != EDGE_HAS_SPECIALTY:
                continue
            if edata.get("confidence", 0) < 0.5:
                continue

            spec_key = target.split("::", 1)[1] if "::" in target else target
            if spec_key not in distribution:
                distribution[spec_key] = {}
            distribution[spec_key][region] = distribution[spec_key].get(region, 0) + 1

    return distribution


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
