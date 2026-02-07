# VirtueCommand - Product Specification

> Chat-driven healthcare intelligence for NGO mission planners.
> Ask questions. See the map. Plan the mission.

**Version:** 1.0 | **Date:** Feb 7, 2026 | **Challenge:** Databricks "Bridging Medical Deserts"

---

## 1. What Is This?

VirtueCommand is an agentic AI system that turns messy, scraped healthcare facility data from Ghana into actionable intelligence. An NGO planner types a question in natural language, and the system reasons across structured and unstructured data to deliver evidence-backed answers with citations, confidence scores, and a reactive map.

**Core insight:** Facility data scraped from Facebook pages and directories is *claims*, not *facts*. VirtueCommand treats every data point as an assertion requiring verification, not ground truth.

---

## 2. Who Is It For?

**Primary user:** NGO mission planners (e.g., program directors at Virtue Foundation, Mercy Ships, SEE International) who need to decide *where* to deploy medical teams and *what* to bring.

**Key user characteristics:**
- Non-technical (no SQL, no code)
- Working under time pressure with incomplete information
- Need to justify decisions to donors with evidence
- May be in low-bandwidth environments

---

## 3. How It Works

### 3.1 Two-Panel Interface

```
┌─────────────────────────────┬──────────────────────────────┐
│                             │                              │
│       MAPBOX MAP            │         CHAT PANEL           │
│   (reactive - responds      │   (natural language input)   │
│    to conversation)         │                              │
│                             │   ┌────────────────────────┐ │
│   - Facility markers        │   │ "Where are the         │ │
│   - Coverage circles        │   │  surgical deserts in   │ │
│   - Desert highlighting     │   │  Northern Region?"     │ │
│   - Region shading          │   └────────────────────────┘ │
│                             │                              │
│                             │   Agent response with        │
│                             │   citations + confidence     │
│                             │                              │
│                             │   ┌────────────────────────┐ │
│                             │   │ TRACE PANEL (collapse)  │ │
│                             │   │ Agent reasoning steps   │ │
│                             │   └────────────────────────┘ │
└─────────────────────────────┴──────────────────────────────┘
```

The planner **never touches the map directly** — it updates reactively based on the conversation. Ask about Northern Region, the map zooms there. Ask about surgical capability, facilities light up by capability level.

### 3.2 Three Interaction Modes

The Supervisor Agent classifies every query into one of three modes:

#### MODE 1: EXPLORE — "What's out there?"

> "How many hospitals in Northern Region have surgical capability?"
> "What services does Tamale Teaching Hospital offer?"
> "Which region has the most clinics?"

- Handles **must-have questions**: 1.1–1.5, 2.1, 2.3, 6.1, 7.5, 7.6
- Uses **SQL queries** for structured lookups (counts, comparisons, filters)
- Uses **Self-RAG vector search** for unstructured text (procedures, equipment, capabilities)
- Self-reflective loop filters false positives (e.g., "we refer patients for surgery" ≠ "we do surgery")

#### MODE 2: VERIFY — "Can I trust this?"

> "Which facilities claim surgery but lack operating theatre equipment?"
> "Show me facilities with suspicious capability claims"
> "Does Kumasi South Hospital really have an ICU?"

- Handles **must-have questions**: 3.1, 3.4, 4.4, 4.7, 4.8, 4.9
- Uses **Knowledge Graph** to find mismatches (capability claims with no supporting equipment edges)
- Runs **Advocate/Skeptic debate** for flagged facilities — one agent argues the claims are legit, the other argues they're suspicious
- Outputs per-facility confidence score with specific flags and evidence

#### MODE 3: PLAN — "Where should I deploy?"

> "I have 1 ophthalmologist for 2 weeks. Where should I send them?"
> "Where would a surgical mission have the most impact?"

