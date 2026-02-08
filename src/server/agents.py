"""VirtueCommand agent orchestration — multi-agent architecture.

Supervisor (main agent) delegates to three data-gathering sub-agents
via function_tool wrappers, then synthesizes the final answer.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import AsyncIterator

from agents import Agent, Runner, function_tool
from agents.stream_events import RunItemStreamEvent

from server.config import settings
from server.models import ChatResponse, MapAction
from server.tracing import TraceRecorder

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"

# Module-level state
_graph = None
_supervisor = None


def _load_prompt(filename: str) -> str:
    """Load a prompt markdown file from the prompts/ directory."""
    return (_PROMPTS_DIR / filename).read_text()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Sub-agent factories
# ---------------------------------------------------------------------------

def _create_explorer(G) -> Agent:
    from agent.tools import make_explorer_tools
    return Agent(
        name="Explorer",
        instructions=_load_prompt("explorer.md"),
        tools=make_explorer_tools(G),
        model="gpt-5.2",
    )


def _create_fact_agent(G) -> Agent:
    from agent.tools import make_fact_tools
    return Agent(
        name="FactAgent",
        instructions=_load_prompt("fact-agent.md"),
        tools=make_fact_tools(G),
        model="gpt-5.2",
    )


def _create_verifier(G) -> Agent:
    from agent.tools import make_verifier_tools
    return Agent(
        name="Verifier",
        instructions=_load_prompt("verifier.md"),
        tools=make_verifier_tools(G),
        model="gpt-5.2",
    )


# ---------------------------------------------------------------------------
# Supervisor construction
# ---------------------------------------------------------------------------

def _create_supervisor(G) -> Agent:
    """Create the Supervisor agent with agent-as-tool wrappers."""
    explorer = _create_explorer(G)
    fact_agent = _create_fact_agent(G)
    verifier = _create_verifier(G)

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
        instructions=_load_prompt("supervisor.md"),
        tools=[
            ask_explorer,
            ask_fact_agent,
            ask_verifier,
            run_facility_debate,
            run_mission_debate,
        ],
        model="gpt-5.2",
    )


# ---------------------------------------------------------------------------
# Fallback (no API key)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_agent_stream(message: str, session_id: str = "default") -> AsyncIterator[dict]:
    """Run the Supervisor agent and yield SSE-ready event dicts.

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

    # Detect mode from which agent tools were called
    mode = "explore"
    tool_names = {s.name for s in recorder.steps}
    if "ask_verifier" in tool_names or "run_facility_debate" in tool_names:
        mode = "verify"
    elif "run_mission_debate" in tool_names:
        mode = "plan"

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
