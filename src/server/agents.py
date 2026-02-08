"""VirtueCommand agent orchestration using OpenAI Agents SDK."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Optional

from agents import Agent, Runner, function_tool
from agents.stream_events import RunItemStreamEvent

from server.config import settings
from server.models import ChatResponse, FacilitySummary, MapAction
from server.tracing import TraceRecorder

logger = logging.getLogger(__name__)

# Module-level state
_graph = None
_supervisor = None


def init_agents(graph_dir: str = "data") -> None:
    """Initialize graph and agents. Called at server startup."""
    global _graph, _supervisor
    try:
        from graph.export import load_graph
        _graph = load_graph(graph_dir)
        _supervisor = _create_supervisor(_graph)
        logger.info("Agents initialized with graph (%d nodes)", _graph.number_of_nodes())
    except Exception as e:
        logger.warning("Could not initialize agents with graph: %s. Using fallback.", e)
        _graph = None
        _supervisor = None


def _create_debate_tools():
    """Create function_tools that wrap the debate services."""

    @function_tool
    async def run_facility_debate(facility_data_json: str) -> str:
        """Run an Advocate/Skeptic debate to verify a facility's capability claims.

        Call this after inspecting a facility with inspect_facility to get a
        balanced credibility assessment. The debate produces a confidence score
        and specific flags.

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

        Call this after gathering gap data via find_gaps and explore_overview
        to get a structured recommendation with tradeoffs.

        Args:
            constraints_and_data_json: JSON string with keys:
                - user_constraints: str (e.g. "2 ophthalmologists, 10 days")
                - candidate_regions: list[dict] each with keys:
                    region, facilities, deserts, population, facility_count
        """
        from server.services.mission_planner import plan_mission_tool_fn
        return await plan_mission_tool_fn(constraints_and_data_json)

    return run_facility_debate, run_mission_debate


def _create_supervisor(G) -> Agent:
    """Create the Supervisor agent with handoffs to specialists."""
    from agent.self_rag_agent import create_agent as create_explore_agent
    from agent.tools import make_all_tools

    explore_agent = create_explore_agent(G)
    graph_tools = make_all_tools(G)
    run_facility_debate, run_mission_debate = _create_debate_tools()

    # VerifyAgent: graph tools + debate tool
    verify_agent = Agent(
        name="VerifyAgent",
        instructions="""You are VirtueCommand's verification specialist. You evaluate whether facility capability claims are trustworthy.

WORKFLOW:
1. Call resolve_terms on any medical terms in the query
2. Use detect_anomalies to find facilities with suspicious patterns
3. Use inspect_facility to deep-dive into flagged facilities
4. Use get_requirements to check equipment compliance
5. For the most suspicious facilities, call run_facility_debate with the facility's data to get an Advocate/Skeptic analysis with confidence score

For each flagged facility, clearly state:
- What they claim vs what evidence exists
- Missing prerequisite equipment
- Source count and quality
- Advocate and Skeptic perspectives (from the debate)
- Your confidence assessment

Be honest about data limitations. Flag uncertainty explicitly.""",
        tools=[*graph_tools, run_facility_debate],
        model="gpt-4o",
    )

    # PlanAgent: graph tools + mission debate tool
    plan_agent = Agent(
        name="PlanAgent",
        instructions="""You are VirtueCommand's mission planning specialist. You help NGO teams decide where to deploy medical missions.

WORKFLOW:
1. Call resolve_terms on the medical specialty/capability mentioned
2. Use find_gaps with gap_type="deserts" to find regions lacking the specialty
3. Use find_cold_spots for geographic coverage analysis
4. Use explore_overview for region context on top candidate regions
5. Use find_gaps with gap_type="could_support" to find upgrade-ready facilities
6. Call run_mission_debate with user constraints + candidate region data to get a structured comparison with Coverage/Readiness/Equity scores

Present the debate results with:
- 2-3 ranked deployment options with scores
- A clear recommendation with caveats
- Verification steps before committing
- Honest unknowns""",
        tools=[*graph_tools, run_mission_debate],
        model="gpt-4o",
    )

    supervisor = Agent(
        name="Supervisor",
        instructions="""You are VirtueCommand's triage agent. Classify user queries and hand off to the right specialist.

EXPLORE queries — questions about what exists, counts, facility lookups, geographic search:
- "How many hospitals have cardiology?"
- "What services does Tamale Teaching Hospital offer?"
- "Which region has the most clinics?"
- "Hospitals within 50km of Tamale doing surgery?"
-> Hand off to VirtueCommand (the explore agent)

VERIFY queries — questions about data quality, trust, suspicious claims:
- "Which facilities have suspicious capability claims?"
- "Does this hospital really have an ICU?"
- "Facilities claiming surgery but lacking equipment?"
-> Hand off to VerifyAgent

PLAN queries — deployment decisions, mission planning, resource allocation:
- "Where should I send my ophthalmology team?"
- "I have 2 surgeons for 10 days. Where's the most impact?"
- "Where are the biggest gaps for eye care?"
-> Hand off to PlanAgent

