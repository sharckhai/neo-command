"""Multi-agent debate for mission deployment planning."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field, asdict
from typing import Optional

from openai import AsyncOpenAI

from server.config import settings


@dataclass
class DeploymentOption:
    region: str
    facility_name: str | None = None
    coverage_score: float = 0.0   # 0-100 population impact
    readiness_score: float = 0.0  # 0-100 infrastructure quality
    equity_score: float = 0.0     # 0-100 underserved priority
    overall_score: float = 0.0    # weighted composite
    evidence: str = ""
    caveats: list[str] = field(default_factory=list)
    verification_steps: list[str] = field(default_factory=list)


@dataclass
class PlanBrief:
    options: list[DeploymentOption] = field(default_factory=list)
    recommendation: str = ""
    tradeoff_analysis: str = ""
    unknowns: list[str] = field(default_factory=list)

    def to_display(self) -> str:
        """Format for chat display."""
        lines = []
        for i, opt in enumerate(self.options, 1):
            lines.append(f"**Option {i}: {opt.region}**")
            if opt.facility_name:
                lines.append(f"  Base facility: {opt.facility_name}")
            lines.append(
                f"  Coverage: {opt.coverage_score:.0f}/100 | "
                f"Readiness: {opt.readiness_score:.0f}/100 | "
                f"Equity: {opt.equity_score:.0f}/100"
            )
            lines.append(f"  Overall: {opt.overall_score:.0f}/100")
            lines.append(f"  {opt.evidence[:200]}")
            if opt.caveats:
                lines.append(f"  Caveats: {'; '.join(opt.caveats)}")
            if opt.verification_steps:
                lines.append(f"  Verify: {'; '.join(opt.verification_steps)}")
            lines.append("")

        lines.append(f"**Recommendation:** {self.recommendation}")
        lines.append("")
        lines.append(f"**Tradeoffs:** {self.tradeoff_analysis}")
        if self.unknowns:
            lines.append("")
            lines.append(f"**Unknowns:** {'; '.join(self.unknowns)}")
        return "\n".join(lines)


ADVOCATE_SYSTEM = """You are a mission planning advocate arguing for deploying a medical team to a specific region in Ghana.

You will receive:
- The user's constraints (team composition, duration, specialty)
- Data about YOUR assigned region (facilities, capabilities, gaps, population)

Argue WHY this region should be the deployment target. Address:
1. COVERAGE: How many people would benefit? What's the population without access?
2. READINESS: What infrastructure exists? Can the team operate effectively?
3. EQUITY: How underserved is this region? Are other NGOs already covering it?

Be specific. Use data. Acknowledge weaknesses honestly but argue for your region.
Keep to ~150 words. Output JSON:
{
    "coverage_score": <0-100>,
    "readiness_score": <0-100>,
    "equity_score": <0-100>,
    "evidence": "<your argument>",
    "caveats": ["<honest limitations>"],
    "verification_steps": ["<what to check before committing>"],
    "recommended_facility": "<best base facility name or null>"
}"""


SYNTHESIS_SYSTEM = """You are a mission planning synthesis agent comparing three deployment options for an NGO medical team.

You will receive three advocate arguments for different regions. Produce a final recommendation.

Score weights: Coverage 40%, Readiness 30%, Equity 30%.

