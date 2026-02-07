# VirtueCommand — Product Specification

## A Multi-Agent Healthcare Intelligence System for NGO Mission Planning in Ghana

**Version**: 2.0 — February 2026
**Context**: Virtue Foundation Actionable Data Initiative + Databricks Hackathon
**Primary User**: NGO healthcare planners making resource allocation decisions in low-income countries
**Initial Scope**: Ghana (Upper West, Upper East, Northern, Savannah regions)

---

## Part 1: Problem Definition

### The Real Problem

The Virtue Foundation has spent two decades building the World Compendium — the most comprehensive index of healthcare facilities and nonprofits across 72 low- and lower-middle-income countries. VFMatch.org provides maps, facility profiles, and nonprofit directories. The data exists.

**The problem is not data collection. The problem is decision support.**

An NGO planner in Tamale, Ghana, sitting with a laptop and an intermittent connection, faces decisions like:

- "Where should our next ophthalmology mission go? We have 14 volunteers for 3 weeks."
- "This facility in Wa claims to have an operating room. Can it actually support our team?"
- "Three NGOs are already doing eye camps in Bolgatanga. Should we go there too, or is Tumu completely unserved?"
- "We have $50,000 for equipment. Where does it save the most lives?"

Today, answering these questions requires a researcher to manually cross-reference facility databases, search the web for corroborating evidence, calculate distances, estimate populations, and synthesize unstructured reports — a process that takes days to weeks and still produces uncertain answers.

**This platform turns that process into a conversation.**

### What Exists Today (and Where It Falls Short)

The Virtue Foundation ecosystem already includes:

| Component | What It Does | What's Missing |
|---|---|---|
| **World Compendium** | Curated directory of facilities + nonprofits in 72 countries | Static — no reasoning, no cross-referencing, no anomaly detection |
| **VFMatch.org** | Map-based visualization, facility profiles, volunteer matching | Search/browse only — can't answer analytical questions |
| **Foundational Data Refresh (FDR)** | Structured + unstructured data on facilities (schema with procedures, equipment, capabilities) | Raw data — no synthesis, no verification, no decision layer |
| **DataRobot models** | Predictive analytics for site identification | Black box — no natural language interface, no explainability |
| **CARTO H3 maps** | Hexagonal grid for spatial analysis of medical deserts | Visualization only — no integrated reasoning about what's inside the hexagons |

**The gap**: There is no system that can take a planner's natural language question, reason across structured data + unstructured text + geospatial context + external evidence, and produce a trustworthy, cited, actionable answer.

That is what VirtueCommand builds.

### What Makes This Genuinely Hard

This is not a standard RAG chatbot problem. Five factors make it fundamentally more complex:

1. **Data is claims, not facts.** A facility's website saying "we perform cataract surgery" is an assertion. It may be true, aspirational, outdated, or fraudulent. The system must reason about claim reliability, not just retrieve claims.

2. **Absence is information.** A facility that lists 200 procedures but no equipment is more suspicious than one that lists 5 procedures and an operating microscope. The system must reason about what's *missing*, not just what's present.

3. **Access ≠ proximity.** A hospital 30km away in Ghana's Upper West Region may be 3 hours by motorcycle during dry season and unreachable during rainy season. Distance without travel time modeling is misleading.

4. **Unstructured text carries the real signal.** The difference between "Dr. Mensah performs cataract surgery on Tuesdays" and "Our surgical department offers comprehensive ophthalmic care" is the difference between a verifiable service and a marketing claim. Linguistic patterns reveal operational reality.

5. **Decisions have consequences.** If the system says a facility can support a surgical mission and it can't, volunteer surgeons arrive to find no reliable electricity, no anesthesia, and no blood supply. Patients who traveled days for care go home untreated. False positives are not acceptable.

---

## Part 2: User & Decision Model

### Primary User: The NGO Mission Planner

**Who they are**: Program directors at organizations like Virtue Foundation, Mercy Ships, Remote Area Medical, SEE International. Typically clinicians (surgeons, public health MDs) who transitioned to operational roles. Technically literate but not data scientists. Work across time zones. Often planning from the US/Europe for operations in sub-Saharan Africa.

**Their planning cycle**:

```
Identify Need → Select Region → Verify Partner Facility → Recruit Team → Deploy → Report Impact
     ↑                                                                              |
     └──────────────────── Data from prior missions ←───────────────────────────────┘
```

**Their core decisions and what the system must answer**:

| Decision | Key Question | Data Required | Consequence of Bad Answer |
|---|---|---|---|
| **Where to send the next mission** | Which regions have the highest unmet need for our specialty? | Population, disease burden, existing facilities, current NGO presence, facility capability gaps | Mission goes to an already-served area; underserved region remains neglected |
| **Which facility to partner with** | Can this facility actually support our surgical team? | Equipment inventory, power/water reliability, staff availability, operating room count, past mission history | Team arrives to a facility that can't support them; surgeries don't happen |
| **Whether to invest in equipment** | Would a new autoclave at Facility X unlock surgical capacity, or is the bottleneck workforce? | Equipment gaps, staffing levels, procedure-to-infrastructure ratios, regional referral patterns | Equipment donated to facility that can't use it; sits unused |
| **Avoiding duplication** | Are other NGOs already serving this area for this specialty? | NGO operational footprints, mission schedules, geographic coverage, specialty overlap | Resources wasted on duplication while gaps persist elsewhere |
| **Transport/access planning** | Can patients in catchment area actually reach this facility? | Road networks, travel time (not just distance), seasonal accessibility, transport infrastructure | Mission planned at facility patients can't reach |

### Secondary Users

- **Ministry of Health officials**: Need regional dashboards for health planning, workforce allocation, equipment budgets. Require PDF/report exports for meetings.
- **Donor organizations**: Need impact justification — where does the next dollar do the most good? Require data-backed investment cases.
- **Volunteer clinicians**: Need to understand what they're walking into — facility capabilities, patient volume expectations, local clinical team.

---

## Part 3: The Interface

VirtueCommand is a **chat-driven planning tool** where NGO planners ask questions about healthcare in Ghana and get evidence-backed, debate-tested recommendations with a live map.

### Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  VIRTUECOMMAND                                   [Trace Log ▶]  │
├──────────────────────────────┬───────────────────────────────────┤
│                              │                                   │
│  MAP                         │  CHAT                             │
│  (Mapbox, dark style)        │                                   │
│                              │  Welcome! I can help you          │
│  ● Facilities (colored       │  explore healthcare facility      │
│    by capability level)      │  data across Ghana.               │
│                              │                                   │
│  █ Coverage zones            │  Try:                             │
│                              │  • "Where are the surgical        │
│  ░ Medical deserts           │    deserts?"                      │
│                              │  • "I have 2 surgeons to          │
│                              │    deploy — where?"               │
│                              │  • "Is Aisha Hospital's MRI       │
│                              │    claim credible?"               │
│                              │                                   │
│                              │  ┌───────────────────────────┐   │
│                              │  │ Ask anything...            │   │
│                              │  └───────────────────────────┘   │
├──────────────────────────────┴───────────────────────────────────┤
│  [Trace Panel — collapsed by default, expandable]               │
│  Shows: agent steps, tool calls, evidence used, confidence      │
└──────────────────────────────────────────────────────────────────┘
```

Two panels: **Map + Chat**. That's the core. The trace panel slides up from the bottom or opens as a sidebar when the user clicks "Trace Log" — it's for power users and auditors but doesn't clutter the planner's experience.

**The map is reactive to chat.** Every agent response can push commands to the map: highlight a region, show facilities matching a query, draw coverage circles, shade deserts. The planner never manually operates the map — they just talk, and the map responds.

### Three Modes of Interaction

The system handles three types of questions, each leveraging different SOTA techniques:

| Mode | What the Planner Asks | Techniques | Challenge Questions Covered |
|---|---|---|---|
| **EXPLORE** — "What's out there?" | "What surgical capabilities exist in Northern Region?" | Self-RAG (retrieval + self-reflection), Text-to-SQL | 1.1–1.5, 2.1, 2.3, 6.1, 7.5, 7.6 |
| **VERIFY** — "Can I trust this?" | "Which hospitals have suspicious claims?" | GraphRAG (knowledge graph traversal), Advocate/Skeptic Debate | 3.1, 3.4, 4.4, 4.6, 4.8, 4.9 |
| **PLAN** — "Where should I deploy?" | "I have 1 ophthalmologist for 6 months. Where?" | Multi-Agent Debate, GraphRAG, Gap Analysis | Planning System (Core MVP #3) + Social Impact |

### Export Capabilities

Every conversation can be exported as:

- **Mission Briefing (PDF)**: Formatted document with map, facility assessment, readiness checklist, recommended equipment list, and all citations. Ready for team distribution.
- **Donor Report Extract (DOCX)**: Impact-focused summary with population data, gap analysis, and projected outcomes. Ready for grant applications.
- **Data Table (CSV)**: Raw results for planners who want to do their own analysis.

### Design for Low-Bandwidth

- Chat interface works on 2G connections (text-only mode)
- Maps use vector tiles (not raster) for minimal data transfer
- Reports are generated server-side and downloaded as single files
- Critical data (facility profiles, readiness checklists) cacheable for offline access

---

## Part 4: Four SOTA Techniques

Each technique earns its place by solving a specific problem that simpler approaches cannot.

| Technique | What It Solves | Evaluation Weight |
|---|---|---|
| **Self-RAG** | Messy data → reliable answers (retrieval quality + self-correction) | IDP criterion, 30% |
| **GraphRAG** | Gap detection + multi-hop reasoning across facility relationships | Technical accuracy, 35% |
| **Multi-Agent Debate** | Planning recommendations with explicit tradeoffs | Social impact, 25% |
| **Tracing + Human-in-the-Loop** | Trust + citations + planner can push back | UX, 10% + stretch goal |

### Technique 1: Self-RAG (Self-Reflective Retrieval-Augmented Generation)

**Problem it solves**: Standard RAG retrieves text that matches a query but doesn't verify whether the retrieved content actually answers the question. In healthcare data, this creates dangerous false positives — a facility that mentions "surgery" in the context of "we refer surgical cases to Tamale" gets retrieved for a query about surgical capabilities.

**How it works**:

```
1. Query decomposition: determine if query needs structured (SQL)
   and/or unstructured (vector) retrieval
2. Initial retrieval: SQL query for structured fields +
   vector search for free-text mentions
3. SELF-REFLECTION: Grade relevance of each result.
   "Retrieved 8 facilities. But 2 mention surgery only as
   'we refer surgical cases to...' — this is NOT capability,
   it's referral. Filtering."
4. SELF-REFLECTION: Assess query coverage.
   "Searched 'surgery' but should also check 'operating theatre',
   'surgical', 'OR'. Running expanded search."
5. Second retrieval with expanded terms catches 2 more facilities
6. Final answer with per-facility confidence scores
```

**Where it's used**: Every EXPLORE query. The self-reflection loop catches referral mentions, aspirational language, and incomplete search terms that standard RAG misses.

### Technique 2: GraphRAG (Knowledge Graph + Retrieval)

**Problem it solves**: Facility verification requires multi-hop reasoning — "Does this facility have the equipment that its claimed procedures require?" This isn't a retrieval problem; it's a graph traversal problem. You need to connect procedure claims → required equipment → actual equipment listed → infrastructure dependencies.

**The knowledge graph** (pre-computed at ingestion):

```
[Region] ──has──▶ [Facility]
[Facility] ──has_capability──▶ [Surgery]
[Facility] ──has_equipment──▶ [Operating Room]
[Facility] ──LACKS──▶ [NICU]
[Facility] ──could_support──▶ [Ophthalmology]
[Region] ──desert_for──▶ [Cardiology]
```

**Where it's used**: All VERIFY queries (finding mismatches between claims and evidence), gap analysis (traversing regions for missing capabilities), and planning (finding facilities with infrastructure that *could* support a new service).

### Technique 3: Multi-Agent Debate

**Problem it solves**: Planning decisions involve genuine tradeoffs — equity vs. feasibility, population coverage vs. facility readiness, high need vs. high risk. A single model produces a single answer. A debate between advocates surfaces the tradeoffs explicitly, letting the planner make an informed choice rather than accepting a black-box recommendation.

**Two debate patterns**:

- **Advocate / Skeptic** (for verification): One agent argues the facility claim is legitimate; another argues it's suspicious. The system synthesizes a verdict with confidence.
- **Multi-Advocate** (for planning): Each advocate argues for a different deployment option, with evidence. The system presents all options with tradeoffs.

**Where it's used**: All VERIFY queries (Advocate/Skeptic) and all PLAN queries (Multi-Advocate).

### Technique 4: Tracing + Human-in-the-Loop

**Problem it solves**: NGO planners won't act on recommendations they can't verify. Every claim the system makes must trace back to source data, and the planner must be able to push back, ask follow-ups, and test scenarios.

**Implementation**: MLflow logs every agent step, tool call, retrieval result, and reasoning chain. The Trace Panel exposes this to users who want to inspect. Citations in every response link to source data rows and specific text fields.

---

## Part 5: Detailed Interaction Examples

### Mode 1: EXPLORE

```
PLANNER: "What surgical capabilities exist in Northern Region?"