Always hand off. Never answer directly. Just classify and delegate.""",
        handoffs=[explore_agent, verify_agent, plan_agent],
        model="gpt-4o-mini",
    )

    return supervisor


# ---------- Fallback keyword routing (no API key) ----------

_VERIFY_KW = ["suspicious", "verify", "trust", "claim", "mismatch", "real", "credible", "lack", "missing"]
_PLAN_KW = ["deploy", "send", "mission", "where should", "recommend", "prioritize", "plan"]


def _classify_mode_heuristic(message: str) -> str:
    text = message.lower()
    if any(kw in text for kw in _PLAN_KW):
        return "plan"
    if any(kw in text for kw in _VERIFY_KW):
        return "verify"
    return "explore"


def _fallback_response(message: str) -> ChatResponse:
    """Basic response when no API key / no graph."""
    mode = _classify_mode_heuristic(message)
    return ChatResponse(
        mode=mode,
        answer=f"VirtueCommand is running in offline mode (no API key). Mode detected: {mode}. "
               "Please set OPENAI_API_KEY to enable full agent capabilities.",
        citations=[],
        map_actions=[],
        facilities=[],
        trace=[],
    )


# ---------- Main entry point ----------

async def run_agent_stream(message: str, session_id: str = "default") -> AsyncIterator[dict]:
    """Run the agent pipeline and yield SSE-ready event dicts.

    Yields:
        {"type": "trace", "step": {...}}  - tool call events
        {"type": "token", "text": "..."}  - answer tokens
        {"type": "final", "payload": {...}} - complete ChatResponse
    """
    if not _supervisor or not settings.openai_api_key:
        resp = _fallback_response(message)
        for word in resp.answer.split():
            yield {"type": "token", "text": word + " "}
        yield {"type": "final", "payload": resp.model_dump()}
        return

    recorder = TraceRecorder()
    answer_parts = []
    facilities_mentioned = []
    regions_mentioned = []
    mode = "explore"  # will be updated based on agent handoff

    result = Runner.run_streamed(_supervisor, message)

    async for event in result.stream_events():
        if not isinstance(event, RunItemStreamEvent):
            continue

        item = event.item
        item_type = item.type if hasattr(item, "type") else type(item).__name__

        if item_type == "tool_call_item":
            call = item.raw_item
            name = getattr(call, "name", "unknown")
            args = getattr(call, "arguments", "")
            recorder.add_step(name, {"args": args[:500]}, {})
            yield {"type": "trace", "step": {"name": name, "args": args[:200]}}

            # Extract regions/facilities from tool args for map actions
            try:
                args_dict = json.loads(args) if args else {}
                if "region" in args_dict and args_dict["region"]:
                    regions_mentioned.append(args_dict["region"])
            except (json.JSONDecodeError, TypeError):
                pass

        elif item_type == "tool_call_output_item":
            output = getattr(item, "output", "")
            # Update last trace step with output
            if recorder.steps:
                recorder.steps[-1].output = {"result": str(output)[:500]}

            # Extract facility data from tool outputs for map actions
            try:
                output_data = json.loads(output) if isinstance(output, str) else {}
                results = output_data.get("results", [])
                for r in results[:20]:
                    if "facility_id" in r and "name" in r:
                        facilities_mentioned.append(r)
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass

        elif item_type == "message_output_item":
            # This is the final message from the agent
            content = ""
            if hasattr(item, "raw_item"):
                raw = item.raw_item
                if hasattr(raw, "content"):
                    for part in raw.content:
                        if hasattr(part, "text"):
                            content += part.text
            if content:
                for word in content.split():
                    yield {"type": "token", "text": word + " "}
                answer_parts.append(content)

        elif item_type == "handoff_output_item":
            # Detect which agent was handed off to for mode classification
            target = getattr(item, "target_agent", None)
            if target:
                target_name = getattr(target, "name", "")
                if "Verify" in target_name:
                    mode = "verify"
                elif "Plan" in target_name:
                    mode = "plan"

    # Build map actions
    map_actions = []
    if regions_mentioned:
        map_actions.append(MapAction(type="zoom_region", data={"region": regions_mentioned[0]}))
    if facilities_mentioned:
        map_actions.append(MapAction(
            type="highlight_facilities",
            data={"facilities": [{"name": f.get("name"), "lat": f.get("lat"), "lng": f.get("lng")}
                                  for f in facilities_mentioned[:50] if f.get("lat")]}
        ))

    # Build final response
    final_answer = " ".join(answer_parts) if answer_parts else result.final_output or "No response generated."

    response = ChatResponse(
        mode=mode,
        answer=final_answer,
        citations=[],
        map_actions=map_actions,
        facilities=[],
        trace=recorder.snapshot(),
    )

    yield {"type": "final", "payload": response.model_dump()}


# Backward-compatible sync wrapper
def build_chat_response(message: str) -> ChatResponse:
    """Sync fallback for when async isn't available."""
    return _fallback_response(message)
