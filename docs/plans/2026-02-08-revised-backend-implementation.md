# VirtueCommand Backend — Revised Implementation Plan

> **Context:** graph-rag branch provides Knowledge Graph (742 facilities, 7539 edges), 11 agent tools (OpenAI Agents SDK function_tools), Self-RAG agent with prompt, and CLI runner. Our job: integrate into FastAPI backend + add multi-agent debate patterns for VERIFY/PLAN modes.

## What We Reuse From graph-rag (DO NOT REBUILD)

| Component | Location on graph-rag | What it does |
|---|---|---|
| Knowledge Graph | `graph/` (build, queries, schema, normalize, medical_requirements, desert, inference, geocode, export, config) | Full NetworkX graph with 6 node types, 8 edge types |
| 11 Agent Tools | `agent/tools/` (resolve, search, inspect, gap, anomaly, overview) | All wrapped as `@function_tool` for Agents SDK |
| Self-RAG Agent | `agent/self_rag_agent.py` | Single agent with all 11 tools + detailed prompt |
| Agent Runner | `agent/runner.py` | CLI streaming via `Runner.run_streamed()` |
| Prompts | `prompts/self-rag-agent.md`, `prompts/tools.md` | Agent instructions + tool documentation |
| Caches | `data/geocode_cache.json`, `data/normalization_cache.json` | Pre-computed lookups |

## What We Build (6 Tasks)

### Task 1: Merge graph-rag into our branch

**Goal:** Bring graph-rag code into virtuecommand-pipeline so all subsequent tasks can import it.

**Steps:**
1. `git merge origin/graph-rag --no-commit` (resolve conflicts manually)
2. Merge `pyproject.toml` dependencies (add `geopy`, `networkx` if missing)
3. Verify `graph/`, `agent/`, `prompts/` directories are present
4. Build knowledge graph: `python -m graph.build_graph <csv_path>`
5. Smoke test: `python -m agent.runner "How many hospitals in Northern Region?"`

**Files touched:** pyproject.toml, .gitignore, new dirs: graph/, agent/, prompts/
**Blocked by:** nothing
**Blocks:** Tasks 2, 3, 4, 5

---

### Task 2: Rewrite agents.py — Supervisor Agent with Agents SDK

**Goal:** Replace keyword routing with OpenAI Agents SDK Supervisor that hands off to specialized agents.

**Architecture:**
```
Supervisor (Triage)
  ├── handoff → ExploreAgent (= graph-rag Self-RAG agent, all 11 tools)
  ├── handoff → VerifyAgent (graph tools + debate service from Task 4)
  └── handoff → PlanAgent (graph tools + debate service from Task 5)
```

**Implementation:**
```python
# src/server/agents.py (rewrite)

from agents import Agent, Runner
from agent.self_rag_agent import create_agent as create_explore_agent
from agent.tools import make_all_tools
from graph.export import load_graph

# Load graph once at module level
G = None  # initialized in startup

def init_graph(graph_dir: str = "data"):
    global G
    G = load_graph(graph_dir)

def create_supervisor():
    explore_agent = create_explore_agent(G)
    verify_agent = Agent(
        name="VerifyAgent",
        instructions="...",  # verification-focused prompt
        tools=[*make_all_tools(G), run_debate_tool],
        model="gpt-4o",
    )
    plan_agent = Agent(
        name="PlanAgent",
        instructions="...",  # planning-focused prompt
        tools=[*make_all_tools(G), run_plan_debate_tool],
        model="gpt-4o",
    )
    supervisor = Agent(
        name="Supervisor",
        instructions="Classify user intent into EXPLORE/VERIFY/PLAN and hand off...",
        handoffs=[explore_agent, verify_agent, plan_agent],
        model="gpt-4o-mini",  # fast for classification
    )
    return supervisor

async def build_chat_response(message: str, session_id: str) -> AsyncIterator:
    supervisor = create_supervisor()
    result = Runner.run_streamed(supervisor, message)
    async for event in result.stream_events():
        yield event
    return result.final_output
```

**Files:** `src/server/agents.py` (rewrite)
**Blocked by:** Task 1
**Blocks:** Task 6

---

### Task 3: Rewrite app.py — SSE streaming + map actions + session state

**Goal:** Wire Agents SDK streaming into FastAPI SSE endpoint with trace capture and map action generation.

**Implementation:**
- Use `Runner.run_streamed()` from Agents SDK
- Capture `RunItemStreamEvent` types: tool_call_item → trace, message_output_item → tokens
- Generate map_actions by parsing tool call results for region/facility data
- In-memory session store: `dict[session_id, list[messages]]` for multi-turn context
- Pass conversation history to Runner for follow-up queries

**SSE event types emitted:**
```
{type: "token", text: "..."}           # streaming answer tokens
{type: "trace", step: {...}}           # tool call trace events
{type: "final", payload: ChatResponse} # complete response with map_actions, citations, facilities
```

**Map action extraction logic:**
- Tool call to `search_facilities` or `count_facilities` with region param → `zoom_region`
- Tool results containing facility objects with lat/lng → `highlight_facilities`
- Tool call to `find_gaps` with deserts → `shade_regions`

