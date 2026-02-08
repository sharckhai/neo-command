"""Graph-structured retrieval tools: query_graph, list_vocabulary, query_absence."""

from __future__ import annotations

import json
from typing import Any

import networkx as nx
from agents import function_tool

from graph.queries import (
    get_facility_details,
    get_facility_mismatches,
    find_suspicious_facilities,
    get_deserts_for_specialty,
    get_facilities_that_could_support,
    get_regional_comparison,
    search_facilities_by_capability,
    search_facilities_by_equipment,
    get_specialty_distribution,
    find_nearest_facilities,
    list_specialties,
    get_graph_summary,
)
from graph.normalize import CANONICAL_CAPABILITIES, CANONICAL_EQUIPMENT


_QUERY_DISPATCH = {
    "facility_details": lambda G, p: get_facility_details(G, p["fid"]),
    "facility_mismatches": lambda G, p: get_facility_mismatches(G, p["fid"]),
    "suspicious_facilities": lambda G, p: find_suspicious_facilities(G, p.get("min_ratio", 0.3)),
    "deserts_for_specialty": lambda G, p: get_deserts_for_specialty(G, p["specialty_key"]),
    "could_support": lambda G, p: get_facilities_that_could_support(G, p["capability_key"]),
    "regional_comparison": lambda G, p: get_regional_comparison(G, p["specialty_key"]),
    "facilities_by_capability": lambda G, p: search_facilities_by_capability(
        G, p["capability_key"], p.get("region"),
    ),
    "facilities_by_equipment": lambda G, p: search_facilities_by_equipment(
        G, p["equipment_key"], p.get("region"),
    ),
    "specialty_distribution": lambda G, p: get_specialty_distribution(G),
    "nearest_facilities": lambda G, p: find_nearest_facilities(
        G,
        p["lat"],
        p["lng"],
        capability_key=p.get("capability_key"),
        specialty_key=p.get("specialty_key"),
        limit=p.get("limit", 10),
    ),
    "list_specialties": lambda G, p: list_specialties(G),
    "graph_summary": lambda G, p: get_graph_summary(G),
}

_ABSENCE_DISPATCH = {
    "facility_lacks": lambda G, t: get_facility_mismatches(G, t),
    "region_deserts": lambda G, t: get_deserts_for_specialty(G, t),
    "could_support": lambda G, t: get_facilities_that_could_support(G, t),
}


def make_graph_tools(G: nx.MultiDiGraph) -> list:
    """Create graph tools bound to the given graph instance."""

    @function_tool
    def query_graph(query_type: str, params: str) -> str:
        """Run a structured query against the knowledge graph.

        Args:
            query_type: One of: facility_details, facility_mismatches,
                suspicious_facilities, deserts_for_specialty, could_support,
                regional_comparison, facilities_by_capability,
                facilities_by_equipment, specialty_distribution,
                nearest_facilities, list_specialties, graph_summary.
            params: JSON-encoded dict of parameters for the chosen query.
                See tool docs for required params per query_type.
        """
        handler = _QUERY_DISPATCH.get(query_type)
        if not handler:
            return json.dumps({
                "error": f"Unknown query_type: {query_type}",
                "valid_types": list(_QUERY_DISPATCH.keys()),
            })
        try:
            parsed_params = json.loads(params) if isinstance(params, str) else params
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON in params: {e}"})

        try:
            result = handler(G, parsed_params)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @function_tool
    def list_vocabulary(domain: str) -> str:
        """List the graph's canonical vocabulary for a domain.

        Args:
            domain: Either "capabilities" or "equipment".
        """
        if domain == "capabilities":
            source = CANONICAL_CAPABILITIES
        elif domain == "equipment":
            source = CANONICAL_EQUIPMENT
        else:
            return json.dumps({"error": f"Unknown domain: {domain}. Use 'capabilities' or 'equipment'."})

        items = []
        for key, meta in source.items():
            items.append({
                "key": key,
                "display": meta["display"],
                "category": meta.get("category", ""),
                "aliases": meta.get("aliases", []),
            })
        return json.dumps(items)

    @function_tool
    def query_absence(query_type: str, target: str) -> str:
        """Query what is MISSING — the graph's unique value over raw text.

        Args:
            query_type: One of: facility_lacks, region_deserts, could_support.
            target: The target identifier — facility_id for facility_lacks,
                specialty_key for region_deserts, capability_key for could_support.
        """
        handler = _ABSENCE_DISPATCH.get(query_type)
        if not handler:
            return json.dumps({
                "error": f"Unknown query_type: {query_type}",
                "valid_types": list(_ABSENCE_DISPATCH.keys()),
            })
        try:
            result = handler(G, target)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    return [query_graph, list_vocabulary, query_absence]
