"""Inspection tools: inspect_facility, get_requirements, find_lacks."""

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

    @function_tool
    def find_lacks(
        capability: str,
        facility_ids: list[str] | None = None,
        region: str | None = None,
    ) -> str:
        """Find facilities that LACK required equipment for a claimed capability.

        Queries the pre-computed LACKS edges in the graph. Each LACKS edge means
        the facility claims a capability but has no evidence of a required piece
        of equipment. Returns per-facility: missing equipment list, the
        HAS_CAPABILITY confidence and raw_text that produced the claim, and
        total equipment the facility does have.

        Use this to quickly separate false NLP mappings (low confidence +
        vague raw_text + lacks everything) from real gaps (high confidence +
        specific raw_text + lacks some items).

        Args:
            capability: Canonical capability key (e.g. "general_surgery").
            facility_ids: Optional list of facility IDs to check. If omitted,
                searches all facilities with LACKS edges for this capability.
            region: Optional region filter (e.g. "Northern").
        """
        # Collect LACKS edges for this capability
        lacks_by_fac: dict[str, list[str]] = {}
        for src, tgt, edata in G.edges(data=True):
            if edata.get("edge_type") != "LACKS":
                continue
            if capability not in edata.get("required_by", []):
                continue
            if facility_ids and src not in facility_ids:
                continue
            if region:
                fac_region = G.nodes[src].get("region") or ""
                if fac_region.lower() != region.lower():
                    continue
            equip = tgt.split("::", 1)[1] if "::" in tgt else tgt
            lacks_by_fac.setdefault(src, []).append(equip)

        results = []
        for fid, missing in lacks_by_fac.items():
            ndata = G.nodes[fid]

            # Get the HAS_CAPABILITY edge(s) for this capability
            cap_node = f"capability::{capability}"
            claim_edges = []
            for _, t, ed in G.edges(fid, data=True):
                if ed.get("edge_type") == "HAS_CAPABILITY" and t == cap_node:
                    claim_edges.append({
                        "confidence": ed.get("confidence"),
                        "source_field": ed.get("source_field"),
                        "raw_text": ed.get("raw_text", ""),
                    })

            # Count total equipment the facility has
            equip_count = sum(
                1 for _, _, ed in G.edges(fid, data=True)
                if ed.get("edge_type") == "HAS_EQUIPMENT"
            )

            results.append({
                "facility_id": fid,
                "name": ndata.get("name", "Unknown"),
                "region": ndata.get("region"),
                "facility_type": ndata.get("facility_type"),
                "missing_equipment": sorted(missing),
                "missing_count": len(missing),
                "total_equipment_count": equip_count,
                "capability_claims": claim_edges,
            })

        results.sort(key=lambda r: r["missing_count"], reverse=True)

        return json.dumps({
            "capability": capability,
            "facilities_lacking": len(results),
            "results": results,
        }, default=str)

    return [inspect_facility, get_requirements, find_lacks]
