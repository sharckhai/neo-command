# VirtueCommand

**AI-powered health facility intelligence system for Ghana.** VirtueCommand ingests facility data from multiple sources, builds a medical knowledge graph, and exposes a multi-agent system that answers operational questions — from "which facilities offer dialysis in Northern Region?" to "where should we deploy a surgical mission team?"

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Language** | Python 3.11+ |
| **Agent Framework** | OpenAI Agents SDK (`openai-agents`) |
| **LLM** | GPT-5.2 (agents), GPT-4o-mini (batch normalization) |
| **Graph** | NetworkX MultiDiGraph (in-memory) |
| **Vector Store** | LanceDB (local) / Databricks Vector Search (cloud) |
| **API** | FastAPI + Uvicorn, SSE streaming |
| **Data Processing** | Pandas, DuckDB, PyArrow |
| **Geospatial** | Geopy (geocoding + distance) |
| **Fuzzy Matching** | thefuzz |
| **Frontend** | Next.js (apps/web) |

---

## External Data Sources

### Primary: Virtue Foundation Facility & Doctor Registry (FDR)
987 facility records extracted via web scraping + LLM extraction from facility websites, social media pages, and health registries. Each record includes contact info, address, specialties, procedures, equipment, capabilities, and raw free-text descriptions.

### DHS Subnational Health Indicators
Demographic & Health Survey (DHS 2022) data for all 16 Ghana regions — child/maternal mortality, anemia prevalence, vaccination rates, insurance coverage, and facility delivery rates. Used by the Planner agent to score equity and need.

### Population & Accessibility
- **Population by region** — for density-based scoring
- **Travel time data** — regional accessibility metrics and road quality classification
- **OpenStreetMap** — facility boundary reference data

### WHO Health Systems
National-level health system rankings used for country-level context enrichment.

---

## Knowledge Graph Pipeline

The graph is built from raw CSV data through a multi-stage pipeline (`src/graph/build_graph.py`):

```
CSV (987 rows)
  │
  ├─ 1. Load & Clean ─── parse JSON-encoded list fields, normalize nulls
  ├─ 2. Region Normalize ─ 54+ raw address variants → 16 canonical regions
  ├─ 3. Deduplicate ────── merge multi-source rows by pk_unique_id
  ├─ 4. Vocab Normalize ── free-text → canonical nodes (LLM + regex)
  ├─ 5. Build Graph ────── create nodes + edges with confidence scores
  ├─ 6. Inference ─────── derive LACKS / COULD_SUPPORT edges
  ├─ 7. Desert Detection ─ flag regions with zero providers for a specialty
  └─ 8. Export ──────────── pickle + GraphML + metadata JSON
```

**Output**: 1,019 nodes (742 facilities, 16 regions, 35 capabilities, 48 equipment types) and 7,794 edges.

### Node Types
`Region` | `Facility` | `NGO` | `Specialty` | `Capability` | `Equipment`

### Edge Types
| Edge | Meaning |
|------|---------|
| `LOCATED_IN` | Facility → Region |
| `HAS_CAPABILITY` | Facility → Capability (with confidence score) |
| `HAS_EQUIPMENT` | Facility → Equipment |
| `HAS_SPECIALTY` | Facility → Specialty |
| `LACKS` | Facility → Equipment (inferred: claims capability but missing prerequisite equipment) |
| `COULD_SUPPORT` | Facility → Capability (inferred: has 60%+ required equipment) |
| `DESERT_FOR` | Region → Specialty (zero or near-zero providers) |

### Vocabulary Normalization

Free-text fields (raw_procedures, raw_capabilities, raw_equipment) are mapped to canonical graph nodes via a two-pass approach:

1. **Keyword/regex matching** against an alias dictionary (confidence 0.8)
2. **LLM batch fallback** (GPT-4o-mini) for unmatched items, cached in `data/normalization_cache.json`

### Inference Engine

`src/graph/inference.py` derives edges that don't exist in source data:

- **LACKS**: For each facility claiming a capability, cross-reference `medical_requirements.py` to find missing prerequisite equipment.
- **COULD_SUPPORT**: For facilities *without* a capability but possessing 60%+ of the required equipment — surfacing upgrade opportunities.

---

## Multi-Agent Architecture

VirtueCommand uses a **supervisor pattern** — one orchestrator agent delegates to three specialist agents via tool calls (no handoffs). Each agent has its own system prompt and scoped tool set.

```
                    ┌──────────────┐
        User ──────▶│  Supervisor  │◀──── GPT-5.2
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     ┌──────────┐   ┌──────────┐   ┌──────────┐
     │ Analyst  │   │ Planner  │   │ Verifier │
     │(10 tools)│   │ (1 tool) │   │(2 tools) │
     └──────────┘   └──────────┘   └──────────┘
            │              │              │
            └──────────────┴──────────────┘
                           │
                    ┌──────────────┐
                    │   RAG Agent  │
                    │  (3 tools)   │
                    └──────────────┘
```

### Supervisor

The entry point for all queries. Reads user intent, selects the right specialist(s), and synthesizes a final answer.

**Tools**: `ask_analyst`, `ask_planner`, `ask_verifier`, `ask_rag_agent`, `run_facility_debate`, `run_mission_debate`

**Routing logic**:
- Simple data lookups → Analyst only
- Mission / deployment planning → Analyst → Planner → (optional) Mission Debate
- Data quality / trust questions → Verifier
- Uploaded document questions → RAG Agent
- Cross-validation → Verifier → Analyst