- Handles **Planning System** (MVP Core Feature #3) + Social Impact criterion
- Uses **Multi-Agent Debate** — three advocates argue for different deployment locations
- Scores each option on **Coverage** (population served), **Readiness** (facility infrastructure), and **Equity** (underserved priority)
- Presents options with tradeoff analysis and explicit recommendation with caveats
- Honest about unknowns — recommends verification steps before committing

---

## 4. Architecture

```
┌──────────────────────────────────────────────────────┐
│                    FRONTEND                           │
│  Next.js + Mapbox (dark) + WebSocket + Trace Panel   │
└────────────────────────┬─────────────────────────────┘
                         │ WebSocket / SSE
┌────────────────────────┴─────────────────────────────┐
│                   BACKEND (FastAPI)                    │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │         LangGraph Supervisor Agent               │ │
│  │    (classifies intent → routes to mode)          │ │
│  └──────┬──────────────┬──────────────┬────────────┘ │
│         │              │              │               │
│         ▼              ▼              ▼               │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐     │
│  │  EXPLORE   │ │   VERIFY   │ │     PLAN     │     │
│  │            │ │            │ │              │     │
│  │ SQL Agent  │ │ Facility   │ │ Multi-Agent  │     │
│  │ + Self-RAG │ │ Intel Agent│ │ Debate       │     │
│  │ Vector     │ │ (Advocate/ │ │ (3 advocates │     │
│  │ Search     │ │  Skeptic)  │ │  + synth)    │     │
│  └────────────┘ └────────────┘ └──────────────┘     │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │              SHARED SERVICES                     │ │
│  │  MLflow Tracing | Medical Knowledge | Geocoding  │ │
│  └─────────────────────────────────────────────────┘ │
└────────────────────────┬─────────────────────────────┘
                         │
┌────────────────────────┴─────────────────────────────┐
│                    DATA LAYER                         │
│                                                       │
│  Databricks SQL Warehouse ─── structured queries      │
│  LanceDB ──────────────────── vector embeddings       │
│  NetworkX Knowledge Graph ─── relationships + gaps    │
└──────────────────────────────────────────────────────┘
```

### 4.1 Agents

#### Supervisor Agent
- LangGraph state machine
- Classifies user intent into EXPLORE / VERIFY / PLAN
- Routes to appropriate agent pipeline
- Maintains conversation state for follow-ups
- Decomposes complex queries into sub-tasks when needed

#### SQL Agent
- Generates SQL against the cleaned facility table in Databricks
- Handles structured queries: counts, comparisons, aggregations, filters
- Covers questions requiring exact numbers (how many, which region has most, etc.)

#### Self-RAG Vector Search Agent
- Searches LanceDB embeddings of procedure/equipment/capability free text
- **Self-reflective loop**: retrieve → grade relevance → filter false positives → expand search with synonyms if needed → return verified results
- Distinguishes actual capabilities from referral mentions, aspirational language, and neighboring facility data
- This is our **IDP Innovation** play (30% of judging)

#### Facility Intelligence Agent
- The trust engine — transforms raw claims into verified intelligence
- **Knowledge Graph queries**: finds capability-equipment mismatches via missing edges
- **Advocate/Skeptic debate**: for each flagged facility, two LLM personas argue whether claims are credible
- **Co-occurrence validation**: surgery requires anesthesia + sterilization + blood supply + post-op care. If any are missing, flag it.
- **Confidence scoring**: 0-100 per facility based on source count, internal consistency, evidence support
- This is our **Technical Accuracy** play (35% of judging)

#### Multi-Agent Debate (Planning)
- Three advocate agents each argue for a different deployment location
- Each presents evidence from the knowledge graph + facility data
- Synthesis agent compares options on Coverage / Readiness / Equity dimensions
- Output includes explicit tradeoffs, recommended option, and verification steps
- This is our **Social Impact** play (25% of judging)

### 4.2 Shared Services

**MLflow Tracing**
- Every agent step logged: tool calls, retrievals, reasoning, LLM inputs/outputs
- Generates citation chains (which data → which reasoning step → which conclusion)
- Powers the Trace Panel in the UI
- Provides **agentic-step-level citations** (the stretch goal judges specifically called out)

**Medical Knowledge Service**
- Prompted LLM with domain-specific medical knowledge
- Procedure-equipment mapping (what equipment does cataract surgery require?)
- Specialty-infrastructure inference (can a 10-bed clinic really do cardiac surgery?)
- Terminology normalization (maps messy text to canonical specialty names)

---

## 5. Data Pipeline

### 5.1 Input
Raw CSV: 987 rows, 797 unique facilities/NGOs, 41 columns. Scraped from Facebook (59%), official websites (24%), directories (17%). Ghana only.

### 5.2 Pre-Processing Pipeline (runs once, ~10 min)

**Step 1: Clean & Normalize**
- Parse JSON arrays in string fields (specialties, procedure, equipment, capability, phone_numbers, websites, affiliationTypeIds)
- Normalize region names (39 raw values → 16 official regions)
- Deduplicate: merge multi-source rows per entity (pk_unique_id) into single enriched records
- Fix known data issues ("farmacy" → "pharmacy")
- Geocode facilities (city → lat/lng via Ghana gazetteer)

**Step 2: LLM Fingerprinting**
- For each facility, LLM extracts structured capabilities from free-text procedure/equipment/capability fields
- Assigns confidence score per capability claim
- Flags anomalies (e.g., "200 procedures" + no equipment listed)
- Identifies upgrade potential (facilities with infrastructure but missing specific capabilities)

**Step 3: Build Knowledge Graph**
- **Nodes**: Regions, Facilities, Capabilities, Equipment, Specialties, NGOs
- **Edges**:
  - `HAS_CAPABILITY` — facility claims a capability
  - `HAS_EQUIPMENT` — facility has specific equipment
  - `HAS_SPECIALTY` — facility offers a specialty
  - `LOCATED_IN` — facility is in a region
  - `LACKS` — facility is MISSING expected equipment for claimed capabilities
  - `COULD_SUPPORT` — facility has infrastructure that could support additional capabilities
  - `DESERT_FOR` — region lacks facilities for a specific specialty/procedure
  - `OPERATES_IN` — NGO operates in a region
- The `LACKS`, `COULD_SUPPORT`, and `DESERT_FOR` edges are the key innovation — modeling what's *missing* enables gap analysis

**Step 4: Index for Retrieval**
- **Databricks SQL Warehouse**: All structured fields (counts, regions, types, capacities)
- **LanceDB Vector Index**: Embeddings of free-text fields (procedure, equipment, capability, description), chunked at field level for precise citations, with metadata filters (region, facility type, specialty)
- **NetworkX Graph**: In-memory knowledge graph for relationship traversal and gap detection

### 5.3 Data Quality Model

Every data point carries metadata:
- `source_url`: where it was scraped from
- `source_type`: facebook / official_website / directory / linkedin
- `confidence`: 0-100 score based on source quality + corroboration
- `corroboration_count`: how many independent sources confirm this claim
- `quality_flags`: list of issues (single_source, aspirational_language, referral_only, stale_data)

---

## 6. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Orchestration** | LangGraph | Agent graphs, state management, conditional routing, conversation memory |
| **LLM** | Claude (Anthropic API) | Medical reasoning quality; tool calling; long context for debate |
| **Text-to-SQL** | Databricks Genie | Native integration with SQL warehouse; judges want to see Databricks |
| **Vector Store** | LanceDB | Lightweight, embeddable, perfect for single-country dataset |
| **Embeddings** | OpenAI text-embedding-3-small | Cost-effective, good retrieval quality |
| **Knowledge Graph** | NetworkX | In-memory, fast traversal, 797 entities is tiny |
| **Tracing** | MLflow (on Databricks) | Agent step logging, citation chains, experiment tracking |
| **Frontend** | Next.js | Fast, full-stack React, WebSocket support |
| **Map** | Mapbox GL JS (dark style) | Beautiful, performant, great API for reactive updates |
| **Backend** | FastAPI (Python) | Async, WebSocket, easy LangGraph integration |
| **Data Platform** | Databricks Free Edition | SQL warehouse, MLflow, Genie — judges want this front and center |
| **Geocoding** | Pre-computed lookup table | Ghana cities → lat/lng, no runtime API dependency |

---

## 7. Must-Have Question Coverage

These 16 questions are what the agent **must** reliably handle (from the challenge's MoSCoW "Must Have" list):

| Question | Mode | Agent(s) |
|---|---|---|
| 1.1 How many hospitals have cardiology? | EXPLORE | SQL Agent |
| 1.2 How many hospitals in [region] can perform [procedure]? | EXPLORE | SQL Agent + Vector Search |
| 1.3 What services does [Facility] offer? | EXPLORE | Vector Search |
| 1.4 Are there clinics in [Area] that do [Service]? | EXPLORE | Vector Search |
| 1.5 Which region has the most [Type] hospitals? | EXPLORE | SQL Agent |
| 2.1 Hospitals treating [condition] within [X] km of [location]? | EXPLORE | SQL Agent + Geocoding |
| 2.3 Largest geographic cold spots for a critical procedure? | EXPLORE | SQL Agent + Knowledge Graph |
| 4.4 Facilities claiming unrealistic procedures for their size? | VERIFY | Facility Intel Agent |
| 4.7 Correlated facility characteristics that move together? | VERIFY | SQL Agent + Facility Intel |
| 4.8 Facilities with high procedure breadth but minimal infrastructure? | VERIFY | Facility Intel Agent |
| 4.9 "Things that shouldn't move together"? | VERIFY | Facility Intel Agent |
| 6.1 Where is the workforce for [subspecialty] practicing? | EXPLORE | SQL Agent + Vector Search |
| 7.5 Procedures dependent on very few facilities? | EXPLORE | SQL Agent |
| 7.6 Oversupply of low-complexity vs scarcity of high-complexity? | EXPLORE | SQL Agent |
| 8.3 Gaps in international development map despite evident need? | PLAN | Knowledge Graph + Multi-Agent |

---

## 8. Judging Criteria Alignment

### Technical Accuracy — 35% (Our strongest play)

| What judges want | How we deliver |
|---|---|
| Reliably handle Must-Have queries | 16 questions mapped to specific agents with defined pipelines |
| Detect anomalies in facility data | Facility Intelligence Agent with knowledge graph mismatch detection |
| Cross-reference claims vs evidence | Advocate/Skeptic debate produces nuanced verification |
| Confidence scoring | Every facility gets 0-100 confidence with per-capability breakdown |
| Citations | Row-level + agentic-step-level via MLflow tracing |

### IDP Innovation — 30% (Our differentiator)

| What judges want | How we deliver |
|---|---|
| Extract meaning from unstructured free-form text | Self-RAG with reflective filtering (not just basic retrieval) |
| Handle messy, inconsistent data | LLM fingerprinting at ingestion + synonym expansion at query time |
| Go beyond simple NER | Distinguish actual capability vs referral vs aspirational language |
| Synthesize structured + unstructured | Dual retrieval (SQL + Vector) fused in agent reasoning |
| Model what's missing | Knowledge graph LACKS edges — absence is information |

### Social Impact — 25% (The "why it matters" story)

| What judges want | How we deliver |
|---|---|
| Identify medical deserts | DESERT_FOR edges in knowledge graph + map visualization |
| Aid resource allocation | PLAN mode with multi-agent debate scoring Coverage/Readiness/Equity |
| Show actionable insights | Ranked deployment recommendations with tradeoff analysis |
| Real-world usability | Designed for actual NGO planner workflows and decisions |
| Honest about limitations | System explicitly states unknowns and recommends verification |

### User Experience — 10% (Clean and focused)

| What judges want | How we deliver |
|---|---|
| Natural language for non-technical users | Conversational chat with suggested starter prompts |
| Intuitive interface | Two-panel (map + chat), no manual map interaction needed |
| Transparency | Collapsible Trace Panel shows agent reasoning for trust |
| Follow-up dialogue | Conversation state maintained across turns |

---

## 9. Stretch Goals (If Time Permits)

Ordered by impact-to-effort ratio:

1. **Map visualization with coverage circles** — shade regions by healthcare density, draw catchment areas around facilities. High visual impact for demo.
2. **PDF export for mission briefings** — generate a downloadable report from a PLAN conversation. Shows real-world integration.
3. **H3 hex grid population overlay** — pre-compute population per hex cell using WorldPop data, overlay on map to show population vs. facility density gaps.
4. **Travel time estimation** — use road network data to show that 50km in rural Ghana ≠ 50km in Accra. Changes the gap analysis fundamentally.

---

## 10. Key Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Databricks for SQL + MLflow | Yes | Sponsor's platform. Judges want to see it. Free Edition is sufficient for 797 entities. |
| Knowledge graph over pure RAG | NetworkX in-memory | Enables gap detection via missing edges. Pure RAG can only find what exists, not what's missing. 797 nodes is tiny — no need for Neo4j. |
| Self-RAG over basic RAG | Custom reflective loop | Free-text is messy. Basic retrieval returns false positives (referral mentions, aspirational language). Self-reflection filters these. Worth the extra LLM calls. |
| Advocate/Skeptic over statistical anomaly detection | LLM debate pattern | Produces more nuanced, explainable verification than simple threshold-based flags. Also makes for a compelling demo. |
| LanceDB over FAISS | LanceDB | Simpler API, persistent storage, metadata filtering built-in. FAISS requires more boilerplate. |
| Next.js over Streamlit | Next.js | Reactive map + chat requires real frontend. Streamlit can't do split-pane with WebSocket-driven map updates. Worth the setup cost. |
| Pre-computed fingerprinting | Yes | Move the hard work (LLM extraction from messy text) offline. Runtime queries are fast against pre-processed data. |
| Claude over GPT-4 for reasoning | Claude | Longer context window for debate agents. Strong medical reasoning. But use GPT-4o-mini for bulk fingerprinting (cheaper). |

---

## 11. Data Model

### Facility (cleaned, deduplicated)

```
pk_unique_id        int         -- entity-level ID (797 unique)
name                string      -- official facility name
organization_type   enum        -- "facility" | "ngo"
facilityTypeId      enum        -- "hospital" | "clinic" | "pharmacy" | "dentist" | "doctor" | null
operatorTypeId      enum        -- "public" | "private" | null
affiliationTypeIds  string[]    -- ["faith-tradition", "government", "academic", "community", "philanthropy-legacy"]
specialties         string[]    -- camelCase specialty codes from hierarchy
description         string      -- free-text description
procedure           string[]    -- free-text procedure claims
equipment           string[]    -- free-text equipment claims
capability          string[]    -- free-text capability claims
phone_numbers       string[]    -- E164 format
email               string
officialWebsite     string      -- domain only
address_city        string
address_stateOrRegion string
address_country     string      -- "Ghana"
address_countryCode string      -- "GH"
yearEstablished     int | null
capacity            int | null  -- bed count (97.7% null)
numberDoctors       int | null  -- (99.7% null)
lat                 float       -- geocoded
lng                 float       -- geocoded
source_urls         string[]    -- all sources this entity was scraped from
source_count        int         -- number of independent sources
confidence          float       -- overall data confidence 0-100
quality_flags       string[]    -- ["single_source", "aspirational_language", etc.]
```

### NGO (extends same base, different relevant fields)

```
-- Same base fields as Facility, plus:
countries           string[]    -- ISO alpha-2 codes
missionStatement    string
organizationDescription string  -- neutral factual description
```

### Knowledge Graph Edges

```
(Facility)  --HAS_CAPABILITY-->   (Capability)
(Facility)  --HAS_EQUIPMENT-->    (Equipment)
(Facility)  --HAS_SPECIALTY-->    (Specialty)
(Facility)  --LOCATED_IN-->       (Region)
(Facility)  --LACKS-->            (Equipment)      # expected but missing
(Facility)  --COULD_SUPPORT-->    (Capability)     # infrastructure exists
(Region)    --DESERT_FOR-->       (Specialty)       # no coverage
(NGO)       --OPERATES_IN-->      (Region)
```

---

## 12. Example Interactions

### EXPLORE Mode
```
Planner: "How many hospitals in Northern Region can perform surgery?"

VirtueCommand: I found 12 hospitals in Northern Region that mention
surgical capabilities. However, after verifying against equipment
data, only 7 show evidence of surgical infrastructure (operating
theatre, anesthesia equipment, sterilization).

The 5 flagged hospitals mention surgery in their descriptions but
lack supporting equipment evidence. They may offer referral services
rather than direct surgical capability.

[Map highlights Northern Region, marks 7 verified green, 5 flagged amber]

Sources: Tamale Teaching Hospital (3 sources, high confidence),
Yendi Municipal Hospital (2 sources, medium confidence)...
```

### VERIFY Mode
```
Planner: "Which facilities have suspicious capability claims?"

VirtueCommand: I found 13 facilities with capability-infrastructure
mismatches:

1. **Sunrise Clinic** (Accra) — Claims 47 procedures including
   cardiac surgery, but lists no surgical equipment and has 12 beds.
   Confidence: 15/100. Flag: breadth-depth mismatch.

2. **Hope Medical Centre** (Kumasi) — Claims neurosurgery capability
   but no imaging equipment listed. Single Facebook source.
   Confidence: 22/100. Flag: missing prerequisite equipment.

[Advocate view]: "The Facebook page does mention a visiting
neurosurgeon program..."
[Skeptic view]: "No imaging equipment makes even basic neuro
assessment impossible. Likely aspirational or referral only."

[Map marks flagged facilities in red]
```

### PLAN Mode
```
Planner: "I have 2 ophthalmologists for a 10-day mission. Where
should I send them?"

VirtueCommand: I've analyzed coverage gaps, facility readiness, and
population need. Three options:

Option A: Tamale (Northern Region)
- Coverage: 2.1M population, nearest eye care 180km away
- Readiness: Tamale Teaching Hospital has exam rooms, no cataract equipment
- Equity: Highest unmet need score (87/100)
- Risk: Limited post-op follow-up infrastructure

Option B: Ho (Volta Region)
- Coverage: 890K population, some basic eye care exists
- Readiness: Ho Municipal Hospital has partial equipment, needs only
  portable surgical microscope
- Equity: Moderate unmet need (64/100)
- Risk: Some NGO overlap (SEE International visited 8 months ago)

Option C: Sunyani (Bono Region)
- Coverage: 1.2M population
- Readiness: Strong hospital infrastructure, has OR
- Equity: Lower unmet need (52/100) — closer to Kumasi referral
- Risk: Lowest impact per mission-day

Recommendation: Option A (Tamale) for maximum impact, but verify
surgical facility readiness before committing. Three critical
unknowns: (1) reliable electricity, (2) sterilization capability,
(3) post-op staffing.

[Map shows all three options with coverage circles and comparison bars]
```

---

## 13. What We're NOT Building

- No real-time data scraping or web crawling
- No user authentication or multi-tenancy
- No mobile app (web responsive is fine)
- No financial transaction processing
- No integration with EHR/EMR systems
- No multi-country support (Ghana only for hackathon)
- No "Won't Have" questions from the challenge doc (5.5, 6.2, 11.1, 11.2)
- No travel time routing (stretch goal only)
