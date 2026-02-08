"""Anomaly detection tool: detect_anomalies."""

from __future__ import annotations

import json

import networkx as nx
from agents import function_tool

from graph.queries import (
    detect_procedure_size_anomalies,
    detect_equipment_claim_anomalies,
    detect_feature_correlations,
    detect_bed_or_anomalies,
)


def make_anomaly_tools(G: nx.MultiDiGraph) -> list:
    """Create anomaly detection tools bound to the given graph instance."""

    @function_tool
    def detect_anomalies(
        check_type: str,
        region: str | None = None,
        threshold: float | None = None,
        limit: int = 20,
    ) -> str:
        """Flag facilities with suspicious patterns for data quality review.

        Args:
            check_type: Type of anomaly check. One of:
                - "procedure_vs_size": Facilities claiming many high-complexity
                    procedures relative to their bed capacity.
                - "equipment_vs_claims": Facilities claiming many capabilities
                    but lacking required equipment (high LACKS ratio).
                - "feature_correlation": Expected equipment not present for
                    claimed capabilities (e.g. surgery without operating theatre).
                - "bed_or_ratio": Unusual bed-to-surgical-capability ratios.
            region: Optional region filter.
            threshold: Sensitivity threshold (0.0–1.0). Lower = more sensitive.
                Defaults vary by check_type.
            limit: Max flagged facilities to return (default 20).
        """
        try:
            if check_type == "procedure_vs_size":
                t = threshold if threshold is not None else 0.6
                flagged = detect_procedure_size_anomalies(G, region=region, threshold=t, limit=limit)

            elif check_type == "equipment_vs_claims":
                t = threshold if threshold is not None else 0.4
                flagged = detect_equipment_claim_anomalies(G, region=region, threshold=t, limit=limit)

            elif check_type == "feature_correlation":
                flagged = detect_feature_correlations(G, region=region, limit=limit)

            elif check_type == "bed_or_ratio":
                flagged = detect_bed_or_anomalies(G, region=region, limit=limit)

            else:
                return json.dumps({
                    "error": f"Unknown check_type: {check_type}",
                    "valid_types": [
                        "procedure_vs_size", "equipment_vs_claims",
                        "feature_correlation", "bed_or_ratio",
                    ],
                })

            summary = f"Found {len(flagged)} flagged facilities"
            if region:
                summary += f" in {region}"

            return json.dumps({
                "check_type": check_type,
                "flagged_facilities": flagged,
                "summary": summary,
            }, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    return [detect_anomalies]