**Files:** `src/server/app.py` (rewrite), `src/server/models.py` (minor updates)
**Blocked by:** Task 2
**Blocks:** Task 6

---

### Task 4: Advocate/Skeptic Debate Service (VERIFY mode)

**Goal:** Build the LLM debate pattern for facility verification. This is our Technical Accuracy play (35% of judging).

**CAN START IMMEDIATELY** — writes to a new file, no dependency on merge.

**Implementation:**
```python
# src/server/services/debate.py (new)

@dataclass
class DebateResult:
    facility_name: str
    advocate_summary: str
    skeptic_summary: str
    confidence: int          # 0-100
    flags: list[str]
    evidence: dict

async def run_advocate_skeptic(
    facility_name: str,
    claimed_capabilities: list[str],
    confirmed_equipment: list[str],
    missing_equipment: list[str],
    raw_text: str,
    source_count: int,
) -> DebateResult:
    # 1. Advocate LLM call - argues claims are credible
    # 2. Skeptic LLM call - argues claims are suspicious
    # 3. Judge synthesis - produces confidence score + flags
    ...
```

**Advocate prompt focus:** Find supporting evidence, consider visiting specialists, note corroborating sources, acknowledge partial capability.

**Skeptic prompt focus:** Flag missing prerequisite equipment, note single-source claims, identify referral/aspirational language, check procedure-capacity mismatch.

**Judge synthesis:** Weighs both sides → confidence 0-100 + specific flags.

**Fallback:** If no API key, return heuristic-only result using existing `verify.py` logic.

**Files:** `src/server/services/debate.py` (new)
**Blocked by:** nothing (interface-only, integrates with graph tools in Task 6)
**Blocks:** Task 6

---

### Task 5: Multi-Agent Debate Service (PLAN mode)

**Goal:** Build three-advocate debate for deployment recommendations. This is our Social Impact play (25% of judging).

**CAN START IMMEDIATELY** — writes to a new file, no dependency on merge.

**Implementation:**
```python
# src/server/services/mission_planner.py (new)

@dataclass
class DeploymentOption:
    region: str
    coverage_score: float    # population served
    readiness_score: float   # infrastructure quality
    equity_score: float      # underserved priority
    evidence: str
    caveats: list[str]
    verification_steps: list[str]

@dataclass
class PlanBrief:
    options: list[DeploymentOption]
    recommendation: str
    tradeoff_analysis: str
    unknowns: list[str]

async def run_plan_debate(
    user_constraints: str,         # "2 ophthalmologists, 10 days"
    desert_data: list[dict],       # from find_gaps
    cold_spot_data: list[dict],    # from find_cold_spots
    region_overviews: list[dict],  # from explore_overview
) -> PlanBrief:
    # 1. Select top 3 candidate regions from gap data
    # 2. Advocate A argues for region 1
    # 3. Advocate B argues for region 2
    # 4. Advocate C argues for region 3
    # 5. Synthesis agent scores all three on Coverage/Readiness/Equity
    ...
```

**Each advocate receives:** Region overview, facility data, gap analysis, user constraints.
**Each advocate argues:** Why their region maximizes mission impact.
**Synthesis agent:** Compares all three, scores dimensions, produces recommendation with caveats.

**Fallback:** If no API key, return heuristic ranking from existing `plan.py` logic.

**Files:** `src/server/services/mission_planner.py` (new)
**Blocked by:** nothing (interface-only, integrates with graph tools in Task 6)
**Blocks:** Task 6

---

### Task 6: Integration + Smoke Test

**Goal:** Wire Tasks 4 and 5 into the Supervisor agents, run end-to-end tests.

**Steps:**
1. Create `run_debate` function_tool that VerifyAgent can call → invokes debate.py
2. Create `run_plan_debate` function_tool that PlanAgent can call → invokes mission_planner.py
3. Run must-have questions through the full pipeline
4. Verify SSE streaming works (curl test against /api/chat)
5. Verify map_actions are generated correctly

**Test queries:**
- EXPLORE: "How many hospitals in Northern Region have surgical capability?"
- VERIFY: "Which facilities claim surgery but lack operating theatre equipment?"
- PLAN: "I have 2 ophthalmologists for 10 days. Where should I send them?"

**Files:** `src/server/agents.py` (add tool wiring), test scripts
**Blocked by:** Tasks 2, 3, 4, 5

---

## Team Structure

```
Team Lead (coordinator)
  ├── core-integrator: Tasks 1 → 2 → 3 → 6 (sequential critical path)
  ├── verify-builder:  Task 4 (parallel, independent file)
  └── plan-builder:    Task 5 (parallel, independent file)
```

**File ownership (no conflicts):**
- core-integrator: `src/server/agents.py`, `src/server/app.py`, `src/server/config.py`, `pyproject.toml`
- verify-builder: `src/server/services/debate.py` (new file)
- plan-builder: `src/server/services/mission_planner.py` (new file)

**Timeline:**
- Phase 1 (parallel): core-integrator does Task 1 merge | verify-builder does Task 4 | plan-builder does Task 5
- Phase 2 (sequential): core-integrator does Tasks 2 + 3 (after merge)
- Phase 3: core-integrator does Task 6 integration (after all services ready)
