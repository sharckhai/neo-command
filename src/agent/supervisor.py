"""Supervisor agent: delegates to Analyst and Verifier sub-agents."""
from __future__ import annotations

from pathlib import Path

from agents import Agent, Runner, function_tool
from agents.stream_events import RunItemStreamEvent

from agent.analyst import create_analyst
from agent.planner import create_planner
from agent.rag_agent import create_rag_agent
from agent.verifier import create_verifier

_PROMPTS = Path(__file__).resolve().parent.parent.parent / "prompts"


def _print_sub_event(agent_name: str, event: RunItemStreamEvent) -> None:
    item = event.item
    item_type = item.type if hasattr(item, "type") else type(item).__name__
    prefix = f"  [{agent_name}]"
    if item_type == "tool_call_item":
        call = item.raw_item
        name = call.name if hasattr(call, "name") else "?"
        args = call.arguments if hasattr(call, "arguments") else ""
        args_display = args[:300] + "..." if len(str(args)) > 300 else args
        print(f"\n{prefix} >> {name}")
        print(f"{prefix}    args: {args_display}")
    elif item_type == "tool_call_output_item":
        output = item.output if hasattr(item, "output") else str(item)
        output_display = str(output)[:500] + "..." if len(str(output)) > 500 else output
        print(f"{prefix}    << {output_display}")


def create_supervisor(G) -> Agent:
    """Create the Supervisor agent with agent-as-tool wrappers."""
    analyst = create_analyst(G)
    planner = create_planner(G)
    verifier = create_verifier(G)
    rag_agent = create_rag_agent()

    # --- Agent-as-tool wrappers ---

    @function_tool
    async def ask_analyst(query: str) -> str:
        """Ask the Analyst for all data retrieval: overviews, gaps, deserts,
        facility lookups, searches, equipment checks, geospatial queries."""
        result = Runner.run_streamed(analyst, query)
        async for event in result.stream_events():
            if isinstance(event, RunItemStreamEvent):
                _print_sub_event("Analyst", event)
        return result.final_output

    @function_tool
    async def ask_verifier(query: str) -> str:
        """Ask the Verifier to assess data quality: anomaly detection,
        claim validation, equipment compliance checks."""
        result = Runner.run_streamed(verifier, query)
        async for event in result.stream_events():
            if isinstance(event, RunItemStreamEvent):
                _print_sub_event("Verifier", event)
        return result.final_output

    @function_tool
    async def ask_planner(analyst_findings_and_constraints: str) -> str:
        """Ask the Planner to create a resource allocation or deployment plan.

        Call this AFTER getting data from ask_analyst. Provide:
        - The Analyst's findings (deserts, cold spots, candidate facilities)
        - The user's constraints (team size, specialty, duration, budget)

        The Planner will enrich with population/health context and produce
        a scored deployment recommendation."""
        result = Runner.run_streamed(planner, analyst_findings_and_constraints)
        async for event in result.stream_events():
            if isinstance(event, RunItemStreamEvent):
                _print_sub_event("Planner", event)
        return result.final_output

    @function_tool
    async def ask_rag_agent(query: str) -> str:
        """Ask the RAG agent to search uploaded documents, ingest new files,
        or answer questions from document contents."""
        result = Runner.run_streamed(rag_agent, query)
        async for event in result.stream_events():
            if isinstance(event, RunItemStreamEvent):
                _print_sub_event("RAG", event)
        return result.final_output

    # --- Debate tools ---

    @function_tool
    async def run_facility_debate(facility_data_json: str) -> str:
        """Run an Advocate/Skeptic debate to verify a facility's capability claims.

        Call this after getting facility data from ask_analyst or ask_verifier
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

        Call this after gathering gap and facility data from ask_analyst
        to get a structured comparison with
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
            ask_analyst,
            ask_planner,
            ask_verifier,
            ask_rag_agent,
            run_facility_debate,
            run_mission_debate,
        ],
        model="gpt-5.2",
    )
