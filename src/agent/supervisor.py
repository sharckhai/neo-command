"""Supervisor agent: delegates to Explorer, FactAgent, Verifier sub-agents."""
from __future__ import annotations

from pathlib import Path

from agents import Agent, Runner, function_tool

from agent.explorer import create_explorer
from agent.fact_agent import create_fact_agent
from agent.verifier import create_verifier

_PROMPTS = Path(__file__).resolve().parent.parent.parent / "prompts"


def create_supervisor(G) -> Agent:
    """Create the Supervisor agent with agent-as-tool wrappers."""
    explorer = create_explorer(G)
    fact_agent = create_fact_agent(G)
    verifier = create_verifier(G)

    # --- Agent-as-tool wrappers ---

    @function_tool
    async def ask_explorer(query: str) -> str:
        """Ask the Explorer about healthcare landscape, distributions,
        gaps, deserts, cold spots, or NGO coverage."""
        result = await Runner.run(explorer, query)
        return result.final_output

    @function_tool
    async def ask_fact_agent(query: str) -> str:
        """Ask the FactAgent for facility details: lookups by name,
        multi-criteria searches, equipment checks, geospatial queries."""
        result = await Runner.run(fact_agent, query)
        return result.final_output

    @function_tool
    async def ask_verifier(query: str) -> str:
        """Ask the Verifier to assess data quality: anomaly detection,
        claim validation, equipment compliance checks."""
        result = await Runner.run(verifier, query)
        return result.final_output

    # --- Debate tools ---

    @function_tool
    async def run_facility_debate(facility_data_json: str) -> str:
        """Run an Advocate/Skeptic debate to verify a facility's capability claims.

        Call this after getting facility data from ask_fact_agent or ask_verifier
        to get a balanced credibility assessment with confidence score.

        Args:
            facility_data_json: JSON string with keys:
                - facility_name: str
                - claimed_capabilities: list[str]
                - confirmed_equipment: list[str]
                - missing_equipment: list[str]
                - raw_text: str (facility description)
                - source_count: int
        """
        from server.services.debate import debate_facility_tool_fn
        return await debate_facility_tool_fn(facility_data_json)

    @function_tool
    async def run_mission_debate(constraints_and_data_json: str) -> str:
        """Run a three-advocate debate to compare deployment options for a
        medical mission. Each advocate argues for a different region.

        Call this after gathering gap and facility data from ask_explorer
        and ask_fact_agent to get a structured comparison with
        Coverage/Readiness/Equity scores.

        Args:
            constraints_and_data_json: JSON string with keys:
                - user_constraints: str (e.g. "2 ophthalmologists, 10 days")
                - candidate_regions: list[dict] each with keys:
                    region, facilities, deserts, population, facility_count
        """
        from server.services.mission_planner import plan_mission_tool_fn
        return await plan_mission_tool_fn(constraints_and_data_json)

    # --- Build Supervisor ---

    return Agent(
        name="Supervisor",
        instructions=(_PROMPTS / "supervisor.md").read_text(),
        tools=[
            ask_explorer,
            ask_fact_agent,
            ask_verifier,
            run_facility_debate,
            run_mission_debate,
        ],
        model="gpt-5.2",
    )
