"""Vocabulary guard tool: resolve_terms."""

from __future__ import annotations

import json

import networkx as nx
from agents import function_tool

from graph.normalize import (
    CANONICAL_CAPABILITIES,
    CANONICAL_EQUIPMENT,
    match_capabilities,
    match_equipment,
)
from graph.schema import NODE_SPECIALTY


def _build_specialty_index(G: nx.MultiDiGraph) -> dict[str, str]:
    """Build a lowercase-term -> specialty_key lookup from graph specialty nodes."""
    import re

    index: dict[str, str] = {}
    for nid, ndata in G.nodes(data=True):
        if ndata.get("node_type") != NODE_SPECIALTY:
            continue
        key = nid.split("::", 1)[1] if "::" in nid else nid
        index[key.lower()] = key
        words = re.sub(r"([a-z])([A-Z])", r"\1 \2", key).lower()
        index[words] = key
        display = ndata.get("display_name")
        if display:
            index[display.lower()] = key
    return index


def _match_specialty(term: str, specialty_index: dict[str, str]) -> tuple[str, float] | None:
    term_lower = term.lower().strip()
    if term_lower in specialty_index:
        return specialty_index[term_lower], 0.9
    for indexed_term, key in specialty_index.items():
        if term_lower in indexed_term or indexed_term in term_lower:
            return key, 0.7
    return None


def make_resolve_tools(G: nx.MultiDiGraph) -> list:
    """Create vocabulary resolution tools."""
    specialty_index = _build_specialty_index(G)

    @function_tool
    def resolve_terms(
        terms: list[str],
        show_all_vocabulary: bool = False,
        domain: str | None = None,
    ) -> str:
        """Map user's natural-language medical terms to canonical graph keys.

        ALWAYS call this first on medical terms from the user's query.
        Determines whether to use graph queries, raw text search, or both.

        Args:
            terms: Medical terms extracted from the user's query.
            show_all_vocabulary: If True, include the full list of canonical
                terms for the relevant domain(s). Useful for reformulating queries.
            domain: Optional filter — "capabilities", "equipment", or "specialties".
                If omitted, searches all domains.
        """
        mapped: list[dict] = []
        unmapped: list[str] = []

        for term in terms:
            cap_matches = match_capabilities(term) if domain in (None, "capabilities") else []
            eq_matches = match_equipment(term) if domain in (None, "equipment") else []
            spec_match = _match_specialty(term, specialty_index) if domain in (None, "specialties") else None

            if cap_matches or eq_matches or spec_match:
                for key, conf in cap_matches:
                    mapped.append({
                        "term": term, "key": key,
                        "confidence": conf, "domain": "capabilities",
                    })
                for key, conf in eq_matches:
                    mapped.append({
                        "term": term, "key": key,
                        "confidence": conf, "domain": "equipment",
                    })
                if spec_match:
                    mapped.append({
                        "term": term, "key": spec_match[0],
                        "confidence": spec_match[1], "domain": "specialties",
                    })
            else:
                unmapped.append(term)

        total = len(terms)
        mapped_term_count = total - len(unmapped)
        coverage_ratio = mapped_term_count / total if total > 0 else 0.0

        # Determine retrieval strategy
        if coverage_ratio >= 0.7:
            strategy = "graph"
        elif coverage_ratio <= 0.2:
            strategy = "raw_text"
        else:
            strategy = "mixed"

        result: dict = {
            "mapped": mapped,
            "unmapped": unmapped,
            "coverage_ratio": round(coverage_ratio, 2),
            "strategy": strategy,
        }

        if show_all_vocabulary:
            vocab: dict = {}
            if domain in (None, "capabilities"):
                vocab["capabilities"] = [
                    {"key": k, "display": v["display"], "category": v.get("category", "")}
                    for k, v in CANONICAL_CAPABILITIES.items()
                ]
            if domain in (None, "equipment"):
                vocab["equipment"] = [
                    {"key": k, "display": v["display"], "category": v.get("category", "")}
                    for k, v in CANONICAL_EQUIPMENT.items()
                ]
            if domain in (None, "specialties"):
                vocab["specialties"] = [
                    {"key": v, "term": k}
                    for k, v in specialty_index.items()
                ]
            result["vocabulary"] = vocab

        return json.dumps(result)

    return [resolve_terms]
