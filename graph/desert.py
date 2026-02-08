"""Compute DESERT_FOR edges: regions lacking facilities for a given specialty.

A region is a "desert" for specialty S if it has fewer than `min_facilities`
facilities with HAS_SPECIALTY(confidence ≥ threshold) for S.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import networkx as nx

from graph.schema import (
    NODE_FACILITY, NODE_REGION, NODE_SPECIALTY,
    EDGE_HAS_SPECIALTY, EDGE_LOCATED_IN, EDGE_DESERT_FOR,
    region_id, specialty_id,
)


def _find_nearest_with_service(
    region_key: str,
    regions_with_service: set[str],
    adjacency: dict[str, list[str]],
) -> str | None:
    """BFS to find nearest region that has a given specialty."""
    if region_key in regions_with_service:
        return region_key

    visited = {region_key}
    queue = list(adjacency.get(region_key, []))

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        if current in regions_with_service:
            return current

        for neighbor in adjacency.get(current, []):
            if neighbor not in visited:
                queue.append(neighbor)

    return None


def add_desert_edges(
    G: nx.MultiDiGraph,
    country_config: Any,
    *,
    min_facilities: int = 1,
    confidence_threshold: float = 0.5,
) -> int:
    """Add DESERT_FOR edges for (region, specialty) pairs lacking coverage.

    Args:
        G: The knowledge graph.
        country_config: Country config with REGION_METADATA and REGION_ADJACENCY.
        min_facilities: Minimum facilities needed to NOT be a desert.
        confidence_threshold: Minimum confidence on HAS_SPECIALTY edge.

    Returns:
        Number of DESERT_FOR edges added.
    """
    # Build a mapping: region_key → {specialty_key → count}
    region_specialty_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    # Find all facilities and their regions
    for fid, fdata in G.nodes(data=True):
        if fdata.get("node_type") != NODE_FACILITY:
            continue

        # Get this facility's region
        fac_region = fdata.get("region")
        if not fac_region:
            continue

        # Get specialties with sufficient confidence
        for _, target, edata in G.edges(fid, data=True):
            if edata.get("edge_type") != EDGE_HAS_SPECIALTY:
                continue
            if edata.get("confidence", 0) < confidence_threshold:
                continue
            # Extract specialty key from node ID
            if target.startswith("specialty::"):
                spec_key = target.split("::", 1)[1]
                region_specialty_counts[fac_region][spec_key] += 1

    # Collect all specialties in the graph
    all_specialties = set()
    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") == NODE_SPECIALTY:
            all_specialties.add(nid.split("::", 1)[1])

    # For each (region, specialty) pair, check if it's a desert
    count = 0
    adjacency = getattr(country_config, "REGION_ADJACENCY", {})
    region_meta = getattr(country_config, "REGION_METADATA", {})

    for region_key in region_meta:
        rid = region_id(region_key)
        if not G.has_node(rid):
            continue

        population = region_meta[region_key].get("population", 0)

        for spec_key in all_specialties:
            facility_count = region_specialty_counts.get(region_key, {}).get(spec_key, 0)

            if facility_count >= min_facilities:
                continue

            # Find regions that DO have this specialty
            regions_with = {
                r for r, specs in region_specialty_counts.items()
                if specs.get(spec_key, 0) >= min_facilities
            }

            nearest = _find_nearest_with_service(region_key, regions_with, adjacency)

            # Severity: population per facility (higher = worse)
            severity = population / (facility_count + 1)

            sid = specialty_id(spec_key)
            if not G.has_node(sid):
                continue

            G.add_edge(
                rid, sid,
                edge_type=EDGE_DESERT_FOR,
                facility_count=facility_count,
                population=population,
                nearest_region_with_service=nearest,
                severity=round(severity, 1),
            )
            count += 1

    return count