SELF-RAG PIPELINE:
1. Query decomposition: need both structured (facility counts)
   and unstructured (free-text mentions of surgery)
2. Retrieve: SQL query for Northern Region facilities +
   vector search for surgical mentions in procedure/equipment/capability
3. SELF-REFLECTION: "Retrieved 8 facilities. But 2 of these
   mention surgery only as 'we refer surgical cases to...' —
   this is NOT capability, it's referral. Filtering."
4. SELF-REFLECTION: "I searched 'surgery' but should also check
   'operating theatre', 'surgical', 'OR'. Running expanded search."
5. Second retrieval catches 2 more facilities
6. Final answer with confidence per facility

RESPONSE: "Northern Region has 8 facilities mentioning surgical services.
6 are verified with corroborating equipment data. 2 are likely
referral-only."

[Map: Northern Region highlighted, 8 pins appear,
 6 green (verified), 2 yellow (unverified)]
[Citations: each facility linked to row + specific text]
```

### Mode 2: VERIFY

```
PLANNER: "Which hospitals have suspicious claims?"

GRAPHRAG + DEBATE PIPELINE:
1. Knowledge graph query: find facilities where capability claims
   have no supporting equipment edges
2. For each flagged facility, run Advocate/Skeptic debate:

   Facility: "General Clinic, Accra"
   Type: clinic | Procedures: mentions surgery

   ADVOCATE: "Many clinics in Ghana perform minor surgical
   procedures. This could be legitimate minor surgery."

   SKEPTIC: "Classified as 'clinic', no operating theatre listed,
   no equipment field populated at all. Surgical claims from a
   facility with zero equipment data should be treated as unverified."

   VERDICT: ⚠️ LOW CONFIDENCE — unverified surgical claim

3. Aggregate all flags into a report

RESPONSE: "Found 13 facilities with capability/infrastructure mismatches.
4 are clinics claiming surgical procedures with no equipment data.
3 hospitals claim advanced imaging but only list basic X-ray.
Full list with reasoning attached."

[Map: 13 flagged facilities appear as ⚠️ markers]
[Trace: full debate transcript for each, expandable]
```

### Mode 3: PLAN

```
PLANNER: "I have 1 ophthalmologist for 6 months. Where?"

MULTI-AGENT DEBATE + GRAPHRAG:
1. Graph query: find all facilities with eye care capabilities
2. Graph query: find regions with NO eye care
3. Graph query: find facilities with infrastructure that COULD support
   ophthalmology (has some medical equipment, reasonable facility size,
   but no eye specialist)
4. Three advocates debate with evidence:

┌──────────────────────────────────────────────────────┐
│ DEPLOYMENT ANALYSIS: 1 Ophthalmologist               │
│                                                      │
│ 📊 OPTION A: Tamale — Northern Region                │
│ Coverage: ████████████████████░  2.4M people         │
│ Readiness: ████████░░░░░░░░░░░  UNCERTAIN            │
│ Equity:    █████████████████████ HIGHEST NEED         │
│ "Zero verified eye care in the north.                │
│ Tamale Teaching Hospital has general infrastructure   │
│ but no ophthalmology equipment confirmed."           │
│ [3 citations]                                        │
│                                                      │
│ 📊 OPTION B: Ho — Volta Region                       │
│ Coverage: ██████████░░░░░░░░░░  900K people          │
│ Readiness: ████████████████░░░  GOOD                 │
│ Equity:    ████████████████░░░░ HIGH NEED            │
│ "Volta has 1 low-confidence eye clinic.              │
│ Ho Municipal Hospital has surgical capacity that     │
│ could support ophthalmic procedures."                │
│ [4 citations]                                        │
│                                                      │
│ 📊 OPTION C: Cape Coast — Central Region             │
│ Coverage: ██████████████░░░░░░  1.2M people          │
│ Readiness: ██████████████████░  HIGHEST              │
│ Equity:    ██████░░░░░░░░░░░░░░ MODERATE             │
│ "Some existing eye care but limited to basic.        │
│ Cape Coast Teaching Hospital is well-equipped        │
│ and could immediately support advanced ophthalmic    │
│ surgery." [5 citations]                              │
│                                                      │
│ ⚖️ TRADEOFF: Tamale maximizes lives affected but    │
│ infrastructure is unconfirmed. Cape Coast is safest  │
│ bet but serves fewer underserved.                    │
│ Recommend: Tamale pending site verification.         │
│                                                      │
│ [Map shows all 3 options with coverage circles]      │
└──────────────────────────────────────────────────────┘

PLANNER: "What would we need to verify in Tamale before committing?"

AGENT: [follows up using graph — traverses infrastructure edges
 for Tamale Teaching Hospital]
"Three critical unknowns:
1. Slit lamp and ophthalmoscope availability (not in data)
2. Darkened examination room (not mentioned)
3. Reliable electricity for laser equipment (no power data in records)

Note: St. Anthony's Hospital in Dzodze received equipment through
an NGO project including a generator [row 891]. A similar bundled
deployment model could work for Tamale."
```

### Extended Planning Dialogue

This example demonstrates the full conversational depth of Mode 3 — the planner explores, refines, and acts:

```
PLANNER: "We're planning an ophthalmology mission to northern Ghana in
          March. Where should we go?"

