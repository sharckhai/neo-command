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

The map is **bidirectional** — chat drives the map AND the map drives the chat:
- **Chat → Map**: Ask about Northern Region, the map zooms there. Ask about surgical capability, facilities light up by capability level.
- **Map → Chat**: Click a facility marker to see its profile and verification status. Click a region to trigger "What's the healthcare landscape here?" Click empty space to ask "What's near here?" Select multiple facilities to compare them.

The planner can use whichever feels natural — type a question or explore the map directly. Both interaction paths feed the same agent pipeline.

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
│  Next.js + Mapbox (dark) + SSE streaming + Trace Panel│
└────────────────────────┬─────────────────────────────┘
                         │ SSE (Server-Sent Events)
┌────────────────────────┴─────────────────────────────┐
│                   BACKEND (FastAPI)                    │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │         OpenAI Agents SDK Supervisor Agent               │ │
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
│  Databricks Vector Search ─── vector embeddings       │
│  NetworkX Knowledge Graph ─── relationships + gaps    │
└──────────────────────────────────────────────────────┘
```

### 4.1 Agents

#### Triage Agent (Supervisor)
- OpenAI Agents SDK `Agent` with `handoffs` to specialized agents
- Classifies user intent into EXPLORE / VERIFY / PLAN using `instructions` prompt
- Uses SDK `handoff()` to delegate to the right specialist agent — the SDK handles context passing automatically
- **Conversation state**: Full message history maintained in the SDK `Runner` context per session. Each agent in the handoff chain sees the full conversation. For long sessions, a background summarization call compresses older messages. This enables multi-turn flows like: recommend → planner pushes back → re-evaluate with new constraints.
- Decomposes complex queries into sub-tasks when needed via sequential handoffs

#### SQL Agent
- OpenAI Agents SDK `Agent` with Genie as a `function_tool`
- Genie (Databricks text-to-SQL) generates SQL against the cleaned facility table
- Agent validates Genie output, handles edge cases, formats results
- Covers questions requiring exact numbers (how many, which region has most, etc.)

#### Self-RAG Vector Search Agent
- OpenAI Agents SDK `Agent` with vector search + self-reflection tools
- Searches Databricks Vector Search embeddings of procedure/equipment/capability free text
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

**Graceful Failure Handling**
- Every agent has a fallback response that is informative, not dead-end:
  - **Empty SQL results**: "No facilities matching that query in the data. This could mean: (a) the capability exists but wasn't captured in our sources, (b) it genuinely doesn't exist in this region. Would you like me to check neighboring regions or broaden the search?"
  - **Facility not found**: "I don't have data on [name]. Did you mean [fuzzy match suggestions]? Or I can search for [specialty] facilities in that area instead."
  - **Low-confidence results**: "I found 3 matches, but confidence is low (all single-source Facebook data). Take these with caution — I'd recommend verifying before planning a mission."
  - **Agent reasoning failure**: Show partial results with "Here's what I could determine. I wasn't able to assess [X] because [reason]."

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
- **Deduplicate with merge strategy**: Group rows by `pk_unique_id`. For each entity, merge fields across sources using priority: (1) official website > directory > Facebook for structured fields, (2) union all free-text claims across sources, (3) for conflicting values (e.g., different bed counts), keep the value from the highest-quality source and flag the conflict in `quality_flags`. Result: 797 clean entity records from 987 raw rows.
- Fix known data issues ("farmacy" → "pharmacy")
- **Geocode facilities (multi-strategy)**:
  - Primary: city name → lat/lng via Ghana gazetteer lookup table
  - Fallback 1: LLM extraction from capability/description text (many contain "Located at..." phrases) — 64 facilities have null cities but may have location in free text
  - Fallback 2: Region centroid for facilities with only `address_stateOrRegion`
  - Tag geocoding confidence: `exact` (address match), `city` (city centroid), `extracted` (LLM from text), `region` (region centroid), `unknown` (no location data)

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
- **Databricks Vector Search Index**: Embeddings of free-text fields (procedure, equipment, capability, description), chunked at field level for precise citations, with metadata filters (region, facility type, specialty). Falls back to LanceDB for local dev.
- **NetworkX Graph**: In-memory knowledge graph for relationship traversal and gap detection

### 5.3 Data Quality Model

Every data point carries metadata:
- `source_url`: where it was scraped from
- `source_type`: facebook / official_website / directory / linkedin
- `confidence`: 0-100 score based on source quality + corroboration
- `corroboration_count`: how many independent sources confirm this claim
- `quality_flags`: list of issues (single_source, aspirational_language, referral_only, stale_data)

---

## 6. Provided Prompts & Pydantic Models

The challenge provides 4 Python files (`data/prompts_and_pydantic_models/`) that define how the CSV data was originally extracted. These are our source-of-truth for understanding the data schema and can be reused/adapted in our agents.

### 6.1 Organization Extraction (`organization_extraction.py`)
- **Prompt**: `ORGANIZATION_EXTRACTION_SYSTEM_PROMPT` — classifies entities from text into facilities, NGOs, or other
- **Model**: `OrganizationExtractionOutput` — `ngos: List[str]`, `facilities: List[str]`, `other_organizations: List[str]`
- **Our use**: Adapt this prompt for the Triage Agent's intent classification. Reuse the facility/NGO distinction logic.

### 6.2 Organization Information (`facility_and_ngo_fields.py`)
- **Prompt**: `ORGANIZATION_INFORMATION_SYSTEM_PROMPT` — extracts structured fields for a single `{organization}`
- **Models**: `BaseOrganization` → `Facility` (adds facilityTypeId, operatorTypeId, affiliationTypeIds, description, area, numberDoctors, capacity) and `NGO` (adds countries, missionStatement, organizationDescription)
- **Our use**: These Pydantic models define our data model directly. Use `Facility` and `NGO` as the canonical schemas for our cleaned data. The `BaseOrganization` fields map 1:1 to CSV columns.

### 6.3 Medical Specialties (`medical_specialties.py`)
- **Prompt**: `MEDICAL_SPECIALTIES_SYSTEM_PROMPT` — 4-step reasoning chain to classify specialties from facility name + text
- **Model**: `MedicalSpecialties` — `specialties: List[str]` (camelCase, case-sensitive)
- **Key config**: `LEVEL_OF_SPECIALTIES = 1` (0th and 1st hierarchy levels). Depends on external `fdr.config.medical_specialties.MEDICAL_HIERATCHY`.
- **Our use**: Reuse the facility name parsing rules and terminology mappings in our Medical Knowledge Service. The specialty list defines valid values for the `specialties` column.

### 6.4 Free-Form Facts (`free_form.py`)
- **Prompt**: `FREE_FORM_SYSTEM_PROMPT` — extracts procedures, equipment, capabilities from text + images for `{organization}`
- **Model**: `FacilityFacts` — `procedure: List[str]`, `equipment: List[str]`, `capability: List[str]`
- **Our use**: This is the most critical file. The `procedure`, `equipment`, and `capability` columns in the CSV were generated by this prompt. Understanding these category definitions is essential for:
  - Building accurate vector search over these fields
  - The Facility Intelligence Agent's co-occurrence validation (e.g., a procedure should have supporting equipment)
  - The Self-RAG agent's relevance grading (knowing what counts as a "procedure" vs "capability")

### 6.5 Pipeline Integration

These 4 stages ran sequentially during data collection:
```
Web page → Stage 1: Extract org names → Stage 2: Extract structured fields
         → Stage 3: Classify specialties → Stage 4: Extract free-form facts
