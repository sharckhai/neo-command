"""Context tools: get_region_context for external data enrichment."""

from __future__ import annotations

import json

import networkx as nx
from agents import function_tool

from graph.config.ghana import REGION_METADATA, REGION_ADJACENCY
from graph.config.load_health_indicators import load_all_indicators, load_who_health_systems
from graph.config.travel_factors import REGION_TRAVEL_FACTORS
from graph.schema import (
    EDGE_LOCATED_IN,
    EDGE_HAS_CAPABILITY,
    EDGE_HAS_SPECIALTY,
    NODE_FACILITY,
    region_id,
)

# Cache loaded indicators (loaded once per process)
_indicators_cache: dict | None = None
_who_cache: dict | None = None


def _get_indicators() -> dict[str, dict]:
    global _indicators_cache
    if _indicators_cache is None:
        _indicators_cache = load_all_indicators()
    return _indicators_cache


def _get_who() -> dict[str, float]:
    global _who_cache
    if _who_cache is None:
        _who_cache = load_who_health_systems()
    return _who_cache


def _count_facilities_in_region(G: nx.MultiDiGraph, region: str) -> int:
    """Count facilities located in a region."""
    rid = region_id(region)
    if rid not in G:
        return 0
    count = 0
    for src, dst, data in G.in_edges(rid, data=True):
        if data.get("edge_type") == EDGE_LOCATED_IN:
            if G.nodes[src].get("node_type") == NODE_FACILITY:
                count += 1
    return count


def _count_facilities_with_capability_in_region(
    G: nx.MultiDiGraph, region: str, capability_or_specialty: str
) -> int:
    """Count facilities in a region that have a given capability or specialty."""
    rid = region_id(region)
    if rid not in G:
        return 0

    # Collect facility IDs in this region
    facilities_in_region = set()
    for src, dst, data in G.in_edges(rid, data=True):
        if data.get("edge_type") == EDGE_LOCATED_IN:
            if G.nodes[src].get("node_type") == NODE_FACILITY:
                facilities_in_region.add(src)

    # Check which have the capability/specialty
    count = 0
    for fid in facilities_in_region:
        for _, dst, data in G.out_edges(fid, data=True):
            etype = data.get("edge_type")
            if etype in (EDGE_HAS_CAPABILITY, EDGE_HAS_SPECIALTY):
                # dst is like "capability::cataract_surgery" or "specialty::ophthalmology"
                key = dst.split("::", 1)[-1] if "::" in dst else dst
                if key == capability_or_specialty:
                    count += 1
                    break
    return count


