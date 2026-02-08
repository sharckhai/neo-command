"""Exploration tools: region overview, facility browsing, equipment requirements."""

from __future__ import annotations

import json

import networkx as nx
from agents import function_tool

from graph.queries import (
    list_regions,
    get_region_details,
    get_facilities_in_region,
    get_capability_requirements,
    get_specialty_capabilities,
)


def make_explore_tools(G: nx.MultiDiGraph) -> list:
    """Create exploration tools bound to the given graph instance."""

    @function_tool
    def explore_regions() -> str:
        """List all 16 regions of Ghana with population, facility count, and desert count.

        Use as an entry point to understand the healthcare landscape.
        No parameters needed.
        """
        try:
            result = list_regions(G)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @function_tool
    def explore_region(region_key: str) -> str:
        """Deep-dive into a specific region: facilities, specialties, deserts, NGOs, neighbours.

        Args:
            region_key: Canonical region key. One of: greater_accra, ashanti, western,
                western_north, central, eastern, volta, oti, northern, savannah,
                north_east, upper_east, upper_west, bono, bono_east, ahafo.
        """
        try:
            result = get_region_details(G, region_key)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @function_tool
    def explore_facilities(
        region_key: str,
        specialty_key: str | None = None,
        limit: int = 50,
    ) -> str:
        """List facilities in a region, optionally filtered by specialty.

        Args:
            region_key: Canonical region key (e.g. "northern", "greater_accra").
            specialty_key: Optional specialty filter (e.g. "ophthalmology", "surgery").
            limit: Max results to return (default 50).
        """
        try:
            result = get_facilities_in_region(G, region_key, specialty_key, limit)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @function_tool
    def get_equipment_requirements(capability_key: str) -> str:
        """Get required and recommended equipment for a medical capability.

        Use for gap analysis: compare what a facility HAS vs. what it NEEDS.

        Args:
            capability_key: Canonical capability key (e.g. "cataract_surgery",
                "cesarean_section", "general_surgery", "dialysis").
        """
        try:
            result = get_capability_requirements(capability_key)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @function_tool
    def get_specialty_overview(specialty_key: str) -> str:
        """Which capabilities do facilities of a specialty have, with counts and percentages.

        Bridges the specialty-to-capability relationship for analysis.

        Args:
            specialty_key: Canonical specialty key (e.g. "ophthalmology",
                "gynecologyAndObstetrics", "surgery", "dentistry").
        """
        try:
            result = get_specialty_capabilities(G, specialty_key)
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    return [
        explore_regions,
        explore_region,
        explore_facilities,
        get_equipment_requirements,
        get_specialty_overview,
    ]
