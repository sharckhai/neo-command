"""Vocabulary coverage tool: check_vocabulary_coverage."""

from __future__ import annotations

import json

from agents import function_tool

from graph.normalize import match_capabilities, match_equipment


def make_vocab_tools() -> list:
    """Create vocabulary tools (no graph dependency)."""

    @function_tool
    def check_vocabulary_coverage(terms: list[str]) -> str:
        """Check how well query terms map to the graph's canonical vocabulary.

        ALWAYS call this first on medical terms from the user's query.
        If coverage_ratio < 0.3, skip graph queries and use search_raw_text instead.

        Args:
            terms: Medical terms extracted from the user's query.
        """
        mapped: list[dict] = []
        unmapped: list[str] = []

        for term in terms:
            cap_matches = match_capabilities(term)
            eq_matches = match_equipment(term)

            if cap_matches or eq_matches:
                # Take the best match from either domain
                best_matches = []
                for key, conf in cap_matches:
                    best_matches.append({
                        "term": term,
                        "key": key,
                        "confidence": conf,
                        "domain": "capabilities",
                    })
                for key, conf in eq_matches:
                    best_matches.append({
                        "term": term,
                        "key": key,
                        "confidence": conf,
                        "domain": "equipment",
                    })
                mapped.extend(best_matches)
            else:
                unmapped.append(term)

        total = len(terms)
        mapped_term_count = total - len(unmapped)
        coverage_ratio = mapped_term_count / total if total > 0 else 0.0

        return json.dumps({
            "mapped": mapped,
            "unmapped": unmapped,
            "coverage_ratio": round(coverage_ratio, 2),
        })

    return [check_vocabulary_coverage]