```

We don't need to re-run this pipeline (the CSV is our input), but we reuse the prompts/models:
- **At ingestion**: Use `FacilityFacts` categories to validate/re-parse the CSV's free-text fields
- **At query time**: Use `MEDICAL_SPECIALTIES_SYSTEM_PROMPT` rules for specialty matching and synonym expansion
- **For validation**: Use `ORGANIZATION_INFORMATION_SYSTEM_PROMPT`'s conservative extraction rules as the standard for our Facility Intelligence Agent

---

## 7. Databricks Free Edition Constraints

The challenge is explicitly scoped for the Databricks Free Edition. Key limits to design around:
- **SQL Warehouse**: Serverless, limited compute hours. Our dataset is 797 entities — queries are fast and cheap. Pre-compute aggregations where possible to minimize runtime queries.
- **MLflow**: Free tier includes experiment tracking and model registry. Agent step tracing fits within limits for a hackathon demo.
- **Model Serving**: Foundation model APIs (DBRX, Llama 3) available with rate limits. Use for SQL Agent and fingerprinting. Batch fingerprinting during pre-processing, not at runtime.
- **Vector Search**: Mosaic AI Vector Search is available. If Free Edition limits are too restrictive, fall back to LanceDB locally with a note in the demo.
- **Storage**: Unity Catalog with limited storage. 797 entities + embeddings is well under any limit.

**Mitigation**: Pre-compute everything possible (fingerprints, embeddings, knowledge graph) so runtime only needs lightweight SQL queries and vector lookups. Heavy LLM reasoning (debate agents) goes through OpenAI API (GPT-4o), not Databricks compute.

---

## 8. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Orchestration** | OpenAI Agents SDK | Native OpenAI integration, agent handoffs, tool use, guardrails. Clean agent-to-agent delegation. |
| **LLM (Reasoning)** | GPT-4o | Best-in-class reasoning for debate agents, medical knowledge, anomaly detection |
| **LLM (Fast tasks)** | GPT-4o-mini | Cost-effective for fingerprinting, classification, geocoding extraction |
| **Text-to-SQL** | Databricks Genie | Native integration with SQL warehouse; judges want to see Databricks |
| **Vector Store** | Databricks Vector Search (Mosaic AI) | Sponsor alignment — keeps all data on Databricks platform. Falls back to LanceDB if Free Edition limits are hit. |
| **Embeddings** | OpenAI text-embedding-3-small | Same provider as LLMs. Cost-effective, good retrieval quality for medical text |
| **Knowledge Graph** | NetworkX | In-memory, fast traversal, 797 entities is tiny |
| **Tracing** | MLflow (on Databricks) | Agent step logging, citation chains, experiment tracking |
| **Frontend** | Next.js | Fast, full-stack React, SSE streaming support |
| **Map** | Mapbox GL JS (dark style) | Beautiful, performant, great API for reactive + interactive updates. Map is core, not stretch — the entire product falls flat without it. |
| **Backend** | FastAPI (Python) | Async, SSE streaming, native Python for OpenAI Agents SDK |
| **Data Platform** | Databricks Free Edition | SQL warehouse, MLflow, Genie — judges want this front and center |
| **Geocoding** | Multi-strategy (gazetteer + LLM extraction + region fallback) | 74% null regions, 6.5% null cities — single strategy won't cover it. LLM extracts "Located at..." from free text as fallback. |

---

## 9. Must-Have Question Coverage

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

## 10. Judging Criteria Alignment

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
| Intuitive interface | Two-panel (map + chat), bidirectional — chat drives map AND map drives chat |
| Transparency | Collapsible Trace Panel shows agent reasoning for trust |
| Follow-up dialogue | Conversation state maintained across turns |

---

## 11. Stretch Goals (If Time Permits)

Ordered by impact-to-effort ratio:

1. **Browser verification agent** — given a facility URL, agent visits the page in real-time to verify current claims against what we have in the dataset. Demonstrates the system can self-update and cross-reference live data. Strong IDP differentiator.
2. **PDF export for mission briefings** — generate a downloadable report from a PLAN conversation. Shows real-world workflow integration. Judges see something they could hand to a donor.
3. **H3 hex grid population overlay** — pre-compute population per hex cell using WorldPop data, overlay on map to show population vs. facility density gaps. Visual impact for Social Impact criterion.
4. **Travel time estimation** — use road network data to show that 50km in rural Ghana ≠ 50km in Accra. Changes the gap analysis fundamentally but complex to implement.

---

## 12. Key Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| OpenAI Agents SDK over LangGraph | Agents SDK | Native OpenAI model integration, clean handoff pattern between agents, built-in guardrails. No adapter layer needed between orchestrator and LLM. Simpler than LangGraph for our agent count. |
| OpenAI models exclusively | GPT-4o + GPT-4o-mini | GPT-4o for reasoning/debate agents where quality matters. GPT-4o-mini for bulk fingerprinting, classification, and geocoding extraction. Single provider simplifies API management and aligns with OpenAI Agents SDK. |
| Databricks for SQL + MLflow | Yes | Sponsor's platform. Judges want to see it. Free Edition is sufficient for 797 entities. |
| Genie for Text-to-SQL | Yes | Databricks-native SQL generation. Understands the schema context. Stronger than hand-rolling SQL generation prompts. |
| Knowledge graph over pure RAG | NetworkX in-memory | Enables gap detection via missing edges. Pure RAG can only find what exists, not what's missing. 797 nodes is tiny — no need for Neo4j. |
| Self-RAG over basic RAG | Custom reflective loop | Free-text is messy. Basic retrieval returns false positives (referral mentions, aspirational language). Self-reflection filters these. Worth the extra LLM calls. |
| Advocate/Skeptic over statistical anomaly detection | LLM debate pattern | Produces more nuanced, explainable verification than simple threshold-based flags. Also makes for a compelling demo. |
| Databricks Vector Search over LanceDB/FAISS | Databricks Mosaic AI | Keeps entire data layer on one platform — SQL, vectors, tracing all on Databricks. Stronger sponsor alignment. LanceDB as local dev fallback if Free Edition Vector Search has limits. |
| Next.js over Streamlit | Next.js | Reactive + interactive map requires real frontend. Streamlit can't do bidirectional map-chat with SSE streaming. Worth the setup cost. |
| Pre-computed fingerprinting | Yes | Move the hard work (LLM extraction from messy text) offline. Runtime queries are fast against pre-processed data. |
| Reuse provided Pydantic models | Yes | The challenge provides `Facility`, `NGO`, `FacilityFacts`, `MedicalSpecialties` models. Using these as our canonical schemas ensures our data layer matches what judges expect. The prompts provide domain expertise we'd otherwise need to invent. |

---

## 13. Data Model

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
lat                 float       -- geocoded (may be city centroid or region centroid)
lng                 float       -- geocoded
geocode_confidence  enum        -- "exact" | "city" | "extracted" | "region" | "unknown"
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

## 14. Example Interactions

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

## 15. Scope Boundaries

**Not in MVP (but possible future work):**
- Real-time web scraping / browser verification agent (stretch goal #1 if time permits)
- Travel time routing via road networks (stretch goal #4)
- Multi-country support (Ghana only for hackathon, architecture is country-agnostic)
- "Won't Have" questions from challenge doc (5.5, 6.2, 11.1, 11.2)

**Out of scope entirely:**
- User authentication or multi-tenancy
- Mobile native app (web responsive is sufficient)
- Financial transaction processing
- EHR/EMR system integration
