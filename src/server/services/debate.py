"""Advocate/Skeptic debate for facility claim verification."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field, asdict
from typing import Optional

from openai import AsyncOpenAI

from server.config import settings


@dataclass
class DebateResult:
    facility_name: str
    advocate_summary: str
    skeptic_summary: str
    confidence: int  # 0-100
    verdict: str  # "verified" | "plausible" | "suspicious" | "likely_false"
    flags: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)

    def to_display(self) -> str:
        """Format for chat display."""
        lines = [
            f"**{self.facility_name}** — Confidence: {self.confidence}/100 ({self.verdict})",
            "",
            f"**Advocate:** {self.advocate_summary}",
            "",
            f"**Skeptic:** {self.skeptic_summary}",
        ]
        if self.flags:
            lines.append("")
            lines.append(f"**Flags:** {', '.join(self.flags)}")
        return "\n".join(lines)


ADVOCATE_SYSTEM = """You are an advocate arguing that a healthcare facility's capability claims are CREDIBLE.

Given the facility's data, find every reason to believe their claims:
- Supporting equipment that partially validates capabilities
- Visiting specialist programs that could explain capabilities without permanent staff
- Corroboration from multiple sources increases credibility
- Consider that facilities in Ghana may have capabilities not fully documented
- Acknowledge partial capability (e.g., basic surgery even without full OR suite)

Be specific. Reference actual data. Keep to ~100 words."""

SKEPTIC_SYSTEM = """You are a skeptic arguing that a healthcare facility's capability claims are SUSPICIOUS.

Given the facility's data, find every reason to doubt their claims:
- Missing prerequisite equipment for claimed procedures
- Single-source claims (especially Facebook-only) are unreliable
- Referral language ("we refer patients for...") ≠ actual capability
- Aspirational language ("we plan to offer...") ≠ current capability
- Procedure count vs bed capacity mismatch (e.g., 47 procedures, 12 beds)
- High-complexity claims from low-infrastructure facilities

Be specific. Reference actual data. Keep to ~100 words."""

JUDGE_SYSTEM = """You are an impartial judge evaluating a healthcare facility's capability claims.

You will receive:
1. The facility's data (capabilities, equipment, sources)
2. An advocate's argument (why claims are credible)
3. A skeptic's argument (why claims are suspicious)

Produce a JSON verdict:
{
    "confidence": <0-100 integer>,
    "verdict": "<verified|plausible|suspicious|likely_false>",
    "flags": ["<specific issues>"],
    "reasoning": "<1-2 sentence summary>"
}

Scoring guide:
- 80-100 (verified): Strong equipment evidence, multiple sources, claims consistent with facility type
- 50-79 (plausible): Some supporting evidence but gaps exist
- 25-49 (suspicious): Significant mismatches, single source, missing prerequisites
- 0-24 (likely_false): Claims contradicted by evidence, extreme mismatches"""


def _build_facility_prompt(
    facility_name: str,
    claimed_capabilities: list[str],
    confirmed_equipment: list[str],
    missing_equipment: list[str],
    raw_text: str,
    source_count: int,
) -> str:
    return f"""Facility: {facility_name}
Source count: {source_count}
Claimed capabilities: {', '.join(claimed_capabilities) if claimed_capabilities else 'none listed'}
Confirmed equipment: {', '.join(confirmed_equipment) if confirmed_equipment else 'none listed'}
Missing expected equipment: {', '.join(missing_equipment) if missing_equipment else 'none'}
Raw description: {raw_text[:500] if raw_text else 'none'}"""


async def run_advocate_skeptic(
    facility_name: str,
    claimed_capabilities: list[str],
    confirmed_equipment: list[str],
    missing_equipment: list[str],
    raw_text: str = "",
    source_count: int = 1,
) -> DebateResult:
    """Run advocate/skeptic debate for a single facility.

    Falls back to heuristic-only if no API key.
    """
    if not settings.openai_api_key:
        return _heuristic_fallback(
            facility_name, claimed_capabilities, confirmed_equipment,
            missing_equipment, raw_text, source_count,
        )

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    facility_prompt = _build_facility_prompt(
        facility_name, claimed_capabilities, confirmed_equipment,
        missing_equipment, raw_text, source_count,
    )

    # Run advocate and skeptic in parallel
    advocate_task = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": ADVOCATE_SYSTEM},
            {"role": "user", "content": facility_prompt},
        ],
        temperature=0.3,
        max_tokens=200,
    )
    skeptic_task = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SKEPTIC_SYSTEM},
            {"role": "user", "content": facility_prompt},
        ],
        temperature=0.3,
        max_tokens=200,
    )

    advocate_resp, skeptic_resp = await asyncio.gather(advocate_task, skeptic_task)
    advocate_text = advocate_resp.choices[0].message.content or ""
    skeptic_text = skeptic_resp.choices[0].message.content or ""

    # Judge synthesis
    judge_prompt = f"""{facility_prompt}