def _find_nearest_region_with_capability(
    G: nx.MultiDiGraph, region: str, capability_or_specialty: str
) -> str | None:
    """BFS over REGION_ADJACENCY to find the nearest region with the capability."""
    from collections import deque

    visited = {region}
    queue = deque(REGION_ADJACENCY.get(region, []))
    for r in queue:
        visited.add(r)

    while queue:
        candidate = queue.popleft()
        if _count_facilities_with_capability_in_region(G, candidate, capability_or_specialty) > 0:
            return candidate
        for neighbor in REGION_ADJACENCY.get(candidate, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
    return None


def _compute_equity_ranking(G: nx.MultiDiGraph) -> list[dict]:
    """Rank all 16 regions by healthcare equity (lower = more underserved).

    Score combines: population per facility, child mortality, anemia,
    insurance gaps, and access classification.
    """
    indicators = _get_indicators()
    rankings = []

    for region, meta in REGION_METADATA.items():
        pop = meta["population"]
        fac_count = _count_facilities_in_region(G, region)
        pop_per_facility = pop / max(fac_count, 1)

        ind = indicators.get(region, {})
        travel = REGION_TRAVEL_FACTORS.get(region, {})

        # Composite need score (higher = more underserved)
        # Normalize each component to roughly 0-100 scale
        score = 0.0
        score += min(pop_per_facility / 200, 100)  # pop/facility, capped
        score += ind.get("infant_mortality", 30)  # deaths per 1000
        score += ind.get("child_anemia_pct", 40)  # % children anemic
        score += ind.get("no_insurance_women_pct", 10) * 2  # % uninsured
        score += (100 - ind.get("facility_delivery_pct", 80))  # % NOT delivering in facility
        score += (travel.get("travel_multiplier", 1.5) - 1.0) * 40  # access penalty

        rankings.append({
            "region": region,
            "display_name": meta["display_name"],
            "equity_score": round(score, 1),
            "population": pop,
            "facility_count": fac_count,
            "pop_per_facility": round(pop_per_facility),
        })

    rankings.sort(key=lambda x: x["equity_score"], reverse=True)
    for i, r in enumerate(rankings, 1):
        r["rank"] = i  # 1 = most underserved
    return rankings


def make_context_tools(G: nx.MultiDiGraph) -> list:
    """Create context enrichment tools bound to the given graph instance."""

    @function_tool
    def get_region_context(
        region: str,
        specialty: str | None = None,
    ) -> str:
        """Get population, health indicators, and facility density for a region.
        Call this before making resource allocation or deployment recommendations.

        Returns population data, DHS health indicators (2022), facility density,
        travel access classification, and equity ranking across all 16 regions.

        Args:
            region: Canonical region key (e.g. "northern", "greater_accra").
            specialty: Optional canonical specialty or capability key.
                If provided, adds provider count, population-per-provider,
                and nearest alternative region for that service.
        """
        region = region.strip().lower().replace(" ", "_")

        meta = REGION_METADATA.get(region)
        if not meta:
            return json.dumps({
                "error": f"Unknown region: {region}",
                "valid_regions": sorted(REGION_METADATA.keys()),
            })

        indicators = _get_indicators().get(region, {})
        travel = REGION_TRAVEL_FACTORS.get(region, {})
        who = _get_who()

        fac_count = _count_facilities_in_region(G, region)
        pop = meta["population"]

        result = {
            "region": region,
            "display_name": meta["display_name"],
            "population": pop,
            "capital": meta["capital"],
            "facility_count": fac_count,
            "population_per_facility": round(pop / max(fac_count, 1)),
            "access": {
                "classification": travel.get("classification", "unknown"),
                "travel_multiplier": travel.get("travel_multiplier", 1.5),
                "road_quality": travel.get("avg_road_quality", "unknown"),
                "notes": travel.get("notes", ""),
            },
            "health_indicators": {
                "source": "Ghana DHS 2022",
                "infant_mortality_per_1000": indicators.get("infant_mortality"),
                "neonatal_mortality_per_1000": indicators.get("neonatal_mortality"),
                "under5_mortality_per_1000": indicators.get("under5_mortality"),
                "child_anemia_pct": indicators.get("child_anemia_pct"),
                "women_anemia_pct": indicators.get("women_anemia_pct"),
                "fully_vaccinated_pct": indicators.get("fully_vaccinated_pct"),
                "dpt3_coverage_pct": indicators.get("dpt3_pct"),
                "measles_coverage_pct": indicators.get("measles_pct"),
                "no_insurance_women_pct": indicators.get("no_insurance_women_pct"),
                "no_insurance_men_pct": indicators.get("no_insurance_men_pct"),
                "total_fertility_rate": indicators.get("total_fertility_rate"),
                "cesarean_delivery_pct": indicators.get("cesarean_pct"),
                "facility_delivery_pct": indicators.get("facility_delivery_pct"),
                "skilled_antenatal_pct": indicators.get("skilled_antenatal_pct"),
                "skilled_delivery_pct": indicators.get("skilled_delivery_pct"),
            },
            "who_national": {
                "hospital_beds_per_10k": who.get("Hospital beds (per 10 000 population)"),
            },
        }

        # Specialty-specific context
        if specialty:
            spec_count = _count_facilities_with_capability_in_region(G, region, specialty)
            nearest_alt = None
            if spec_count == 0:
                nearest_alt = _find_nearest_region_with_capability(G, region, specialty)

            result["specialty_context"] = {
                "specialty": specialty,
                "providers_in_region": spec_count,
                "population_per_provider": round(pop / max(spec_count, 1)) if spec_count > 0 else None,
                "nearest_alternative_region": nearest_alt,
            }

        # Equity ranking
        equity = _compute_equity_ranking(G)
        this_rank = next((r for r in equity if r["region"] == region), None)
        result["equity"] = {
            "rank": this_rank["rank"] if this_rank else None,
            "score": this_rank["equity_score"] if this_rank else None,
            "total_regions": 16,
            "interpretation": "1 = most underserved, 16 = best served",
            "top_5_underserved": [
                {"region": r["display_name"], "rank": r["rank"], "score": r["equity_score"]}
                for r in equity[:5]
            ],
        }

        return json.dumps(result, default=str)

    return [get_region_context]
