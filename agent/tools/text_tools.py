"""Raw text search tools: search_raw_text, get_facility_raw_text."""

from __future__ import annotations

import json
from typing import Any

import networkx as nx
from agents import function_tool

from graph.schema import NODE_FACILITY

_RAW_TEXT_FIELDS = ["raw_procedures", "raw_capabilities", "raw_equipment", "description"]


def make_text_tools(G: nx.MultiDiGraph) -> list:
    """Create text search tools bound to the given graph instance."""

    @function_tool
    def search_raw_text(terms: list[str], fields: list[str] | None = None, region: str | None = None) -> str:
        """Case-insensitive substring search across facility raw text fields.

        Use this when query terms fall outside the graph's canonical vocabulary
        (check_vocabulary_coverage returned low coverage_ratio).

        Args:
            terms: Search terms to look for in facility text.
            fields: Which fields to search. Defaults to all raw text fields:
                raw_procedures, raw_capabilities, raw_equipment, description.
            region: Optional region key to filter results (e.g. "northern").
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

                # Handle both list and string fields
                texts = raw if isinstance(raw, list) else [raw]

                for text in texts:
                    if not text:
                        continue
                    text_lower = text.lower()
                    for term in lower_terms:
                        if term in text_lower:
                            matched_fields.setdefault(field, []).append(text)
                            break  # one match per text item is enough

            if matched_fields:
                results.append({
                    "facility_id": nid,
                    "name": ndata.get("name", "Unknown"),
                    "region": ndata.get("region"),
                    "city": ndata.get("city"),
                    "matched_fields": matched_fields,
                })

        # Cap results to avoid massive payloads
        if len(results) > 50:
            results = results[:50]
            return json.dumps({
                "results": results,
                "truncated": True,
                "total_matches": len(results),
                "note": "Results truncated to 50. Add a region filter to narrow down.",
            })

        return json.dumps({"results": results, "total_matches": len(results)})

    @function_tool
    def get_facility_raw_text(facility_id: str) -> str:
        """Get all raw text fields for a specific facility. Use for cross-validation.

        Args:
            facility_id: The facility node ID (e.g. "facility::123").
        """
        if not G.has_node(facility_id):
            return json.dumps({"error": f"Facility {facility_id} not found"})

        ndata = G.nodes[facility_id]
        if ndata.get("node_type") != NODE_FACILITY:
            return json.dumps({"error": f"{facility_id} is not a facility node"})

        result = {
            "facility_id": facility_id,
            "name": ndata.get("name", "Unknown"),
            "region": ndata.get("region"),
            "city": ndata.get("city"),
            "raw_procedures": ndata.get("raw_procedures", []),
            "raw_capabilities": ndata.get("raw_capabilities", []),
            "raw_equipment": ndata.get("raw_equipment", []),
            "description": ndata.get("description", ""),
        }
        return json.dumps(result, default=str)

    return [search_raw_text, get_facility_raw_text]