ADVOCATE ARGUMENT:
{advocate_text}

SKEPTIC ARGUMENT:
{skeptic_text}"""

    judge_resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": judge_prompt},
        ],
        temperature=0.1,
        max_tokens=200,
        response_format={"type": "json_object"},
    )

    judge_text = judge_resp.choices[0].message.content or "{}"
    try:
        judge_data = json.loads(judge_text)
    except json.JSONDecodeError:
        judge_data = {}

    return DebateResult(
        facility_name=facility_name,
        advocate_summary=advocate_text,
        skeptic_summary=skeptic_text,
        confidence=judge_data.get("confidence", 50),
        verdict=judge_data.get("verdict", "plausible"),
        flags=judge_data.get("flags", []),
        evidence={
            "claimed_capabilities": claimed_capabilities,
            "confirmed_equipment": confirmed_equipment,
            "missing_equipment": missing_equipment,
            "source_count": source_count,
        },
    )


def _heuristic_fallback(
    facility_name: str,
    claimed_capabilities: list[str],
    confirmed_equipment: list[str],
    missing_equipment: list[str],
    raw_text: str,
    source_count: int,
) -> DebateResult:
    """Rules-based verification when no LLM is available."""
    flags = []
    confidence = 70  # start at neutral-positive

    # Missing equipment penalty
    if missing_equipment:
        penalty = min(len(missing_equipment) * 10, 40)
        confidence -= penalty
        flags.append("missing_equipment")

    # Single source penalty
    if source_count <= 1:
        confidence -= 15
        flags.append("single_source")

    # Breadth-depth mismatch
    if len(claimed_capabilities) >= 6 and len(confirmed_equipment) <= 2:
        confidence -= 20
        flags.append("breadth_depth_mismatch")

    # Referral/aspirational language
    referral_words = ["refer", "referral", "transfer"]
    aspirational_words = ["plan to", "aim to", "future", "upcoming"]
    text_lower = raw_text.lower()
    if any(w in text_lower for w in referral_words):
        confidence -= 10
        flags.append("referral_language")
    if any(w in text_lower for w in aspirational_words):
        confidence -= 10
        flags.append("aspirational_language")

    confidence = max(0, min(100, confidence))

    if confidence >= 80:
        verdict = "verified"
    elif confidence >= 50:
        verdict = "plausible"
    elif confidence >= 25:
        verdict = "suspicious"
    else:
        verdict = "likely_false"

    return DebateResult(
        facility_name=facility_name,
        advocate_summary="(Heuristic mode — no LLM available for debate)",
        skeptic_summary="(Heuristic mode — no LLM available for debate)",
        confidence=confidence,
        verdict=verdict,
        flags=flags,
        evidence={
            "claimed_capabilities": claimed_capabilities,
            "confirmed_equipment": confirmed_equipment,
            "missing_equipment": missing_equipment,
            "source_count": source_count,
        },
    )


async def debate_facility_tool_fn(facility_data_json: str) -> str:
    """Wrapper for use as an Agents SDK function_tool.

    Expects JSON with keys: facility_name, claimed_capabilities, confirmed_equipment,
    missing_equipment, raw_text, source_count.
    """
    data = json.loads(facility_data_json)
    result = await run_advocate_skeptic(
        facility_name=data.get("facility_name", "Unknown"),
        claimed_capabilities=data.get("claimed_capabilities", []),
        confirmed_equipment=data.get("confirmed_equipment", []),
        missing_equipment=data.get("missing_equipment", []),
        raw_text=data.get("raw_text", ""),
        source_count=data.get("source_count", 1),
    )
    return json.dumps(asdict(result))