Output JSON:
{
    "recommendation": "<which region and why, 2-3 sentences>",
    "tradeoff_analysis": "<explicit comparison of the three options, 2-3 sentences>",
    "unknowns": ["<things we cannot determine from data>"],
    "ranking": [
        {"region": "<name>", "overall_score": <weighted 0-100>},
        {"region": "<name>", "overall_score": <weighted 0-100>},
        {"region": "<name>", "overall_score": <weighted 0-100>}
    ]
}"""


def _build_region_prompt(
    user_constraints: str,
    region: str,
    region_data: dict,
) -> str:
    """Build the prompt for one advocate."""
    facilities = region_data.get("facilities", [])
    deserts = region_data.get("deserts", [])
    population = region_data.get("population", "unknown")
    facility_count = region_data.get("facility_count", len(facilities))
    top_facilities = facilities[:5] if facilities else []

    fac_text = "\n".join([
        f"  - {f.get('name', '?')} "
        f"({f.get('facility_type', '?')}, capacity: {f.get('capacity', '?')})"
        for f in top_facilities
    ]) if top_facilities else "  (no detailed facility data)"

    desert_text = ", ".join(deserts) if deserts else "none identified"

    extra = {
        k: v
        for k, v in region_data.items()
        if k not in ("facilities", "deserts", "population", "facility_count")
    }

    return (
        f"User constraints: {user_constraints}\n\n"
        f"Region: {region}\n"
        f"Population: {population}\n"
        f"Facility count: {facility_count}\n"
        f"Top facilities:\n{fac_text}\n"
        f"Specialty deserts: {desert_text}\n"
        f"Additional data: {json.dumps(extra, default=str)[:500]}"
    )


async def run_plan_debate(
    user_constraints: str,
    candidate_regions: list[dict],
) -> PlanBrief:
    """Run three-advocate debate for mission deployment planning.

    Args:
        user_constraints: e.g. "2 ophthalmologists, 10 days"
        candidate_regions: list of dicts with keys: region, facilities,
            deserts, population, facility_count, ...
            Should be pre-sorted by need (highest need first). Top 3 are used.

    Falls back to heuristic ranking if no API key.
    """
    if not candidate_regions:
        return PlanBrief(recommendation="No candidate regions available for planning.")

    # Take top 3 candidates
    top3 = candidate_regions[:3]

    if not settings.openai_api_key:
        return _heuristic_fallback(user_constraints, top3)

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    # Run 3 advocates in parallel
    advocate_tasks = []
    for region_data in top3:
        region_name = region_data.get("region", "Unknown")
        prompt = _build_region_prompt(user_constraints, region_name, region_data)
        task = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": ADVOCATE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        advocate_tasks.append(task)

    advocate_responses = await asyncio.gather(*advocate_tasks)

    # Parse advocate results
    advocate_results = []
    for i, resp in enumerate(advocate_responses):
        text = resp.choices[0].message.content or "{}"
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {}
        region_name = top3[i].get("region", f"Region {i+1}")
        advocate_results.append({"region": region_name, **data})

    # Synthesis — combine all advocate arguments into one prompt
    synthesis_parts = [f"User constraints: {user_constraints}\n"]
    for idx, ar in enumerate(advocate_results, 1):
        synthesis_parts.append(
            f"ADVOCATE {idx} ({ar.get('region', '?')}):\n"
            f"{json.dumps(ar, indent=2)}\n"
        )
    synthesis_prompt = "\n".join(synthesis_parts)

    synth_resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYNTHESIS_SYSTEM},
            {"role": "user", "content": synthesis_prompt},
        ],
        temperature=0.1,
        max_tokens=400,
        response_format={"type": "json_object"},
    )

    synth_text = synth_resp.choices[0].message.content or "{}"
    try:
        synth_data = json.loads(synth_text)
    except json.JSONDecodeError:
        synth_data = {}

    # Build options from advocate results + synthesis ranking
    ranking = synth_data.get("ranking", [])
    ranking_scores = {r["region"]: r.get("overall_score", 50) for r in ranking}

    options = []
    for ar in advocate_results:
        region = ar.get("region", "Unknown")
        overall = ranking_scores.get(
            region,
            ar.get("coverage_score", 50) * 0.4
            + ar.get("readiness_score", 50) * 0.3
            + ar.get("equity_score", 50) * 0.3,
        )
        options.append(DeploymentOption(
            region=region,
            facility_name=ar.get("recommended_facility"),
            coverage_score=ar.get("coverage_score", 50),
            readiness_score=ar.get("readiness_score", 50),
            equity_score=ar.get("equity_score", 50),
            overall_score=overall,
            evidence=ar.get("evidence", ""),
            caveats=ar.get("caveats", []),
            verification_steps=ar.get("verification_steps", []),
        ))

    options.sort(key=lambda o: o.overall_score, reverse=True)

    return PlanBrief(
        options=options,
        recommendation=synth_data.get(
            "recommendation",
            f"Recommend {options[0].region} based on overall score."
            if options
            else "",
        ),
        tradeoff_analysis=synth_data.get("tradeoff_analysis", ""),
        unknowns=synth_data.get("unknowns", []),
    )


def _heuristic_fallback(
    user_constraints: str,
    candidates: list[dict],
) -> PlanBrief:
    """Simple ranking when no LLM is available."""
    options = []
    for i, c in enumerate(candidates):
        region = c.get("region", f"Region {i+1}")
        fac_count = c.get("facility_count", 0)
        desert_count = len(c.get("deserts", []))
        pop = c.get("population", 0)

        # Simple scoring
        if isinstance(pop, (int, float)) and pop > 0:
            coverage = min(100, (pop / 100_000) * 10)
        else:
            coverage = 50
        readiness = min(100, fac_count * 5) if fac_count else 20
        equity = min(100, desert_count * 20 + (100 - readiness) * 0.5)
        overall = coverage * 0.4 + readiness * 0.3 + equity * 0.3

        options.append(DeploymentOption(
            region=region,
            coverage_score=round(coverage, 1),
            readiness_score=round(readiness, 1),
            equity_score=round(equity, 1),
            overall_score=round(overall, 1),
            evidence=f"{region}: {fac_count} facilities, {desert_count} specialty deserts",
            caveats=["Heuristic scoring -- no LLM debate available"],
            verification_steps=["Verify facility infrastructure on-site"],
        ))

    options.sort(key=lambda o: o.overall_score, reverse=True)

    return PlanBrief(
        options=options,
        recommendation=(
            f"Recommend {options[0].region} (score: {options[0].overall_score:.0f}/100)"
            if options
            else "No data"
        ),
        tradeoff_analysis="Heuristic mode -- scores based on facility density and desert count only.",
        unknowns=[
            "Equipment readiness",
            "Actual population access patterns",
            "Road/transport conditions",
        ],
    )


async def plan_mission_tool_fn(constraints_and_data_json: str) -> str:
    """Wrapper for use as an Agents SDK function_tool.

    Expects JSON with keys: user_constraints, candidate_regions.
    """
    data = json.loads(constraints_and_data_json)
    result = await run_plan_debate(
        user_constraints=data.get("user_constraints", ""),
        candidate_regions=data.get("candidate_regions", []),
    )
    return json.dumps(asdict(result), default=str)
