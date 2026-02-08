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


def find_nearest_facilities(
    G: nx.MultiDiGraph,
    lat: float,
    lng: float,
    capability_key: str | None = None,
    specialty_key: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Find facilities nearest to a point, optionally filtered by capability or specialty.

    Uses haversine distance. Returns list sorted by distance_km ascending.
    """
    cid = capability_id(capability_key) if capability_key else None
    sid = specialty_id(specialty_key) if specialty_key else None

    results = []

    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue
        flat = ndata.get("lat")
        flng = ndata.get("lng")
        if flat is None or flng is None:
            continue

        # Filter by capability
        if cid:
            has_cap = any(
                edata.get("edge_type") == EDGE_HAS_CAPABILITY and target == cid
                for _, target, edata in G.edges(nid, data=True)
            )
            if not has_cap:
                continue

        # Filter by specialty
        if sid:
            has_spec = any(
                edata.get("edge_type") == EDGE_HAS_SPECIALTY and target == sid
                for _, target, edata in G.edges(nid, data=True)
            )
            if not has_spec:
                continue

        dist = _haversine_km(lat, lng, flat, flng)
        results.append({
            "facility_id": nid,
            "facility_name": ndata.get("name", "Unknown"),
            "region": ndata.get("region"),
            "city": ndata.get("city"),
            "lat": flat,
            "lng": flng,
            "distance_km": round(dist, 2),
        })

    results.sort(key=lambda x: x["distance_km"])
    return results[:limit]


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


def get_facilities_in_region(
    G: nx.MultiDiGraph,
    region_key: str,
    specialty_key: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """List facilities in a region, optionally filtered by specialty.

    Args:
        region_key: Canonical region key (e.g. "northern").
        specialty_key: Optional specialty to filter by (e.g. "ophthalmology").
        limit: Max results to return (default 50).
    """
    sid = specialty_id(specialty_key) if specialty_key else None
    results = []

    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_FACILITY:
            continue
        if ndata.get("region") != region_key:
            continue

        if sid:
            has_spec = any(
                edata.get("edge_type") == EDGE_HAS_SPECIALTY
                and target == sid
                and edata.get("confidence", 0) >= 0.5
                for _, target, edata in G.edges(nid, data=True)
            )
            if not has_spec:
                continue

        # Gather capabilities for this facility
        capabilities = []
        for _, target, edata in G.edges(nid, data=True):
            if edata.get("edge_type") == EDGE_HAS_CAPABILITY:
                ckey = target.split("::", 1)[1] if "::" in target else target
                capabilities.append(ckey)

        results.append({
            "facility_id": nid,
            "name": ndata.get("name", "Unknown"),
            "city": ndata.get("city"),
            "facility_type": ndata.get("facility_type"),
            "capabilities": capabilities,
        })

    results.sort(key=lambda x: len(x["capabilities"]), reverse=True)
    return results[:limit]


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
