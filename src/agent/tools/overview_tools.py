"""Overview tool: explore_overview."""

from __future__ import annotations

import json

import networkx as nx
from agents import function_tool

from graph.queries import (
    list_regions,
    get_region_details,
    get_specialty_capabilities,
    get_graph_summary,
    list_specialties,
)


def make_overview_tools(G: nx.MultiDiGraph) -> list:
    """Create overview/exploration tools bound to the given graph instance."""

    @function_tool
    def explore_overview(scope: str, key: str | None = None) -> str:
        """High-level landscape exploration: national overview, region
        deep-dive, or specialty breakdown.

        Args:
            scope: One of:
                - "national": Graph stats, all regions with population/facility/
                    desert counts, top specialties. No key needed.
                - "region": Deep-dive into a specific region: facilities,
                    specialty counts, deserts, NGOs, neighbours.
                    Requires key = region key (e.g. "northern").
                - "specialty": Capabilities, regional distribution, facility
                    count for a specialty.
                    Requires key = specialty key (e.g. "ophthalmology").
            key: Required for "region" and "specialty" scopes. The region key
                or specialty key to explore.
        """
        try:
            if scope == "national":
                summary = get_graph_summary(G)
                regions = list_regions(G)
                specialties = list_specialties(G)
                return json.dumps({
                    "scope": "national",
                    "graph_stats": summary,
                    "regions": regions,
                    "top_specialties": specialties[:15],
                }, default=str)

            elif scope == "region":
                if not key:
                    return json.dumps({"error": "key parameter required for region scope"})
                result = get_region_details(G, key)
                if "error" in result:
                    return json.dumps(result)
                return json.dumps({"scope": "region", **result}, default=str)

            elif scope == "specialty":
                if not key:
                    return json.dumps({"error": "key parameter required for specialty scope"})
                result = get_specialty_capabilities(G, key)
                if "error" in result:
                    return json.dumps(result)
                return json.dumps({"scope": "specialty", **result}, default=str)

            else:
                return json.dumps({
                    "error": f"Unknown scope: {scope}",
                    "valid_scopes": ["national", "region", "specialty"],
                })

        except Exception as e:
            return json.dumps({"error": str(e)})

    return [explore_overview]
