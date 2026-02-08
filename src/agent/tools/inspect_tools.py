"""Inspection tools: inspect_facility, get_requirements."""

from __future__ import annotations

import json

import networkx as nx
from agents import function_tool

from graph.queries import get_facility_details, get_facility_mismatches, get_capability_requirements
from graph.schema import NODE_FACILITY


_RAW_TEXT_FIELDS = ["raw_procedures", "raw_capabilities", "raw_equipment", "description"]


def make_inspect_tools(G: nx.MultiDiGraph) -> list:
    """Create inspection tools bound to the given graph instance."""

    @function_tool
    def inspect_facility(
        facility_ids: str | list[str],
        include_raw_text: bool = True,
        include_gap_analysis: bool = True,
    ) -> str:
        """Deep-dive into one or more facilities in a single call.

        Returns a JSON list — one object per facility — with all graph edges,
        raw text, and equipment gap analysis.

        Args:
            facility_ids: One facility ID or a list of IDs (e.g. "facility::123"
                or ["facility::43", "facility::121", "facility::373"]).
            include_raw_text: Include raw text fields for cross-validation (default True).
            include_gap_analysis: Include LACKS edges and mismatch ratio (default True).
        """
        ids = [facility_ids] if isinstance(facility_ids, str) else list(facility_ids)
        results = []

        for fid in ids:
            if not G.has_node(fid):
                results.append({"facility_id": fid, "error": f"Facility {fid} not found"})
                continue

            ndata = G.nodes[fid]
            if ndata.get("node_type") != NODE_FACILITY:
                results.append({"facility_id": fid, "error": f"{fid} is not a facility node"})
                continue

            details = get_facility_details(G, fid)
            if "error" in details:
                results.append({"facility_id": fid, **details})
                continue

            result = {
                "facility_id": fid,
                "name": details.get("name", "Unknown"),
                "region": details.get("region"),
                "city": details.get("city"),
                "facility_type": details.get("facility_type"),
                "capacity": details.get("capacity"),
                "number_doctors": details.get("number_doctors"),
                "lat": details.get("lat"),
                "lng": details.get("lng"),
                "specialties": details.get("specialties", []),
                "capabilities": details.get("capabilities", []),
                "equipment": details.get("equipment", []),
                "could_support": details.get("could_support", []),
            }

            if include_gap_analysis:
                mismatches = get_facility_mismatches(G, fid)
                result["lacks"] = mismatches.get("lacks", [])
                result["mismatch_ratio"] = mismatches.get("mismatch_ratio", 0)
            else:
                result["lacks"] = details.get("lacks", [])

            if include_raw_text:
                result["raw_text"] = {}
                for field in _RAW_TEXT_FIELDS:
                    val = ndata.get(field)
                    if val:
                        result["raw_text"][field] = val

            results.append(result)

        return json.dumps(results, default=str)

    @function_tool
    def get_requirements(
        capability: str,
        facility_ids: str | list[str] | None = None,
    ) -> str:
        """Look up required/recommended equipment for a capability,
        optionally comparing against one or more facilities.

        Args:
            capability: Canonical capability key (e.g. "cataract_surgery",
                "cesarean_section", "dialysis").
            facility_ids: Optional — one facility ID or a list of IDs to compare.
                Returns compliance score and present/missing equipment per facility.
        """
        reqs = get_capability_requirements(capability)
        if "error" in reqs:
            return json.dumps(reqs)

        result = dict(reqs)

        if facility_ids:
            ids = [facility_ids] if isinstance(facility_ids, str) else list(facility_ids)
            comparisons = []

            for fid in ids:
                if not G.has_node(fid):
                    comparisons.append({"facility_id": fid, "error": f"Facility {fid} not found"})
                    continue

                fac_equip = set()
                for _, target, edata in G.edges(fid, data=True):
                    if edata.get("edge_type") == "HAS_EQUIPMENT":
                        key = target.split("::", 1)[1] if "::" in target else target
                        fac_equip.add(key)

                required = set(reqs.get("required", []))
                has_required = required & fac_equip
                missing_required = required - fac_equip
                compliance = len(has_required) / len(required) if required else 1.0

                comparisons.append({
                    "facility_id": fid,
                    "has_required": sorted(has_required),
                    "missing_required": sorted(missing_required),
                    "compliance_score": round(compliance, 3),
                })

            if len(comparisons) == 1:
                result["facility_comparison"] = comparisons[0]
            else:
                result["facility_comparisons"] = comparisons

        return json.dumps(result, default=str)

    return [inspect_facility, get_requirements]
