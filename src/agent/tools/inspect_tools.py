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
        facility_id: str,
        include_raw_text: bool = True,
        include_gap_analysis: bool = True,
    ) -> str:
        """Deep dive into a single facility: all graph edges, raw text,
        and equipment gap analysis in one call.

        Args:
            facility_id: The facility node ID (e.g. "facility::123").
            include_raw_text: Include raw text fields for cross-validation (default True).
            include_gap_analysis: Include LACKS edges and mismatch ratio (default True).
        """
        if not G.has_node(facility_id):
            return json.dumps({"error": f"Facility {facility_id} not found"})

        ndata = G.nodes[facility_id]
        if ndata.get("node_type") != NODE_FACILITY:
            return json.dumps({"error": f"{facility_id} is not a facility node"})

        # Get full structured details
        details = get_facility_details(G, facility_id)
        if "error" in details:
            return json.dumps(details)

        # Build response
        result = {
            "facility_id": facility_id,
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

        # Gap analysis
        if include_gap_analysis:
            mismatches = get_facility_mismatches(G, facility_id)
            result["lacks"] = mismatches.get("lacks", [])
            result["mismatch_ratio"] = mismatches.get("mismatch_ratio", 0)
        else:
            result["lacks"] = details.get("lacks", [])

        # Raw text
        if include_raw_text:
            result["raw_text"] = {}
            for field in _RAW_TEXT_FIELDS:
                val = ndata.get(field)
                if val:
                    result["raw_text"][field] = val

        return json.dumps(result, default=str)

    @function_tool
    def get_requirements(
        capability: str,
        facility_id: str | None = None,
    ) -> str:
        """Look up required/recommended equipment for a capability,
        optionally comparing against a specific facility.

        Args:
            capability: Canonical capability key (e.g. "cataract_surgery",
                "cesarean_section", "dialysis").
            facility_id: Optional facility ID to compare against. Returns
                compliance score and lists of present/missing equipment.
        """
        reqs = get_capability_requirements(capability)
        if "error" in reqs:
            return json.dumps(reqs)

        result = dict(reqs)

        if facility_id:
            if not G.has_node(facility_id):
                result["facility_comparison"] = {"error": f"Facility {facility_id} not found"}
            else:
                # Get facility equipment
                fac_equip = set()
                for _, target, edata in G.edges(facility_id, data=True):
                    if edata.get("edge_type") == "HAS_EQUIPMENT":
                        key = target.split("::", 1)[1] if "::" in target else target
                        fac_equip.add(key)

                required = set(reqs.get("required", []))
                has_required = required & fac_equip
                missing_required = required - fac_equip
                compliance = len(has_required) / len(required) if required else 1.0

                result["facility_comparison"] = {
                    "facility_id": facility_id,
                    "has_required": sorted(has_required),
                    "missing_required": sorted(missing_required),
                    "compliance_score": round(compliance, 3),
                }

        return json.dumps(result, default=str)

    return [inspect_facility, get_requirements]
