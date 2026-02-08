"""Gap analysis tools: find_gaps, find_cold_spots."""

from __future__ import annotations

import json

import networkx as nx
from agents import function_tool

from graph.queries import (
    get_deserts_for_specialty,
    get_facilities_that_could_support,
    analyze_ngo_coverage,
    compute_equipment_compliance,
    find_geographic_cold_spots,
)


def make_gap_tools(G: nx.MultiDiGraph) -> list:
    """Create gap analysis tools bound to the given graph instance."""

    @function_tool
    def find_gaps(
        gap_type: str,
        specialty: str | None = None,
        capability: str | None = None,
        region: str | None = None,
        min_readiness: float = 0.6,
    ) -> str:
        """Discover what is MISSING — medical deserts, equipment compliance,
        upgrade-ready facilities, and NGO coverage gaps.

        This is the graph's unique value — information that raw text search
        CANNOT provide.

        Args:
            gap_type: Type of gap analysis. One of:
                - "deserts": Regions lacking a specialty, sorted by severity.
                    Requires specialty parameter.
                - "could_support": Facilities ready for capability upgrade.
                    Requires capability parameter.
                - "ngo_gaps": Regions with high need but no NGO presence,
                    plus overlap analysis. No extra params needed.
                - "equipment_compliance": Percentage of facilities claiming
                    a capability that have the required equipment.
                    Optional capability and region filters.
            specialty: Required for "deserts" gap_type. Canonical specialty key.
            capability: Required for "could_support". Optional for
                "equipment_compliance". Canonical capability key.
            region: Optional region filter for "equipment_compliance".
            min_readiness: Minimum readiness score for "could_support" (default 0.6).
        """
        try:
            if gap_type == "deserts":
                if not specialty:
                    return json.dumps({"error": "specialty parameter required for deserts gap_type"})
                result = get_deserts_for_specialty(G, specialty)
                return json.dumps({"gap_type": "deserts", "specialty": specialty, "results": result}, default=str)

            elif gap_type == "could_support":
                if not capability:
                    return json.dumps({"error": "capability parameter required for could_support gap_type"})
                result = get_facilities_that_could_support(G, capability)
                # Filter by readiness
                result = [r for r in result if r.get("readiness_score", 0) >= min_readiness]
                return json.dumps({
                    "gap_type": "could_support", "capability": capability,
                    "min_readiness": min_readiness, "results": result,
                }, default=str)

            elif gap_type == "ngo_gaps":
                result = analyze_ngo_coverage(G)
                return json.dumps({"gap_type": "ngo_gaps", **result}, default=str)

            elif gap_type == "equipment_compliance":
                result = compute_equipment_compliance(G, capability=capability, region=region)
                return json.dumps({"gap_type": "equipment_compliance", **result}, default=str)

            else:
                return json.dumps({
                    "error": f"Unknown gap_type: {gap_type}",
                    "valid_types": ["deserts", "could_support", "ngo_gaps", "equipment_compliance"],
                })
        except Exception as e:
            return json.dumps({"error": str(e)})

    @function_tool
    def find_cold_spots(
        capability: str | None = None,
        specialty: str | None = None,
        radius_km: float = 100.0,
        population_weighted: bool = True,
    ) -> str:
        """Identify regions where a capability/specialty is absent within a
        given radius. Essential for geographic coverage analysis.

        Args:
            capability: Canonical capability key (e.g. "cesarean_section").
                Provide either capability or specialty.
            specialty: Canonical specialty key (e.g. "ophthalmology").
                Provide either capability or specialty.
            radius_km: Maximum acceptable distance to a facility with the
                service (default 100 km).
            population_weighted: Sort by population-weighted severity
                (default True).
        """
        if not capability and not specialty:
            return json.dumps({"error": "Provide either capability or specialty parameter"})

        try:
            result = find_geographic_cold_spots(
                G,
                capability=capability,
                specialty=specialty,
                radius_km=radius_km,
            )
            if not population_weighted and "cold_spots" in result:
                result["cold_spots"].sort(
                    key=lambda x: x.get("nearest_facility_km") or 99999,
                    reverse=True,
                )
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)})

    return [find_gaps, find_cold_spots]