### Analyst

Graph data retrieval specialist. Follows a structured 3-phase workflow:

| Phase | Purpose | Key Tools |
|-------|---------|-----------|
| **0. Vocabulary** | Map user terms to graph vocabulary | `resolve_terms` |
| **1. Landscape** | Get overviews, gaps, and distributions before drilling down | `explore_overview`, `find_gaps`, `count_facilities`, `find_cold_spots` |
| **2. Search** | Find candidate facilities matching criteria | `search_facilities`, `find_facility`, `search_raw_text` |
| **3. Detail** | Batch deep-dive into specific facilities | `inspect_facility`, `get_requirements` |

### Planner

Resource allocation and deployment planning. Enriches Analyst findings with health context data, then scores candidate deployment locations.

**Scoring formula**: Coverage (40%) + Readiness (30%) + Equity (30%)

| Phase | Purpose |
|-------|---------|
| **1. Context Enrichment** | Call `get_region_context` for all candidate regions — pulls DHS indicators, population density, travel access, equity rankings |
| **2. Candidate Scoring** | Score each option on population impact, infrastructure readiness, and underserved priority |
| **3. Plan Synthesis** | Produce ranked options with equipment needs, logistics notes, and caveats |

### Verifier

Data quality and claim validation. Queries `LACKS` edges to identify facilities where capability claims are undermined by missing equipment.

**Tools**: `resolve_terms`, `find_lacks`

### RAG Agent

Handles uploaded documents (PDF, DOCX, HTML, TXT, CSV). Parses and chunks documents preserving structure (tables, headings), embeds with `text-embedding-3-small`, and stores in LanceDB for semantic search.

**Tools**: `ingest_document`, `query_documents`, `list_documents`

---

## Debate Mechanisms

Two structured debate protocols stress-test agent outputs before presenting results.

### Facility Debate (Credibility Assessment)

Evaluates whether a facility's claimed capabilities are trustworthy.

```
Advocate ──▶ argues claims are credible (equipment support, multi-source corroboration)
Skeptic  ──▶ argues claims are suspicious (missing prerequisites, single-source, aspirational language)
Judge    ──▶ produces verdict: verified | plausible | suspicious | likely_false (0-100 confidence)
```

### Mission Debate (Deployment Planning)

Stress-tests deployment recommendations with competing regional advocates.

```
Advocate (Region A) ──┐
Advocate (Region B) ──┼──▶ Synthesizer ──▶ ranked recommendation with tradeoff analysis
Advocate (Region C) ──┘
```

Each advocate scores their region on **Coverage** (population impact), **Readiness** (infrastructure quality), and **Equity** (underserved priority). The Synthesizer weighs all arguments and produces a final ranked plan.

---

## API Layer

FastAPI server (`src/server/app.py`) with three endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check |
| `/api/facilities` | GET | List all facilities with coordinates (for map rendering) |
| `/api/chat` | POST | SSE-streamed agent conversation |

### Chat Streaming

The `/api/chat` endpoint returns Server-Sent Events with three event types:

- **`trace`** — tool call name + arguments (for UI side-effects like map zooming)
- **`token`** — incremental answer text from the LLM
- **`final`** — structured `ChatResponse` with mode, answer, citations, map actions, and facility references

---

## Project Structure

```
.
├── src/
│   ├── agent/
│   │   ├── supervisor.py      # Orchestrator agent
│   │   ├── analyst.py         # Data retrieval agent
│   │   ├── planner.py         # Resource allocation agent
│   │   ├── verifier.py        # Data quality agent
│   │   ├── rag_agent.py       # Document search agent
│   │   └── tools/             # 13 composable graph tools
│   │       ├── resolve_tools.py
│   │       ├── search_tools.py
│   │       ├── inspect_tools.py
│   │       ├── gap_tools.py
│   │       ├── overview_tools.py
│   │       ├── context_tools.py
│   │       ├── anomaly_tools.py
│   │       └── rag_tools.py
│   ├── graph/
│   │   ├── build_graph.py     # CSV → graph pipeline
│   │   ├── normalize.py       # Free-text → canonical vocabulary
│   │   ├── inference.py       # LACKS / COULD_SUPPORT derivation
│   │   ├── desert.py          # Desert detection
│   │   ├── queries.py         # Graph traversal queries
│   │   ├── export.py          # Load/save (pickle + GraphML)
│   │   ├── schema.py          # Node/edge type constants
│   │   └── config/            # Region mappings, health indicators
│   ├── server/
│   │   ├── app.py             # FastAPI application
│   │   ├── agents.py          # Agent init + SSE streaming
│   │   └── services/
│   │       ├── debate.py      # Facility credibility debate
│   │       └── mission_planner.py  # Mission deployment debate
│   └── models/                # Pydantic models + enums
├── apps/web/                  # Next.js frontend
├── prompts/                   # Agent system prompts (Markdown)
├── data/
│   ├── knowledge_graph.gpickle
│   ├── knowledge_graph.graphml
│   ├── normalization_cache.json
│   └── external/              # DHS, population, travel, OSM data
└── pyproject.toml
```

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENAI_API_KEY` | Yes | LLM inference + embeddings |
| `DATABRICKS_HOST` | No | Cloud vector store |
| `DATABRICKS_TOKEN` | No | Cloud vector store auth |
| `VIRTUECOMMAND_TRACE_CONSOLE` | No | Enable console tracing |
