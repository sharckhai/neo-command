"""Search tools: find_facility, search_facilities, count_facilities, search_raw_text."""

from __future__ import annotations

import json
from typing import Any

import networkx as nx
from agents import function_tool

from graph.queries import (
    fuzzy_find_facility,
    search_facilities_multi,
    count_and_group_facilities,
)
from graph.schema import NODE_FACILITY

_RAW_TEXT_FIELDS = ["raw_procedures", "raw_capabilities", "raw_equipment", "description"]


def make_search_tools(G: nx.MultiDiGraph) -> list:
    """Create search tools bound to the given graph instance."""

    @function_tool
    def find_facility(name: str, region: str | None = None, limit: int = 5) -> str:
        """Fuzzy-match a facility name to graph facility IDs.

        Essential bridge between natural language and graph node IDs.
        Use when the user mentions a facility by name (e.g. "Korle Bu",
        "Tamale Teaching Hospital").

        Args:
            name: User-provided facility name to search for.
            region: Optional region key to narrow the search.
            limit: Max results to return (default 5).
        """
        try:
            result = fuzzy_find_facility(G, name, region, limit)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @function_tool
    def search_facilities(
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
    ) -> str:
        """Universal multi-criteria facility search with optional geospatial radius.

        Finds facilities matching ANY COMBINATION of filters. At least one
        filter should be provided.

        Args:
            capability: Canonical capability key (e.g. "cataract_surgery").
            equipment: Canonical equipment key (e.g. "ultrasound").
            specialty: Canonical specialty key (e.g. "ophthalmology").
            region: Region key (e.g. "northern", "greater_accra").
            facility_type: Facility type filter (substring match).
            min_capacity: Minimum bed/capacity count.
            near_lat: Latitude for geospatial search.
            near_lng: Longitude for geospatial search.
            radius_km: Maximum distance in km (requires near_lat/near_lng).
            limit: Max results (default 25).
            sort_by: "relevance" (default), "distance", or "capacity".
        """
        try:
            result = search_facilities_multi(
                G,
                capability=capability, equipment=equipment,
                specialty=specialty, region=region,
                facility_type=facility_type, min_capacity=min_capacity,
                near_lat=near_lat, near_lng=near_lng, radius_km=radius_km,
                limit=limit, sort_by=sort_by,
            )
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @function_tool
    def count_facilities(
        group_by: str,
        capability: str | None = None,
        equipment: str | None = None,
        specialty: str | None = None,
        region: str | None = None,
        min_confidence: float = 0.5,
    ) -> str:
        """Count facilities grouped by a dimension, with optional filters.

        Returns distributions with counts and percentages. Essential for
        "how many" questions and distribution analysis.

        Args:
            group_by: Dimension to group by. One of: "region", "specialty",
                "capability", "facility_type", "equipment".
            capability: Filter to facilities with this capability.
            equipment: Filter to facilities with this equipment.
            specialty: Filter to facilities with this specialty.
            region: Filter to facilities in this region.
            min_confidence: Minimum edge confidence (default 0.5).
        """
        try:
            result = count_and_group_facilities(
                G, group_by,
                capability=capability, equipment=equipment,
                specialty=specialty, region=region,
                min_confidence=min_confidence,
            )
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @function_tool
    def search_raw_text(
        terms: list[str],
        fields: list[str] | None = None,
        region: str | None = None,
        limit: int = 50,
    ) -> str:
        """Case-insensitive substring search across facility raw text fields.

        Use when query terms fall outside the graph's canonical vocabulary
        (resolve_terms returned low coverage_ratio or strategy="raw_text").

        Args:
            terms: Search terms to look for in facility text.
            fields: Which fields to search. Defaults to all:
                raw_procedures, raw_capabilities, raw_equipment, description.
            region: Optional region key to filter results.
            limit: Max results (default 50).
        """
        search_fields = fields or _RAW_TEXT_FIELDS
        lower_terms = [t.lower() for t in terms]
        results: list[dict[str, Any]] = []

        for nid, ndata in G.nodes(data=True):
            if ndata.get("node_type") != NODE_FACILITY:
                continue
            if region and ndata.get("region") != region:
                continue

            matched_fields: dict[str, list[str]] = {}

            for field in search_fields:
                raw = ndata.get(field)
                if raw is None:
                    continue
                texts = raw if isinstance(raw, list) else [raw]
                for text in texts:
                    if not text:
                        continue
                    text_lower = text.lower()
                    for term in lower_terms:
                        if term in text_lower:
                            matched_fields.setdefault(field, []).append(text)
                            break

            if matched_fields:
                results.append({
                    "facility_id": nid,
                    "name": ndata.get("name", "Unknown"),
                    "region": ndata.get("region"),
                    "city": ndata.get("city"),
                    "matched_fields": matched_fields,
                })

        truncated = len(results) > limit
        results = results[:limit]

        output: dict = {"results": results, "total_matches": len(results)}
        if truncated:
            output["truncated"] = True
            output["note"] = f"Results truncated to {limit}. Add a region filter to narrow down."

        return json.dumps(output)

    return [find_facility, search_facilities, count_facilities, search_raw_text]
