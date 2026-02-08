# NeoCommand

**Bridging Medical Deserts with Agentic AI** | Hack Nation 2026 - Databricks Track

NeoCommand is an AI-powered healthcare intelligence platform built for the [Virtue Foundation](https://virtuefoundation.org/). It parses messy, unstructured medical facility data from Ghana, extracts and verifies capabilities, identifies medical deserts, and helps NGO mission planners deploy teams where they are needed most.

---

## Architecture

```
                          +------------------+
                          |    Supervisor    |  (GPT-5.2 intent routing)
                          +--------+---------+
                                   |
              +--------------------+--------------------+
              |                    |                    |
     +--------v------+   +--------v------+   +---------v-----+   +----------+
     |   Analyst     |   |   Verifier    |   |    Planner    |   | RAG Agent|
     | (data lookup, |   | (debate-based |   | (deployment   |   | (user doc|
     |  gap analysis)|   |  credibility) |   |  scoring)     |   |  search) |
     +-------+-------+   +-------+-------+   +-------+-------+   +----+-----+
             |                    |                   |                 |
     +-------v--------------------v-------------------v-----------------v----+
     |                      Knowledge Graph (NetworkX)                       |
     |          742 facilities, 35 capabilities, 48 equipment types          |
     +----------------------------+------------------------------------------+
                                  |
                   +--------------v--------------+
                   |    Virtue Foundation Ghana   |
                   |    Facility & Doctor Registry |
                   +------------------------------+
```

### Multi-Agent Orchestration (OpenAI Agents SDK)

- **Supervisor** routes user queries to specialist agents using intent classification
- **Analyst** handles all data retrieval: facility lookups, gap analysis, desert detection, cold spot mapping
- **Verifier** runs adversarial **Advocate/Skeptic/Judge debates** to assess facility claim credibility
- **Planner** enriches candidate regions with DHS health indicators, population data, and equity rankings, then scores deployment options on **Coverage (40%) / Readiness (30%) / Equity (30%)**
- **RAG Agent** lets NGO planners upload their own field reports (PDF, DOCX, CSV) and query them alongside facility data

### Debate-Driven Verification

For facility claims, an **Advocate** argues the claims are credible, a **Skeptic** challenges them, and a **Judge** synthesizes a confidence score (0-100) with verdict: `verified | plausible | suspicious | likely_false`.

For mission planning, **three Advocates** each argue for a different deployment region, then a **Synthesis agent** ranks and recommends.

### Intelligent Document Parsing (IDP)

A 5-step rule-based extraction pipeline processes unstructured text fields:

1. **Specialty Tokenization** - maps free-text specialties to 28 canonical capability types
2. **Equipment NER** - regex-based extraction of medical equipment (X-ray, ultrasound, CT, etc.)
3. **Procedure Classification** - maps procedures to capabilities
4. **Semantic Extraction** - detects 24/7 availability, bed counts, theatre counts
5. **Anomaly Detection** - cross-reference conflicts (e.g. surgery claim without operating room)

Every extraction includes **row-level citations** and **per-step provenance** tracing back to source data.

### Self-RAG Pipeline

Retrieval results pass through a multi-stage filter:
1. Embed query via `text-embedding-3-small`
2. Vector search (LanceDB)
3. Filter out aspirational language ("plan to offer...") and referral language ("we refer patients for...")
4. LLM grader labels each result (`supported | referral_only | aspirational | unclear`)
5. Only `supported` results reach the agent

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript 5 |
| Maps | Mapbox GL JS |
| Graph Viz | D3.js (force-directed network) |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Agent Framework | OpenAI Agents SDK (GPT-5.2) |
| Vector Store | LanceDB (local) / Databricks Vector Search |
| Knowledge Graph | NetworkX |
| Data Processing | Pandas, Parquet, Papa Parse (client-side CSV) |
| Client-Side RAG | TF-IDF vectorization (zero API calls for basic lookups) |
| Streaming | Server-Sent Events (SSE) |
| Optional | MLflow experiment tracking, Databricks Genie (Text2SQL) |

---

## Project Structure

```
Neo/
  apps/web/                  # Next.js frontend
    app/                     # App router (layout, page, globals)
    components/              # React components
      ChatPanel.tsx          #   Chat interface with SSE streaming
      MapPanel.tsx           #   Mapbox facility map
      OverviewScreen.tsx     #   Overview + medical desert detection
      MissionScreen.tsx      #   Mission planner (chat + trace panel)
      GraphScreen.tsx        #   D3 facility network graph
      DetailScreen.tsx       #   Facility deep-dive with IDP pipeline trace
      AgentTrace.tsx         #   Real-time agent tool execution trace
      CapPill.tsx            #   Capability badge with confidence score
      Header.tsx             #   Tab navigation
    lib/                     # Client-side logic
      capabilities.ts        #   5-step IDP extraction pipeline
      csv.ts                 #   CSV parsing + multi-row deduplication
      geo.ts                 #   Geocoding (Ghana regions)
      rag.ts                 #   Client-side TF-IDF RAG engine
      types.ts               #   TypeScript interfaces
  src/
    agent/                   # Agent definitions (OpenAI Agents SDK)
      supervisor.py          #   Supervisor with agent-as-tool wrappers
      analyst.py             #   Data retrieval specialist
      verifier.py            #   Claim verification specialist
      planner.py             #   Mission deployment specialist
      rag_agent.py           #   Document search specialist
      tools/                 #   Agent tool functions
    server/                  # FastAPI backend
      app.py                 #   HTTP endpoints (/api/chat, /api/facilities, /api/health)
      agents.py              #   Agent streaming + SSE event generation
      config.py              #   Environment config (Settings dataclass)
      models.py              #   Pydantic models (ChatResponse, MapAction, etc.)
      tracing.py             #   TraceRecorder for agent step logging
      medical_knowledge.py   #   Equipment requirements + language detection
      services/
        debate.py            #   Advocate/Skeptic/Judge facility debate
        mission_planner.py   #   Three-advocate mission deployment debate
        retrieval.py         #   Self-RAG pipeline (embed, search, filter, grade)
        document_parser.py   #   Document ingestion for RAG agent
    graph/                   # Knowledge graph (NetworkX)
    pipeline/                # Data pipeline CLI (Typer)
      run.py                 #   5-step: clean -> geocode -> fingerprint -> embed -> upload
  prompts/                   # Agent system prompts (markdown)
    supervisor.md
    analyst.md
    planner.md
    verifier.md
    rag-agent.md
  data/                      # Datasets + challenge docs
  pyproject.toml             # Python dependencies
```

---

## Setup Instructions

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm
- **OpenAI API key** (required for agent capabilities)
- **Mapbox token** (optional, for map visualization)

### 1. Clone the Repository

```bash
git clone https://github.com/sharckhai/neo-command.git
cd neo-command
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```env
# Required
OPENAI_API_KEY=sk-...

# Optional - map visualization
NEXT_PUBLIC_MAPBOX_TOKEN=pk....
MAPBOX_TOKEN=pk....
```

### 3. Install Python Dependencies

```bash
uv sync
```

### 4. Install Frontend Dependencies

```bash
cd apps/web
npm install
cd ../..
```

### 5. Build the Knowledge Graph (Optional — pre-built in repo)

Generate the NetworkX knowledge graph from the Virtue Foundation Ghana CSV dataset:

```bash
PYTHONPATH=src uv run python -m graph.build_graph \
  "data/Virtue Foundation Ghana v0.3 - Sheet1.csv" \
  --country ghana \
  --output-dir data
```

This parses 987 facility records, deduplicates them into ~800 unique entities, geocodes locations, normalizes free-text fields to canonical vocabularies, and runs inference (LACKS, COULD_SUPPORT, DESERT_FOR edges). Outputs:

- `data/knowledge_graph.gpickle` — fast-loading pickle for runtime
- `data/knowledge_graph.graphml` — for visualization in Gephi
- `data/knowledge_graph_meta.json` — node/edge counts and build timestamp


### 6. Start the Backend

```bash
source .venv/bin/activate
uvicorn server.app:app --reload --port 8000
```

### 7. Start the Frontend

```bash
cd apps/web
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for agent LLM calls |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | No | Mapbox token for map visualization |
| `MAPBOX_TOKEN` | No | Server-side Mapbox token |
| `PIPELINE_TARGET` | No | `local` (default) or `databricks` |
| `DATABRICKS_HOST` | No | Databricks workspace URL |
| `DATABRICKS_TOKEN` | No | Databricks personal access token |
| `DATABRICKS_WAREHOUSE_ID` | No | SQL warehouse for Genie queries |
| `DATABRICKS_GENIE_ENDPOINT` | No | Genie Space ID for Text2SQL |
| `MLFLOW_TRACKING_URI` | No | MLflow server for experiment tracking |

---

## Dependencies

### Python (defined in `pyproject.toml`)

**Core:** fastapi, uvicorn, sse-starlette, openai, openai-agents, pandas, pyarrow, pydantic, networkx, geopy, httpx, python-dotenv

**Vector Search:** lancedb (local) or databricks-vectorsearch (cloud)

**Pipeline:** typer, rich, tenacity, thefuzz, tiktoken, duckdb

**Optional:** mlflow, databricks-sdk, databricks-sql-connector

### Frontend (defined in `apps/web/package.json`)

**Core:** next 16.1.6, react 19.2.3, react-dom 19.2.3

**Visualization:** d3 7.9.0, mapbox-gl 3.15.0

**Data:** papaparse 5.4.1

**Dev:** typescript 5, vitest, @testing-library/react, eslint

---

## Key Features

- **Medical Desert Detection** - identifies regions lacking critical healthcare capabilities
- **Adversarial Debate Verification** - Advocate/Skeptic/Judge pattern for facility claim credibility scoring
- **Mission Deployment Planner** - scores regions on Coverage/Readiness/Equity with structured recommendations
- **Document Upload (RAG)** - NGO planners can upload their own field reports and query across them
- **Real-Time Agent Tracing** - watch agent tool calls and reasoning steps live in the UI
- **Row-Level Citations** - every extracted capability traces back to source CSV row and field
- **Interactive Knowledge Graph** - D3 force-directed network showing facility similarity clusters
- **Geospatial Map** - Mapbox visualization with capability filters and desert zone overlays
- **Self-RAG** - retrieval pipeline that filters aspirational and referral language before results reach agents

---

## Challenge Context

Built for the **Databricks x Hack Nation** track: *Bridging Medical Deserts - Building Intelligent Document Parsing Agents for the Virtue Foundation.*

**Evaluation Criteria:**
- Technical Accuracy (35%) - reliable facility queries and anomaly detection
- IDP Innovation (30%) - extraction and synthesis from unstructured free-form text
- Social Impact (25%) - identifying medical deserts for resource allocation
- User Experience (10%) - intuitive interface for non-technical NGO planners

---

## Team

Built at Hack Nation 2026 (Feb 7-8) in collaboration with MIT Sloan AI Club & MIT Club of Northern California.

---

## License

MIT
