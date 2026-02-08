from __future__ import annotations

from typing import Dict, List, Tuple


def rank_regions_by_facility_density(region_counts: Dict[str, int]) -> List[Tuple[str, int]]:
    return sorted(region_counts.items(), key=lambda item: item[1])


def build_plan_summary(region_counts: Dict[str, int], limit: int = 3) -> str:
    ranked = rank_regions_by_facility_density(region_counts)
    top = ranked[:limit]
    if not top:
        return "No region data available for planning."
    parts = [f"{region} ({count} facilities)" for region, count in top]
    return "Top underserved regions by facility count: " + ", ".join(parts) + "."
