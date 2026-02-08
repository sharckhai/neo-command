"""Compute LACKS and COULD_SUPPORT edges from the base graph.

LACKS: Facility claims a capability but is missing required equipment.
COULD_SUPPORT: Facility doesn't claim a capability but has ≥60% of required equipment.
"""

from __future__ import annotations

import networkx as nx

from graph.schema import (
    NODE_FACILITY, NODE_EQUIPMENT, NODE_CAPABILITY,
    EDGE_HAS_CAPABILITY, EDGE_HAS_EQUIPMENT, EDGE_LACKS, EDGE_COULD_SUPPORT,
    equipment_id, capability_id,
)
from graph.medical_requirements import CAPABILITY_REQUIREMENTS


def _get_facility_equipment(G: nx.MultiDiGraph, fid: str) -> set[str]:
    """Get set of canonical equipment keys that a facility has."""
    equipment = set()
    for _, target, data in G.edges(fid, data=True):
        if data.get("edge_type") == EDGE_HAS_EQUIPMENT:
            # Extract canonical key from node ID "equipment::key"
            if target.startswith("equipment::"):
                equipment.add(target.split("::", 1)[1])
    return equipment


def _get_facility_capabilities(G: nx.MultiDiGraph, fid: str) -> set[str]:
    """Get set of canonical capability keys that a facility claims."""
    capabilities = set()
    for _, target, data in G.edges(fid, data=True):
        if data.get("edge_type") == EDGE_HAS_CAPABILITY:
            if target.startswith("capability::"):
                capabilities.add(target.split("::", 1)[1])
    return capabilities


def add_lacks_edges(G: nx.MultiDiGraph) -> int:
    """Add LACKS edges for facilities missing required equipment for claimed capabilities.

    For each facility:
      For each capability it claims (HAS_CAPABILITY):
        Look up CAPABILITY_REQUIREMENTS[capability].required
        For each required equipment not in the facility's HAS_EQUIPMENT set:
          Add a LACKS edge.

    Returns the number of LACKS edges added.
    """
    count = 0
    facility_nodes = [
        n for n, d in G.nodes(data=True)
        if d.get("node_type") == NODE_FACILITY
    ]

    for fid in facility_nodes:
        owned_equipment = _get_facility_equipment(G, fid)
        claimed_capabilities = _get_facility_capabilities(G, fid)

        for cap_key in claimed_capabilities:
            reqs = CAPABILITY_REQUIREMENTS.get(cap_key)
            if not reqs:
                continue

            for req_equip in reqs.get("required", []):
                if req_equip not in owned_equipment:
                    eid = equipment_id(req_equip)
                    # Ensure equipment node exists
                    if not G.has_node(eid):
                        continue

                    # Check if LACKS edge already exists
                    existing = False
                    for _, t, d in G.edges(fid, data=True):
                        if t == eid and d.get("edge_type") == EDGE_LACKS:
                            # Update: add this capability to the required_by list
                            d.setdefault("required_by", [])
                            if cap_key not in d["required_by"]:
                                d["required_by"].append(cap_key)
                            existing = True
                            break

                    if not existing:
                        G.add_edge(
                            fid, eid,
                            edge_type=EDGE_LACKS,
                            reason=f"Required for {cap_key} but no evidence found",
                            required_by=[cap_key],
                            evidence_status="no_evidence",
                        )
                        count += 1

    return count


def add_could_support_edges(G: nx.MultiDiGraph, min_readiness: float = 0.6) -> int:
    """Add COULD_SUPPORT edges for capabilities a facility could potentially offer.

    For each facility:
      For each capability NOT already claimed:
        If the facility has ≥60% of required equipment:
          Add a COULD_SUPPORT edge with readiness_score.

    Returns the number of COULD_SUPPORT edges added.
    """
    count = 0
    facility_nodes = [
        n for n, d in G.nodes(data=True)
        if d.get("node_type") == NODE_FACILITY
    ]

    for fid in facility_nodes:
        owned_equipment = _get_facility_equipment(G, fid)
        claimed_capabilities = _get_facility_capabilities(G, fid)

        if not owned_equipment:
            continue

        for cap_key, reqs in CAPABILITY_REQUIREMENTS.items():
            if cap_key in claimed_capabilities:
                continue

            required = reqs.get("required", [])
            if not required:
                continue

            # Calculate readiness
            has_required = [eq for eq in required if eq in owned_equipment]
            readiness = len(has_required) / len(required)

            if readiness >= min_readiness:
                missing = [eq for eq in required if eq not in owned_equipment]
                cid = capability_id(cap_key)

                if not G.has_node(cid):
                    continue

                G.add_edge(
                    fid, cid,
                    edge_type=EDGE_COULD_SUPPORT,
                    existing_equipment=has_required,
                    missing_equipment=missing,
                    readiness_score=round(readiness, 2),
                )
                count += 1

    return count