SYSTEM:  [Map highlights northern Ghana regions, color-coded by
          ophthalmology gap severity]

         "Based on verified data, the three regions with the greatest
          unmet ophthalmology need in northern Ghana are:

          1. Sissala East (Upper West) — Population 65,000, nearest
             verified ophthalmology service is 4.2 hours travel in Wa.
             No NGO ophthalmology activity in past 2 years.
             Confidence: High (population data reliable, facility data
             corroborated by 2023 VF mission report).

          2. Bole District (Savannah) — Population 74,000, nearest
             ophthalmology service is 3.8 hours travel in Tamale. One
             faith-based clinic (St. Martin's) claims eye services but
             data is unverified (single web source, no equipment listed).
             Confidence: Medium (facility claim needs verification).

          3. Builsa South (Upper East) — Population 42,000, nearest
             service 2.1 hours in Bolgatanga. SEE International conducted
             an eye camp here in 2022 — no permanent service since.
             Confidence: High.

          Would you like me to assess partner facility readiness in any
          of these regions?"

PLANNER: "Yes, check Sissala. What facility could host us?"

SYSTEM:  [Map zooms to Sissala East, shows facilities]

         "There are 2 facilities in Sissala East district that could
          potentially host a surgical mission:

          Tumu Municipal Hospital
          - Type: District hospital (public)
          - Capacity: 60 beds
          - Has: Operating room (1), backup generator, basic lab
          - Missing for ophthalmology mission: Operating microscope,
            A-scan biometry, phaco machine, IOL inventory, slit lamp
          - Readiness score: 45/100 — facility has basic surgical
            infrastructure but no ophthalmology-specific equipment.
            Your team would need to bring portable equipment.
          - VF history: VF general surgery mission 2022
          - Confidence: High (corroborated by VF mission report +
            GHS registry)

          [Full readiness checklist available — Export as PDF?]"

PLANNER: "What equipment would we need to bring vs. what we could
          procure locally?"

SYSTEM:  "Based on the readiness assessment for Tumu Municipal Hospital:

          BRING (not available locally):
          - Portable operating microscope
          - Phacoemulsification unit + handpieces
          - A-scan/B-scan ultrasound unit
          - IOL inventory (range of diopters)

          PROCURE LOCALLY (available in Wa or Tamale):
          - Surgical drapes and consumables
          - Topical anesthesia (tetracaine, proparacaine)
          - Antibiotics (post-op drops)

          FACILITY ALREADY HAS:
          - Sterilization (autoclave — verified in 2022 mission report)
          - Backup power (diesel generator — confirm fuel availability)
          - Basic surgical instruments

          Note: Confirm generator reliability before mission. 2022
          mission report noted intermittent power issues.

          [Source: VF 2022 Mission Report, Tumu Municipal Hospital
          GHS Profile, FDR Equipment Index]"
```

The planner is in a **dialogue**, not receiving a report. They explore options, ask follow-ups, test scenarios. The system remembers context across the conversation and updates the map with each response.

---

## Part 6: System Architecture

### Architecture Philosophy

Every agent must be tied to a decision the user needs to make. Agents communicate via structured contracts, not vague messages. Every output carries a confidence score and citation chain. The system must degrade gracefully — if one agent fails, the others still work. Natural language in, actionable answer + map + citations out.

### System Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE LAYER                          │
│   Natural Language Chat │ Map View (Mapbox) │ Trace Panel │ Export│
└──────────────────────────────┬────────────────────────────────────┘
                               │ WebSocket
                      ┌────────▼────────┐
                      │    SUPERVISOR    │
                      │  (Intent Router) │
                      │  LangGraph       │
                      └──┬──┬──┬──┬──┬──┘
          ┌──────────────┘  │  │  │  └──────────────┐
          ▼                 ▼  ▼  ▼                 ▼
  ┌──────────────┐  ┌─────────┐ ┌──────────┐  ┌──────────────┐
  │ FACILITY     │  │ DATA    │ │ GAP      │  │ MISSION      │
  │ INTELLIGENCE │  │ QUERY   │ │ FINDER   │  │ PLANNER      │
  │ AGENT        │  │ AGENT   │ │ AGENT    │  │ AGENT        │
  └──────┬───────┘  └───┬─────┘ └────┬─────┘  └──────┬───────┘
         │              │            │                │
  ┌──────▼──────────────▼────────────▼────────────────▼────────┐
  │                 SHARED SERVICES LAYER                       │
  │  Medical Reasoning │ Geospatial Engine │ Citation Tracker   │
  └────────────────────────────┬───────────────────────────────┘
                               │
  ┌────────────────────────────▼───────────────────────────────┐
  │                       DATA LAYER                           │
  │  SQLite (structured) │ FAISS (embeddings) │ NetworkX (KG)  │
  │  Pre-computed: fingerprints, graph, H3 hex grid            │
  └────────────────────────────────────────────────────────────┘
                               │
  ┌────────────────────────────▼───────────────────────────────┐
  │                    MLflow TRACING                           │
  │  Logs every agent step + inputs/outputs for citations      │
  └────────────────────────────────────────────────────────────┘
```

### Frontend

```
┌──────────────────────────────────────────┐
│  FRONTEND (Next.js)                      │
│  ┌────────────┐  ┌────────────────────┐  │
│  │ Map        │  │ Chat               │  │
│  │ (Mapbox)   │  │ (WebSocket)        │  │
│  └────────────┘  └────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │ Trace Panel (collapsible)          │  │
│  └────────────────────────────────────┘  │
└──────────────────┬───────────────────────┘
                   │ WebSocket
                   ▼
┌──────────────────────────────────────────┐
│  BACKEND (FastAPI)                       │
└──────────────────────────────────────────┘
```

---

## Part 7: Agent Definitions

### 1. Supervisor Agent (Intent Router)

**Purpose**: Classify user intent and route to the right agent or agent combination. Not a reasoning agent — a dispatcher.

**Inputs**: User's natural language query + conversation history.

**Processing**:
- Classifies query into one of three modes (EXPLORE / VERIFY / PLAN), which further decompose into five decision categories (mission targeting, facility verification, resource allocation, coordination/deduplication, access/transport)
- Determines whether the query requires a single agent or multi-agent orchestration
- For complex queries, decomposes into sub-tasks and assigns to agents in sequence or parallel
- Maintains conversation state for follow-up queries

**Outputs**: Routing decision — which agent(s), in what order, with what parameters.

**Failure mode**: Misroutes a query. **Mitigation**: If an agent returns low-confidence results, Supervisor re-routes to an alternative agent and asks the user for clarification.

**Why it exists**: Without it, the user would need to know which subsystem to query. The Supervisor turns any question into a routed task.

---

### 2. Data Query Agent (Text-to-SQL + Vector Search with Self-RAG)

**Purpose**: Answer factual questions about facilities, NGOs, and their attributes by querying structured data or performing self-reflective semantic search over unstructured fields.

**Inputs**: Structured query parameters from Supervisor (entity type, filters, geographic scope, specialty, etc.)

**Processing**:

*For structured queries* (counts, comparisons, rankings): translates to SQL via Text-to-SQL against the FDR schema.

*For unstructured queries* (what services does Facility X offer?): performs vector search with metadata filtering over `procedure`, `equipment`, and `capability` fields, then applies the **Self-RAG reflection loop**:

```
1. Initial retrieval
2. Grade relevance of each result
   — Is this actually about what was asked?
3. Filter false positives
   — "we refer surgical cases to..." is referral, NOT capability
   — Aspirational language ("we aim to provide") ≠ current service
4. Assess query coverage
   — Should we expand search terms? ("surgery" → also check
     "operating theatre", "surgical", "OR")
5. If more retrieval needed: run expanded search
6. Return only verified-relevant results with confidence per result
```

*For hybrid queries*: combines SQL results with vector search results.

**Outputs**: Structured result set with row-level citations (facility name, field, source text). Every result carries a relevance confidence score.

**Validation**: Results are sanity-checked — e.g., if a query returns 0 hospitals in a region with known population >500K, flag as potentially incomplete data rather than "no facilities."

**Failure mode**: Text-to-SQL generates incorrect query. **Mitigation**: Show generated SQL to user and allow correction. Vector search returns irrelevant results. **Mitigation**: Confidence thresholding + Self-RAG reflection loop + fallback to keyword search.

**Covers must-have questions**: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 4.7

---

### 3. Facility Intelligence Agent (Verification & Anomaly Detection)

**Purpose**: Assess whether a facility's claimed capabilities are credible, and surface anomalies that suggest misrepresentation or incomplete data. This is the critical differentiator — it transforms raw data into trustworthy intelligence.

**Inputs**: Facility record (structured + unstructured fields), triggered either by user query ("Can Hospital X support our mission?") or by batch verification scan.

**Processing**:

*Capability Consistency Checks* (via Knowledge Graph traversal):
- **Procedure ↔ Equipment alignment**: Does the facility claim procedures that require equipment it doesn't list? Example: claims cataract surgery but no operating microscope, phacoemulsification machine, or A-scan ultrasound → flag.
- **Capability ↔ Infrastructure alignment**: Claims ICU capability but lists capacity of 15 beds and no ventilators → flag.
- **Breadth vs. depth anomaly**: Claims 200 procedures with 2 doctors → flag. Uses statistical benchmarking: procedures-per-doctor ratios, equipment-per-specialty ratios.

*Linguistic Signal Analysis*:
- Parses unstructured text for operational vs. aspirational language. "Dr. Agyeman performs vitrectomy every Wednesday" (high confidence) vs. "We offer comprehensive retinal services" (low confidence).
- Detects temporal patterns: "visiting," "camp," "twice yearly," "in collaboration with" → flags as potentially non-permanent services.
- Classifies services as: **permanent / visiting / camp-based / referral-only**.

*Co-occurrence Validation* (via Knowledge Graph):
- A facility claiming general surgery should have: anesthesia capability, blood supply or bank access, reliable electricity (generator or grid), sterilization equipment, post-operative care capacity.
- Scores each facility on a "capability completeness index" per claimed specialty.

*Advocate/Skeptic Debate* (for flagged facilities):
- **Advocate** argues the claim could be legitimate, citing contextual evidence
- **Skeptic** argues the claim is suspicious, citing missing evidence
- **Verdict** synthesizes both arguments into a confidence assessment

*Cross-source Corroboration*:
- A procedure mentioned on the facility's website, in an NGO mission report, AND in a government registry has higher confidence than one mentioned only on Facebook.

**Outputs**: Facility verification report with:
- Overall confidence score (0-100)
- Per-capability confidence (verified / plausible / unverified / suspicious)
- Specific flags with explanations ("Claims neurosurgery but lists no imaging equipment")
- Missing capability gaps ("To support ophthalmology missions, this facility would need: [list]")
- Mission-specific readiness report (not just a capability inventory)
- Citations for every assessment

**Failure mode**: False negatives — flags a legitimate facility as suspicious because data is incomplete. **Mitigation**: Always frame outputs as "data suggests" not "facility is fraudulent." Always recommend on-the-ground verification for flagged facilities.

**Covers must-have questions**: 3.1, 3.4, 4.4, 4.6, 4.8, 4.9

---

### 4. Gap Finder Agent (Medical Desert Identification)

**Purpose**: Identify geographic regions where healthcare need exceeds available capacity — the "medical deserts" — with specificity by specialty, procedure, and population segment. Answers the fundamental NGO question: *Where is the need greatest?*

**Inputs**: Specialty or procedure of interest, geographic scope, population parameters (optional).

**Processing**:

*Supply Mapping*:
- Queries Data Query Agent for all facilities offering the target specialty/procedure within scope
- Filters through Facility Intelligence Agent to remove low-confidence or suspicious claims
- Maps verified supply points geographically
- Uses knowledge graph `desert_for` edges for pre-computed specialty deserts

*Demand Estimation*:
- Uses population data (WorldPop, Ghana Statistical Service) by administrative region
- Applies disease burden estimates (GBD, WHO) to estimate expected procedure volume
- Accounts for demographic structure where available (age distribution → cataract prevalence, maternal mortality → EmONC need)

*Access Modeling*:
- Calculates **travel time** (not just distance) from population centers to nearest verified facility for the target service
- Uses road network data (OpenStreetMap) with adjustments for road quality and seasonal accessibility
- Defines catchment areas using travel time isochrones (30min, 1hr, 2hr, 4hr)
- Identifies populations outside all catchment areas → these are the medical deserts

*NGO Overlap Check*:
- Queries for NGOs currently operating in identified gap areas
- Classifies NGO presence as permanent (ongoing programs) vs. temporary (mission-based, camps)
- Flags areas with high need AND no NGO presence as highest priority

**Outputs**:
- Ranked list of underserved regions with: population affected, nearest existing service (distance + travel time), confidence in supply data, current NGO presence/absence
- Map visualization with color-coded hexagons (H3) showing supply-demand gap intensity
- Narrative summary explaining methodology and key findings

**Failure mode**: Overestimates gap because data is incomplete (facility exists but isn't in database). **Mitigation**: Clearly label data completeness per region. "We have data on X% of known facilities in this region."

**Covers must-have questions**: 2.1, 2.3, 6.1, 7.5, 7.6, 8.3

---

### 5. Mission Planner Agent (Decision Synthesis & Recommendation)

**Purpose**: Synthesize outputs from all other agents into an actionable mission plan or investment recommendation via **multi-advocate debate**. This is the "last mile" agent that turns intelligence into decisions.

**Inputs**: User's mission parameters (specialty, team size, duration, budget, available dates) + outputs from Gap Finder, Facility Intelligence, and Data Query agents.

**Processing**:

*Candidate Site Ranking*:
- Takes Gap Finder's priority regions
- Cross-references with Facility Intelligence's verified partner facilities in those regions
- Scores each candidate on: unmet need (population × gap severity), facility readiness (capability completeness for the mission type), accessibility (travel time from regional hub), prior mission history, NGO absence (bonus for areas with no current coverage)

*Multi-Advocate Debate*:
- Each advocate argues for a different deployment option with quantified evidence
- Explicit tradeoff analysis: equity vs. feasibility, population coverage vs. facility readiness
- The system presents all options, not a single recommendation

*Readiness Assessment*:
- For top-ranked sites, generates a "mission readiness checklist": what the facility has vs. what the mission needs
- Identifies specific gaps that could be filled pre-mission (e.g., "Facility needs backup generator — $3,000 to procure locally")
- Estimates patient volume based on catchment population and procedure prevalence

*Impact-per-Dollar Framing*:
- Basic cost-effectiveness comparison for recommendations: "Equipping Facility X with a portable ultrasound ($15K) would enable prenatal screening for a catchment of 40,000 women" vs. "A 2-week surgical mission at Facility Y would perform ~100 cataract surgeries at ~$150/surgery."

*Coordination Check*:
- Identifies other NGOs active in the candidate area
- Suggests collaboration opportunities or highlights duplication risks

**Outputs**:
- Ranked mission site recommendations (top 3-5) with justification and visual tradeoff bars
- Per-site readiness report
- Estimated impact metrics (patients served, procedures possible)
- Risk factors and mitigation suggestions
- Exportable briefing document (PDF) for team and donors

**Failure mode**: Recommends a site based on incomplete data that turns out to be unsuitable. **Mitigation**: Every recommendation carries explicit confidence levels and lists assumptions. "This recommendation assumes the facility's claimed operating room is functional — on-the-ground verification recommended."

**Covers**: Integrates all categories; directly supports the core planning cycle.

---

## Part 8: Shared Services Layer

These are **not agents** — they are stateless services called by agents.

### Medical Reasoning Service

A prompted LLM with domain-specific medical knowledge that agents call for:
- **Procedure-equipment mapping**: "What equipment is minimally required for cataract surgery?" → operating microscope, phaco machine or ECCE kit, A-scan biometry, IOL inventory, sterilization
- **Specialty-infrastructure inference**: "What infrastructure should a Level 1 trauma center have?" → 24/7 OR, blood bank, ICU, imaging, etc.
- **Signal function assessment**: Given EmONC signal functions, classify a facility's maternity capability level
- **Language pattern classification**: Distinguish permanent services from visiting/camp/referral patterns in unstructured text

This service maintains a curated knowledge base of clinical requirements that can be updated as medical standards evolve.

### Geospatial Engine

Handles all location-based computation:
- Geodesic distance calculation
- Travel time estimation (road network + speed assumptions by road type + seasonal adjustment)
- H3 hexagonal grid operations (aggregation, neighbor lookup, coverage analysis)
- Catchment area / isochrone generation
- Population-weighted accessibility scoring

Uses: OpenStreetMap road data, WorldPop population grids, administrative boundary files.

### Citation Tracker

Every claim the system makes must trace back to source data. The Citation Tracker:
- Assigns unique IDs to every data point used in reasoning
- Tracks which agent used which data points in which step
- Generates citation chains: "This recommendation is based on [Facility X capability data → Facility Intelligence verification → Gap Finder ranking → Mission Planner scoring]"
- Enables step-level transparency: for each reasoning step, shows inputs and outputs
- Integrates with MLflow for experiment tracking and agent step tracing

---

## Part 9: Data Pipeline (Pre-computation)

Before the chat works, the 987 facilities are processed at ingestion time. This runs once, takes ~10 minutes with a frontier LLM, and then the chat is fast because agents query pre-processed data.

```
RAW CSV (987 rows, messy)
         │
         ▼
┌───────────────────────────┐
│ STEP 1: Clean & Normalize │
│ - Normalize 39 region     │
│   values → 16             │
│ - Deduplicate             │
│ - Parse JSON arrays       │
│ - Geocode facilities      │
│   (city → lat/lng)        │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│ STEP 2: Fingerprint       │
│ - LLM extracts structured │
│   capabilities from       │
│   free text               │
│ - Confidence score per    │
│   capability              │
│ - Anomaly flags           │
│ - Upgrade potential       │
│ - Service temporality     │
│   classification          │
└─────────────┬─────────────┘
              ▼
┌────────────────────────────────────┐
│ STEP 3: Build Knowledge Graph     │
│                                   │
│ [Region] ──has──▶ [Facility]      │
│ [Facility] ──has_cap──▶ [Surgery] │
│ [Facility] ──has_equip──▶ [OR]    │
│ [Facility] ──LACKS──▶ [NICU]     │
│ [Facility] ──could_support──▶ [X] │
│ [Region] ──desert_for──▶ [Cardio] │
└─────────────┬──────────────────────┘
              ▼
┌────────────────────────────────────┐
│ STEP 4: Index for Retrieval       │
│ - SQLite: structured fields       │
│ - FAISS: embeddings of free text  │
│ - NetworkX: knowledge graph       │
│ - H3 hex grid: pre-computed       │
│   population + nearest facility   │
│ - All four queryable by agents    │
└────────────────────────────────────┘
```

---

## Part 10: Data Architecture

### Data Sources

| Source | Type | Content | Update Frequency |
|---|---|---|---|
| **FDR (Foundational Data Refresh)** | Structured + unstructured | Facility attributes, procedures, equipment, capabilities per schema | Periodic scraping |
| **NGO Registry** | Structured | NGO profiles, countries of operation, mission statements, specialties | Quarterly |
| **WorldPop** | Raster | Population density grids at ~100m resolution | Annual |
| **OpenStreetMap** | Network | Road networks with classification (trunk, primary, secondary, track) | Community-maintained |
| **GBD (Global Burden of Disease)** | Tabular | Disease prevalence and incidence by country/region | Annual |
| **Ghana Health Service** | Structured | Official facility registry, district health reports | Irregular |
| **Mission Reports** | Unstructured | Post-mission reports from VF and partner organizations | Per mission |

### Index Architecture

**SQL Database (SQLite / Databricks)**: All structured fields from the FDR schema — facility metadata, contact info, location, operator type, capacity, specialties. This is what the Data Query Agent's Text-to-SQL pipeline queries.

**Vector Index (FAISS / LanceDB)**: Embeddings of unstructured text fields — `procedure`, `equipment`, `capability`, `description`, `organizationDescription`, `missionStatement`. Chunked at the field level (not document level) so citations point to specific fields. Metadata filters on: country, region, facility type, specialty.

**Knowledge Graph (NetworkX)**: Pre-computed facility-capability-equipment-region graph with explicit edge types for has, lacks, could_support, and desert_for relationships. Enables multi-hop traversal for verification and gap analysis.

**Geospatial Index (H3)**: Hexagonal grid (resolution 7, ~5km² per hex) with pre-computed attributes: population count, nearest facility per specialty, travel time to nearest facility. Enables fast spatial queries without recomputing on every request.

### Data Quality Model

Every data point in the system carries a quality assessment:

```json
{
  "value": "Offers cataract surgery using phacoemulsification",
  "source": "facility_website",
  "source_url": "https://wahospital.gh/services",
  "extraction_date": "2024-11-15",
  "confidence": 0.72,
  "corroboration_count": 1,
  "corroborating_sources": ["ngo_mission_report_2023"],
  "staleness_days": 448,
  "quality_flags": ["single_primary_source", "partially_corroborated"]
}
```

---

## Part 11: Confidence & Citation Framework

### Confidence Scoring

Every system output carries a confidence level based on:

| Factor | Weight | Scoring |
|---|---|---|
| **Source count** | 30% | How many independent sources support this claim? 1 source = Low, 2+ corroborating = Medium, 3+ with official registry = High |
| **Source quality** | 25% | Official registry > NGO mission report > Facility website > Social media > User-generated |
| **Recency** | 20% | <6 months = Fresh, 6–18 months = Aging, 18+ months = Stale |
| **Internal consistency** | 15% | Do the facility's claims align with each other? Procedures match equipment? Capacity matches staffing? |
| **Completeness** | 10% | What percentage of expected fields are populated? |

Confidence is surfaced to users as: **High** (act with reasonable confidence), **Medium** (verify key assumptions), **Low** (treat as preliminary — on-the-ground verification essential), **Unverified** (single unconfirmed source — use with extreme caution).

### Citation Chain

Every factual claim traces back through:

```
User-facing claim
  └→ Agent that produced it (with reasoning step ID)
       └→ Data points used (with field-level source)
            └→ Original source (URL, document, registry entry)
```

This is tracked via MLflow experiment logging. Each agent invocation is a "run" with logged inputs, outputs, and intermediate reasoning steps. This enables:

- **Auditability**: Any claim can be traced to source
- **Debugging**: When the system is wrong, we can identify which agent made the error and why
- **Improvement**: Systematic analysis of error patterns to improve agent prompts and logic

---

## Part 12: What's Missing From the Existing Agent Design (Gaps Addressed)

The original agents-and-must-haves document defines a comprehensive question set but has critical gaps when mapped to real planner workflows. This spec addresses six:

| Gap | Problem | How VirtueCommand Addresses It |
|---|---|---|
| **No Readiness Assessment** | Existing design treats facilities as having/not-having a capability. Real planning requires understanding whether a facility can support a specific mission type. | Facility Intelligence Agent produces mission-specific readiness reports, not just capability inventories. |
| **No Transportation/Access Layer** | Geospatial queries for distance but no travel time modeling. In Upper West, 50km could be 30 minutes or 4 hours. | Geospatial Engine uses road network data with quality/speed assumptions. Gap Finder uses travel time as the primary access metric. |
| **No NGO Coordination Intelligence** | NGO coordination failure is a primary challenge — overlapping services while regions go unserved. | Gap Finder integrates NGO operational footprints as a first-class data layer. Mission Planner checks for duplication before recommending sites. |
| **No Temporal Dimension** | A visiting ophthalmologist twice a year is fundamentally different from a permanent department. | Facility Intelligence classifies services as permanent / visiting / camp-based / referral-only via linguistic analysis. |
| **No Impact-per-Dollar Reasoning** | No mechanism for comparing intervention types (equip vs. train vs. send mission). | Mission Planner includes basic cost-effectiveness framing for recommendations. |
| **No Offline/Export Capability** | Assumes real-time interactive system. Planners need PDFs for meetings, CSVs for analysis, offline access in the field. | Every agent output is exportable. Mission Planner produces complete briefing documents. Map visualizations exportable as images. |

---

## Part 13: MVP Scope & Prioritization

### MVP (Build First)

| Component | Scope | Rationale |
|---|---|---|
| Supervisor Agent | Intent classification + routing for 3 modes (Explore/Verify/Plan) | Everything depends on correct routing |
| Data Query Agent (with Self-RAG) | Text-to-SQL for structured queries + self-reflective vector search for unstructured | Foundational — every other agent depends on data access. Self-RAG is the IDP differentiator. |
| Facility Intelligence Agent | Capability consistency checks + linguistic signal analysis + Advocate/Skeptic debate | Core value proposition — turning claims into intelligence |
| Gap Finder Agent | Supply mapping + basic population overlay (without travel time in MVP) | Directly answers "where to go" |
| Knowledge Graph | Pre-computed facility-capability-equipment graph with edge types | Powers both verification and gap analysis |
| Map visualization | Reactive to chat: facility locations + gap hexagons + region highlighting | Planners think spatially |
| Citation tracking | Field-level source attribution via MLflow | Trust requires transparency |
| Trace Panel | Expandable panel showing agent steps, evidence, confidence | For judges and power users |

### Phase 2 (Add Next)

| Component | Scope | Rationale |
|---|---|---|
| Travel time modeling | Road network integration, isochrone generation | Upgrades distance to access — critical for rural planning |
| Mission Planner Agent | Multi-advocate debate, site ranking, readiness checklists, export | The "last mile" from intelligence to action |
| NGO overlap layer | NGO operational footprints + duplication detection | Coordination value |
| PDF/DOCX export | Mission briefings, donor reports | Practical workflow integration |

### Phase 3 (Scale)

| Component | Scope | Rationale |
|---|---|---|
| Temporal service classification | Permanent vs. visiting vs. camp detection | Deeper intelligence |
| Cross-source corroboration | Multi-source verification scoring | Higher confidence data |
| External data integration | GBD disease burden, demographic projections | Demand-side estimation |
| Multi-country expansion | Beyond Ghana to VF's other operational countries | Scale impact |

---

## Part 14: Success Metrics

### Technical Metrics

| Metric | Target | Measurement |
|---|---|---|
| **Must-Have query accuracy** | >85% correct answers on the 15 Must-Have questions | Test set with known-correct answers |
| **Anomaly detection precision** | >70% of flagged facilities confirmed as genuinely suspicious | Manual review by VF clinical staff |
| **False positive rate** | <20% of flagged facilities turn out to be legitimate on ground verification | Tracked over mission cycles |
| **Self-RAG false positive reduction** | >50% fewer irrelevant retrievals vs. standard RAG baseline | Side-by-side evaluation on test queries |

### Impact Metrics

| Metric | Target | Measurement |
|---|---|---|
| **Planning time reduction** | Weeks → hours for mission site selection | Time-to-decision tracking |
| **Mission effectiveness** | >90% of missions report facility met expectations set by system | Post-mission survey |
| **Coverage gap reduction** | Increase % of missions going to previously unserved regions | Year-over-year geographic analysis |
| **Resource coordination** | Reduce reported NGO service duplication in target regions | Partner survey |

### User Metrics

| Metric | Target | Measurement |
|---|---|---|
| **Planner adoption** | 5+ active NGO planning teams within 6 months | Usage tracking |
| **Query-to-action rate** | >30% of interactions lead to a concrete planning action | Follow-up tracking |
| **Trust calibration** | Users report confidence levels align with actual data reliability | User feedback surveys |

---

## Part 15: Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **FDR data is too stale** | High | Medium | Surface staleness prominently; prioritize re-scraping for high-demand regions; allow user-submitted updates post-mission |
| **Text-to-SQL produces wrong queries** | Medium | High | Show generated SQL; allow user correction; maintain curated query templates for common questions |
| **Users over-trust the system** | High | High | Mandatory confidence labels; "verify on ground" warnings for all Medium/Low confidence outputs; never present as ground truth |
| **Facility Intelligence flags legitimate facilities** | Medium | Medium | Frame all flags as "data suggests" not "facility is"; always recommend verification; allow facility operators to respond |
| **Self-RAG reflection loop over-filters** | Medium | Medium | Log all filtered results in trace; allow user to see what was excluded and override |
| **Debate agents produce inconsistent verdicts** | Medium | Low | Seed debate prompts with domain-specific medical reasoning; log all debate transcripts; human review of edge cases |
| **Travel time model is inaccurate** | High | Medium | Use conservative assumptions; clearly state estimates; recommend local validation |
| **System used to justify decisions already made** | Medium | Low | Design outputs to challenge assumptions, not just confirm them; include counter-indicators in reports |

---

## Part 16: Technical Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Orchestration** | LangGraph | Native support for agent graphs, state management, conditional routing |
| **LLM** | Claude (via Anthropic API) or GPT-4o | Medical reasoning quality; tool calling capability; debate generation |
| **Text-to-SQL** | Databricks Genie / custom pipeline | SQL generation quality against FDR schema |
| **Vector Store** | FAISS (MVP) / LanceDB (production) | Lightweight, embeddable, good for single-country datasets |
| **Embeddings** | OpenAI text-embedding-3-small or BGE-large | Cost-effective with good retrieval quality |
| **Knowledge Graph** | NetworkX | Lightweight, Python-native, sufficient for ~1K facility graph |
| **Geospatial** | H3 (Uber) + OSRM (routing) | Hexagonal grid for aggregation; OSRM for travel time |
| **Population Data** | WorldPop + H3 aggregation | Pre-compute population per hex for fast queries |
| **Experiment Tracking** | MLflow | Agent step tracing, citation chain logging, debate transcript capture |
| **Frontend** | Next.js + Mapbox + WebSocket | Reactive map, real-time chat, production-quality UX |
| **Export** | python-docx + reportlab | PDF/DOCX generation for briefing documents |
| **Data Platform** | Databricks Free Edition / SQLite (MVP) | FDR storage, SQL warehouse |

---

## Appendix A: Must-Have Question Coverage

| # | Question | Agent(s) | Mode | Notes |
|---|---|---|---|---|
| 1.1 | How many hospitals have cardiology? | Data Query | EXPLORE | Direct SQL |
| 1.2 | Hospitals in [region] that perform [procedure]? | Data Query | EXPLORE | SQL + vector search |
| 1.3 | What services does [Facility] offer? | Data Query | EXPLORE | Vector search on capability fields |
| 1.4 | Clinics in [Area] that do [Service]? | Data Query | EXPLORE | SQL + vector search |
| 1.5 | Region with most [Type] hospitals? | Data Query | EXPLORE | SQL aggregation |
| 2.1 | Hospitals treating [condition] within [X] km? | Data Query + Geospatial | EXPLORE | SQL + distance calc |
| 2.3 | Largest cold spots for critical procedure? | Gap Finder | EXPLORE | Full gap analysis pipeline |
| 3.1 | Suspicious capability claims? | Facility Intelligence | VERIFY | Graph traversal + debate |
| 3.4 | Facilities with inconsistent data? | Facility Intelligence | VERIFY | Co-occurrence validation |
| 4.4 | Unrealistic procedures relative to size? | Facility Intelligence | VERIFY | Ratio analysis + medical reasoning |
| 4.7 | Correlated facility characteristics? | Data Query + Facility Intelligence | VERIFY | Statistical analysis |
| 4.8 | High breadth with minimal infrastructure? | Facility Intelligence | VERIFY | Anomaly detection via graph |
| 4.9 | Things that shouldn't move together? | Facility Intelligence | VERIFY | Co-occurrence validation |
| 6.1 | Where is workforce for [specialty] practicing? | Data Query + Gap Finder | EXPLORE | Supply mapping |
| 7.5 | Procedures depending on very few facilities? | Data Query + Gap Finder | EXPLORE | Concentration analysis |
| 7.6 | Oversupply vs. scarcity by complexity? | Gap Finder | EXPLORE | Supply-demand analysis |
| 8.3 | Gaps where no NGOs work despite need? | Gap Finder | EXPLORE/PLAN | NGO overlay on gap analysis |

---

## Appendix B: Strengths Inherited From Source Specifications

This merged specification combines the strengths of two prior documents:

**From Spec 1 ("VirtueCommand concept"):**
- Three intuitive interaction modes (Explore / Verify / Plan) as the user's mental model
- Self-RAG pipeline with concrete self-reflection examples showing false positive filtering
- Advocate/Skeptic and Multi-Advocate debate patterns with rich worked examples
- Knowledge graph design with explicit, typed edge relationships (has_cap, LACKS, could_support, desert_for)
- 4-step pre-computation data pipeline (Clean → Fingerprint → Graph → Index)
- Map-reactive chat paradigm — map responds to conversation, no manual operation
- Visual tradeoff presentation for planning recommendations (bar charts per option)
- Conversational follow-up depth — the system remembers context and handles "what would we need to verify?"

**From Spec 2 ("Detailed product spec"):**
- Rigorous problem framing: the 5 factors that make this genuinely hard
- User persona and decision model: planning cycle, decision-consequence mapping, secondary users
- 5-agent architecture with formal bounded responsibilities and clean separation from shared services
- 6 critical gap analysis of the original agent design (readiness, transport, NGO coordination, temporality, cost-effectiveness, offline/export)
- Data quality model with per-datapoint provenance schema
- Weighted confidence scoring framework (source count, quality, recency, consistency, completeness)
- Citation chain formalization through MLflow
- Extended interaction dialogues showing the full planning conversation depth
- MoSCoW-style MVP prioritization with Phase 1/2/3 rationale
- Risk register with mitigations
- Technical, impact, and user success metrics
- Low-bandwidth and offline design considerations for field deployment
- Complete data architecture with sources and update frequencies
