# VirtueCommand — Product Specification
## A chat-driven planning tool where NGO planners ask questions about healthcare in Ghana and get evidence-backed, debate-tested recommendations with a live map.

**Version**: 1.0 — February 2026
**Context**: Virtue Foundation Actionable Data Initiative + Databricks Hackathon
**Primary User**: NGO healthcare planners making resource allocation decisions in low-income countries
**Initial Scope**: Ghana (Upper West, Upper East, Northern, Savannah regions)

### SOTA Technique → Judging Criteria Mapping

| Technique | What It Solves | Judging Criterion |
|---|---|---|
| **Self-RAG** | Messy data → reliable answers | IDP (30%) |
| **GraphRAG** | Gap detection + multi-hop reasoning | Technical Accuracy (35%) |
| **Multi-Agent Debate** | Planning recommendations with tradeoffs | Social Impact (25%) |
| **Tracing + Human-in-the-Loop** | Trust + citations + planner can push back | UX (10%) |

---

## 1. Problem Definition

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

That is what we are building.

### What Makes This Genuinely Hard

This is not a standard RAG chatbot problem. Five factors make it fundamentally more complex:

1. **Data is claims, not facts.** A facility's website saying "we perform cataract surgery" is an assertion. It may be true, aspirational, outdated, or fraudulent. The system must reason about claim reliability, not just retrieve claims.

2. **Absence is information.** A facility that lists 200 procedures but no equipment is more suspicious than one that lists 5 procedures and an operating microscope. The system must reason about what's *missing*, not just what's present.

3. **Access ≠ proximity.** A hospital 30km away in Ghana's Upper West Region may be 3 hours by motorcycle during dry season and unreachable during rainy season. Distance without travel time modeling is misleading.

4. **Unstructured text carries the real signal.** The difference between "Dr. Mensah performs cataract surgery on Tuesdays" and "Our surgical department offers comprehensive ophthalmic care" is the difference between a verifiable service and a marketing claim. Linguistic patterns reveal operational reality.

5. **Decisions have consequences.** If the system says a facility can support a surgical mission and it can't, volunteer surgeons arrive to find no reliable electricity, no anesthesia, and no blood supply. Patients who traveled days for care go home untreated. False positives are not acceptable.

---

## 2. User & Decision Model

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

## 3. Interaction Design — The Three Modes

### Interface Layout: Map + Chat + Trace Panel

```
┌──────────────────────────────────────────────────────────────┐
│  VIRTUECOMMAND                              [Trace Log ▶]    │
├────────────────────────────┬─────────────────────────────────┤
│                            │                                 │
│  MAP                       │  CHAT                           │
│  (Mapbox, dark style)      │                                 │
│                            │  Welcome! I can help you        │
│  ● Facilities (colored     │  explore healthcare facility    │
│    by capability level)    │  data across Ghana.             │
│                            │                                 │
│  █ Coverage zones          │  Try:                           │
│                            │  • "Where are the surgical      │
│  ░ Medical deserts         │    deserts?"                    │
│                            │  • "I have 2 surgeons to        │
│                            │    deploy — where?"             │
│                            │  • "Is Aisha Hospital's MRI     │
│                            │    claim credible?"             │
│                            │                                 │
│                            │  ┌───────────────────────────┐  │
│                            │  │ Ask anything...            │  │
│                            │  └───────────────────────────┘  │
├────────────────────────────┴─────────────────────────────────┤
│  [Trace Panel - collapsed by default, expandable]            │
│  Shows: agent steps, tool calls, evidence used, confidence   │
└──────────────────────────────────────────────────────────────┘
```

Two panels: Map + Chat. That's the core. The trace panel slides up from the bottom or opens as a sidebar when you click "Trace Log" — it's there for judges and power users but doesn't clutter the planner's experience.

**The map is reactive to chat.** Every agent response can push commands to the map: highlight a region, show facilities matching a query, draw coverage circles, shade deserts. The planner never manually operates the map — they just talk, and the map responds.

### Mode 1: EXPLORE — "What's out there?"

*Handles challenge questions: 1.1–1.5, 2.1, 2.3, 6.1, 7.5, 7.6*

**SOTA Technique: Self-RAG** — The system retrieves data, then reflects on whether the retrieval was good enough before answering.

**Pipeline walkthrough:**

```
Planner: "What surgical capabilities exist in Northern Region?"

SELF-RAG PIPELINE:
1. Query decomposition: need both structured (facility counts)
   and unstructured (free-text mentions of surgery)
2. Retrieve: SQL query for Northern Region facilities +
   Vector search for surgical mentions in procedure/equipment/capability
3. SELF-REFLECTION: "Retrieved 8 facilities. But 2 of these
   mention surgery only as 'we refer surgical cases to...' —
   this is NOT capability, it's referral. Filtering."
4. SELF-REFLECTION: "I searched 'surgery' but should also check
   'operating theatre', 'surgical', 'OR'. Running expanded search."
5. Second retrieval catches 2 more facilities
6. Final answer with confidence per facility

Response: "Northern Region has 8 facilities mentioning
surgical services. 6 are verified with corroborating
equipment data. 2 are likely referral-only."

[Map: Northern Region highlighted, 8 pins appear,
 6 green (verified), 2 yellow (unverified)]
[Citations: each facility linked to row + specific text]
```

**Extended example — ophthalmology mission planning:**

```
PLANNER: "We're planning an ophthalmology mission to northern Ghana in
          March. Where should we go?"

SYSTEM:  [Map highlights northern Ghana regions, color-coded by ophthalmology
          gap severity]

         "Based on verified data, the three regions with the greatest unmet
          ophthalmology need in northern Ghana are:

          1. Sissala East (Upper West) — Population 65,000, nearest verified
             ophthalmology service is 4.2 hours travel in Wa. No NGO
             ophthalmology activity recorded in past 2 years.
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
```

### Mode 2: VERIFY — "Can I trust this?"

*Handles challenge questions: 3.1, 3.4, 4.4, 4.6, 4.8, 4.9*

**SOTA Techniques: GraphRAG + Advocate/Skeptic Debate** — The system queries the knowledge graph for structural inconsistencies, then runs an adversarial debate to assess each flagged facility.

**Pipeline walkthrough:**

```
Planner: "Which hospitals have suspicious claims?"

GRAPHRAG + DEBATE PIPELINE:
1. Knowledge graph query: find facilities where
   capability claims have no supporting equipment edges
2. For each flagged facility, run Advocate/Skeptic debate:

   Facility: "General Clinic, Accra"
   Type: clinic | Procedures: mentions surgery

   ADVOCATE: "Many clinics in Ghana perform minor surgical
   procedures. This could be legitimate minor surgery."

   SKEPTIC: "Classified as 'clinic', no operating theatre
   listed, no equipment field populated at all. Surgical
   claims from a facility with zero equipment data should
   be treated as unverified."

   VERDICT: ⚠️ LOW CONFIDENCE — unverified surgical claim

3. Aggregate all flags into a report
```

**Structured output format:**

- **Overall confidence score** (0–100)
- **Per-capability confidence**: verified / plausible / unverified / suspicious
- **Specific flags** with explanations ("Claims neurosurgery but lists no imaging equipment")
- **Missing capability gaps** ("To support ophthalmology missions, this facility would need: [list]")
- **Citations** for every assessment

**Extended example — facility verification:**

```
PLANNER: "Can Tumu Municipal Hospital support our ophthalmology mission?"

SYSTEM:  [Map zooms to Sissala East, shows facility]

         "Tumu Municipal Hospital — Verification Report:

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
```

### Mode 3: PLAN — "Where should I deploy?"

*Handles: Planning System (Core MVP) + Social Impact criterion*

**SOTA Techniques: Multi-Agent Debate + GraphRAG** — Multiple advocate agents each argue for a different deployment option with evidence. The system synthesizes tradeoffs.

**Pipeline walkthrough:**

```
Planner: "I have 1 ophthalmologist for 6 months. Where?"

MULTI-AGENT DEBATE + GRAPHRAG:
1. Graph query: find all facilities with eye care capabilities
2. Graph query: find regions with NO eye care
3. Graph query: find facilities with infrastructure that
   COULD support ophthalmology (has some medical equipment,
   reasonable facility size, but no eye specialist)
4. Three advocates debate with evidence:

┌─────────────────────────────────────────────────┐
│  DEPLOYMENT ANALYSIS: 1 Ophthalmologist         │
│                                                 │
│  OPTION A: Tamale — Northern Region             │
│  Coverage: ████████████████████░  2.4M people   │
│  Readiness: ████████░░░░░░░░░░░  UNCERTAIN      │
│  Equity:    █████████████████████ HIGHEST NEED   │
│  "Zero verified eye care in the north.          │
│   Tamale Teaching Hospital has general           │
│   infrastructure but no ophthalmology equipment  │
│   confirmed." [3 citations]                     │
│                                                 │
│  OPTION B: Ho — Volta Region                    │
│  Coverage: ██████████░░░░░░░░░░  900K people    │
│  Readiness: ████████████████░░░  GOOD           │
│  Equity:    ████████████████░░░░ HIGH NEED      │
│  "Volta has 1 low-confidence eye clinic.        │
│   Ho Municipal Hospital has surgical capacity    │
│   that could support ophthalmic procedures."    │
│   [4 citations]                                 │
│                                                 │
│  OPTION C: Cape Coast — Central Region          │
│  Coverage: ██████████████░░░░░░  1.2M people    │
│  Readiness: ██████████████████░  HIGHEST        │
│  Equity:    ██████░░░░░░░░░░░░░░ MODERATE       │
│  "Some existing eye care but limited to basic.  │
│   Cape Coast Teaching Hospital is well-equipped  │
│   and could immediately support advanced         │
│   ophthalmic surgery." [5 citations]            │
│                                                 │
│  ⚖️ TRADEOFF: Tamale maximizes lives affected   │
│  but infrastructure is unconfirmed. Cape Coast   │
│  is safest bet but serves fewer underserved.    │
│  Recommend: Tamale pending site verification.   │
│                                                 │
│  [Map shows all 3 options with coverage circles] │
└─────────────────────────────────────────────────┘
```

**Mission Planner outputs include:**

- Ranked mission site recommendations (top 3–5) with justification
- Per-site readiness report and mission-specific checklist
- Estimated impact metrics (patients served, procedures possible)
- Cost-effectiveness framing ("Equipping Facility X with a portable ultrasound ($15K) would enable prenatal screening for a catchment of 40,000 women — estimated 800 screenings/year.")
- Risk factors and mitigation suggestions
- Exportable briefing document (PDF) for team and donors

### Export Capabilities

Every conversation can be exported as:
- **Mission Briefing (PDF)**: Formatted document with map, facility assessment, readiness checklist, recommended equipment list, and all citations. Ready for team distribution.
- **Donor Report Extract (DOCX)**: Impact-focused summary with population data, gap analysis, and projected outcomes. Ready for grant applications.
- **Data Table (CSV)**: Raw results for planners who want to do their own analysis.

### Design for Low-Bandwidth

- Chat interface works on 2G connections (text-only mode)
- Maps use vector tiles (not raster) for minimal data transfer
- Reports can be generated server-side and downloaded as single files
- Critical data (facility profiles, readiness checklists) cacheable for offline access

---

## 4. System Architecture

### Design Principles

- Every agent must be tied to a decision the user needs to make
- Agents communicate via structured contracts, not vague "messages"
- Every output carries a confidence score and citation chain
- The system must degrade gracefully — if one agent fails, the others still work
- Natural language in, actionable answer + map + citations out

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js)                        │
│  ┌──────────┐  ┌────────────────┐  ┌──────────────────────┐ │
│  │   Map     │  │  Chat          │  │  Trace Panel         │ │
│  │  (Mapbox) │  │  (WebSocket)   │  │  (collapsible)       │ │
│  └──────────┘  └────────────────┘  └──────────────────────┘ │
└───────────────────────┬──────────────────────────────────────┘
                        │ WebSocket
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  SUPERVISOR AGENT (LangGraph)                          │  │
│  │  Routes by mode: explore / verify / plan               │  │
│  └────┬──────────┬──────────┬──────────┬─────────────────┘  │
│       │          │          │          │                      │
│  ┌────▼───┐ ┌───▼────┐ ┌──▼───────┐ ┌▼──────────────────┐  │
│  │ SQL    │ │ Vector │ │ Facility │ │ Gap Finder /       │  │
│  │ Agent  │ │ Search │ │ Intel    │ │ Mission Planner    │  │
│  │        │ │ Agent  │ │ Agent    │ │ Agent              │  │
│  └────┬───┘ └───┬────┘ └──┬──────┘ └┬───────────────────┘  │
│       │         │         │         │                        │
│  ┌────▼─────────▼─────────▼─────────▼────────────────────┐  │
│  │              SHARED SERVICES LAYER                     │  │
│  │  Medical Reasoning │ Geospatial Engine │ Citation      │  │
│  │  Service           │                   │ Tracker       │  │
│  └────────────────────┬──────────────────────────────────┘  │
│                       │                                      │
│  ┌────────────────────▼──────────────────────────────────┐  │
│  │                    DATA LAYER                          │  │
│  │  SQLite + FAISS + NetworkX KG + H3 Geospatial Index   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  MLflow Tracing                                        │  │
│  │  (logs every agent step + inputs/outputs for citations)│  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Agent Definitions

#### 1. Supervisor Agent (Intent Router)

**Purpose**: Classify user intent and route to the right agent or agent combination. Not a reasoning agent — a dispatcher.

**Inputs**: User's natural language query + conversation history.

**Processing**:
- Classifies query into one of three modes: **EXPLORE**, **VERIFY**, or **PLAN**
- Determines whether the query requires a single agent or multi-agent orchestration
- For complex queries, decomposes into sub-tasks and assigns to agents in sequence or parallel
- Maintains conversation state for follow-up queries

**Outputs**: Routing decision — which agent(s), in what order, with what parameters.

**Failure mode**: Misroutes a query. Mitigation: if an agent returns low-confidence results, Supervisor re-routes to an alternative agent and asks the user for clarification.

---

#### 2. SQL Agent (Text-to-SQL)

**Purpose**: Answer factual questions about facilities, NGOs, and their attributes by querying structured data.

**Inputs**: Structured query parameters from Supervisor (entity type, filters, geographic scope, specialty, etc.)

**Processing**:
- Translates natural language to SQL against the FDR schema (SQLite for hackathon, Databricks for production)
- Handles counts, comparisons, rankings, and aggregations
- Returns raw data with source field citations
- Sanity-checks results — e.g., if a query returns 0 hospitals in a region with known population >500K, flags as potentially incomplete data

**Outputs**: Structured result set with row-level citations (facility name, field, source text).

**Failure mode**: Text-to-SQL generates incorrect query. Mitigation: the agent shows the generated SQL to the user and allows correction.

**Covers must-have questions**: 1.1, 1.2, 1.5, 4.4, 4.7, 7.5, 7.6

---

#### 3. Vector Search Agent (Self-RAG)

**Purpose**: Search embeddings of unstructured text fields — `procedure`, `equipment`, `capability`, `description` — with a self-reflective retrieval loop that filters false positives before answering.

**SOTA Technique: Self-RAG** (targets IDP criterion, 30%)

**Inputs**: Semantic query from Supervisor or other agents.

**Processing — the Self-RAG loop**:
1. **Initial retrieval**: Vector search over embedded facility text
2. **Grade relevance**: Is each result actually about what was asked? (e.g., "we refer surgical cases to..." is NOT a capability claim)
3. **Filter false positives**: Remove referral mentions, aspirational language, irrelevant matches
4. **Decide if more retrieval needed**: Expand query terms (e.g., "surgery" → also check "operating theatre", "surgical", "OR")
5. **Second retrieval** if needed, with expanded terms
6. **Return only verified-relevant results** with confidence per item

**Outputs**: Ranked results with relevance scores, confidence levels, and field-level citations.

**Covers must-have questions**: 1.3, 1.4, 2.1

---

#### 4. Facility Intelligence Agent (Verification & Anomaly Detection)

**Purpose**: Assess whether a facility's claimed capabilities are credible, and surface anomalies that suggest misrepresentation or incomplete data. This is the critical differentiator of the platform.

**SOTA Techniques: GraphRAG + Advocate/Skeptic Debate** (targets Technical Accuracy criterion, 35%)

**Inputs**: Facility record (structured + unstructured fields), triggered either by user query ("Can Hospital X support our mission?") or by batch verification scan.

**Processing**:

*Knowledge Graph Querying (GraphRAG)*:
- Traverses the knowledge graph to find facilities where capability claims have no supporting equipment edges
- Identifies missing edges as gaps (e.g., claims surgery but no `has_equip` edge to any operating equipment)
- Multi-hop reasoning: Region → Facility → Capabilities → Required Equipment → Actual Equipment

*Advocate/Skeptic Debate*:
- For each flagged facility, two LLM perspectives argue:
  - **ADVOCATE**: Argues the claims could be legitimate, citing contextual evidence
  - **SKEPTIC**: Argues the claims are suspicious, citing structural inconsistencies
  - **VERDICT**: Synthesized confidence level with reasoning

*Capability Consistency Checks*:
- **Procedure ↔ Equipment alignment**: Claims cataract surgery but no operating microscope → flag
- **Capability ↔ Infrastructure alignment**: Claims ICU but lists 15 beds and no ventilators → flag
- **Breadth vs. depth anomaly**: Claims 200 procedures with 2 doctors → flag (statistical benchmarking)
- **Linguistic signal analysis**: "Dr. Agyeman performs vitrectomy every Wednesday" (high confidence) vs. "We offer comprehensive retinal services" (low confidence). Detects patterns: "visiting," "camp," "twice yearly," "in collaboration with" → flags as potentially non-permanent services.

*Co-occurrence Validation*:
- Knowledge graph encodes what should co-occur. A facility claiming general surgery should have: anesthesia capability, blood supply access, reliable electricity, sterilization equipment, post-operative care capacity.
- Scores each facility on a "capability completeness index" per claimed specialty.

*Cross-source Corroboration*:
- Checks how many independent sources support a claim. A procedure mentioned on the facility's website, in an NGO mission report, AND in a government registry has higher confidence than one mentioned only on Facebook.

**Outputs**: Facility verification report (see Mode 2 output format above).

**Failure mode**: False negatives (flags a legitimate facility as suspicious because data is incomplete). Mitigation: always frame outputs as "data suggests" not "facility is fraudulent." Always recommend on-the-ground verification for flagged facilities.

**Covers must-have questions**: 3.1, 3.4, 4.4, 4.7, 4.8, 4.9

---

#### 5. Gap Finder Agent / Mission Planner Agent

**Purpose**: Identify geographic regions where healthcare need exceeds available capacity (medical deserts), then synthesize outputs from all agents into actionable mission plans and investment recommendations.

**SOTA Techniques: GraphRAG + Multi-Agent Debate** (targets Social Impact criterion, 25%)

**Inputs**: Specialty/procedure of interest, geographic scope, mission parameters (team size, duration, budget, dates).

**Processing — Gap Analysis (GraphRAG)**:

*Supply Mapping*:
- Queries SQL Agent for all facilities offering the target specialty/procedure within scope
- Filters through Facility Intelligence Agent to remove low-confidence or suspicious claims
- Maps verified supply points geographically
- Knowledge graph traversal: `[Region]──desert_for──▶[Specialty]` edges identify gaps directly

*Demand Estimation*:
- Uses population data (WorldPop, Ghana Statistical Service) by administrative region
- Applies disease burden estimates (GBD, WHO) to estimate expected procedure volume
- Accounts for demographic structure where available (age distribution → cataract prevalence, maternal mortality → EmONC need)

*Access Modeling*:
- Calculates travel time (not just distance) from population centers to nearest verified facility
- Uses road network data (OpenStreetMap) with adjustments for road quality and seasonal accessibility
- Defines catchment areas using travel time isochrones (30min, 1hr, 2hr, 4hr)
- Identifies populations outside all catchment areas → these are the medical deserts

*NGO Overlap Check*:
- Queries for NGOs currently operating in identified gap areas
- Classifies NGO presence as permanent (ongoing programs) vs. temporary (mission-based, camps)
- Flags areas with high need AND no NGO presence as highest priority

**Processing — Mission Planning (Multi-Agent Debate)**:

*Candidate Site Ranking*:
- Takes gap analysis priority regions
- Cross-references with verified partner facilities
- Scores each candidate on: unmet need (population × gap severity), facility readiness, accessibility, prior mission history, NGO absence

*Multi-Advocate Debate*:
- Multiple advocate agents each argue for a different deployment option
- Each advocate presents evidence-backed arguments with visual progress bars (Coverage, Readiness, Equity)
- System synthesizes tradeoffs and produces a recommendation with explicit uncertainty

*Readiness Assessment*:
- For top-ranked sites, generates a mission readiness checklist: what the facility has vs. what the mission needs
- Identifies specific gaps that could be filled pre-mission (e.g., "Facility needs backup generator — $3,000 to procure locally")
- Estimates patient volume based on catchment population and procedure prevalence

*Cost-Effectiveness Framing*:
- "Equipping Facility X with a portable ultrasound ($15K) would enable prenatal screening for a catchment of 40,000 women — estimated 800 screenings/year."
- "A 2-week surgical mission at Facility Y would perform ~100 cataract surgeries at ~$150/surgery."

**Outputs**:
- Ranked list of underserved regions with: population affected, nearest existing service (distance + travel time), confidence in supply data, current NGO presence/absence
- Map visualization with color-coded hexagons (H3) showing supply-demand gap intensity
- Ranked mission site recommendations (top 3–5) with justification
- Per-site readiness report
- Estimated impact metrics (patients served, procedures possible)
- Risk factors and mitigation suggestions
- Exportable briefing document (PDF) for team and donors

**Covers must-have questions**: 2.1, 2.3, 6.1, 7.5, 7.6, 8.3, plus full planning cycle integration

---

### Shared Services Layer

These are not agents — they are stateless services called by agents.

#### Medical Reasoning Service

A prompted LLM with domain-specific medical knowledge that agents call for:
- **Procedure-equipment mapping**: "What equipment is minimally required for cataract surgery?" → operating microscope, phaco machine or ECCE kit, A-scan biometry, IOL inventory, sterilization
- **Specialty-infrastructure inference**: "What infrastructure should a Level 1 trauma center have?" → 24/7 OR, blood bank, ICU, imaging, etc.
- **Signal function assessment**: Given EmONC signal functions, classify a facility's maternity capability level
- **Language pattern classification**: Distinguish permanent services from visiting/camp/referral patterns in unstructured text

This service maintains a curated knowledge base of clinical requirements that can be updated as medical standards evolve.

#### Geospatial Engine

Handles all location-based computation:
- Geodesic distance calculation
- Travel time estimation (road network + speed assumptions by road type + seasonal adjustment)
- H3 hexagonal grid operations (aggregation, neighbor lookup, coverage analysis)
- Catchment area / isochrone generation
- Population-weighted accessibility scoring

Uses: OpenStreetMap road data, WorldPop population grids, administrative boundary files.

#### Citation Tracker

Every claim the system makes must trace back to source data. The Citation Tracker:
- Assigns unique IDs to every data point used in reasoning
- Tracks which agent used which data points in which step
- Generates citation chains: "This recommendation is based on [Facility X capability data → Facility Intelligence verification → Gap Finder ranking → Mission Planner scoring]"
- Enables step-level transparency: for each reasoning step, shows inputs and outputs
- Integrates with MLflow for experiment tracking and agent step tracing

---

## 5. SOTA Techniques Deep Dive

This section details the four state-of-the-art techniques used in VirtueCommand, mapped directly to hackathon judging criteria.

### 5.1 Self-RAG — Self-Reflective Retrieval-Augmented Generation

**Judging criterion**: Innovative Data Processing (IDP) — 30%

Standard RAG retrieves documents and feeds them to an LLM. Self-RAG adds a critical self-reflection step: after retrieval, the LLM evaluates whether the retrieved documents are relevant, sufficient, and correctly interpreted before generating a response.

**Why it matters here**: Healthcare facility data is messy. A naive search for "surgery" returns referral mentions, aspirational claims, and actual capabilities. Self-RAG catches these distinctions.

**Implementation**:
1. **Retrieve** — FAISS vector search over embedded facility text fields
2. **Reflect on retrieval** — LLM grades each result: Is this actually about the queried capability? Is this a claim of capability or a referral? Is the language operational or aspirational?
3. **Decide** — Are results sufficient? If not, expand query terms and retrieve again
4. **Reflect on generation** — Does the final answer faithfully represent the retrieved evidence? Are confidence levels appropriate?

**Where it runs**: Vector Search Agent (every EXPLORE query)

### 5.2 GraphRAG — Knowledge Graph-Enhanced Retrieval

**Judging criterion**: Technical Accuracy — 35%

GraphRAG augments retrieval by structuring data as a knowledge graph, where entities are nodes and relationships are edges. This enables multi-hop reasoning and — critically — detection of *missing* relationships.

**Why it matters here**: A facility claiming surgery but with no equipment edges in the graph is a structural anomaly. A region with no facility edges for a given specialty is a medical desert. The absence of edges IS the signal.

**Knowledge graph structure**:
```
[Region]──has──▶[Facility]
[Facility]──has_cap──▶[Surgery]
[Facility]──has_equip──▶[Operating Room]
[Facility]──LACKS──▶[NICU]
[Facility]──could_support──▶[Ophthalmology]
[Region]──desert_for──▶[Cardiology]
```

**Implementation**:
- Built at ingestion time using NetworkX (see Data Pipeline, Section 6)
- Queried by Facility Intelligence Agent for verification (missing edges = suspicious)
- Queried by Gap Finder Agent for desert detection (absent edges per specialty)
- Multi-hop traversal: Region → Facilities → Capabilities → Required Equipment → Actual Equipment

**Where it runs**: Facility Intelligence Agent (VERIFY mode), Gap Finder Agent (EXPLORE/PLAN modes)

### 5.3 Multi-Agent Debate — Adversarial & Multi-Advocate Reasoning

**Judging criterion**: Social Impact — 25%

Multi-Agent Debate uses multiple LLM instances with distinct roles to argue about a question, producing more robust and balanced recommendations than a single LLM call.

**Two debate patterns**:

1. **Advocate/Skeptic** (used in VERIFY mode):
   - ADVOCATE argues the facility's claims are legitimate
   - SKEPTIC argues the claims are suspicious
   - VERDICT synthesizes with confidence level
   - Prevents both false positives (flagging good facilities) and false negatives (missing bad ones)

2. **Multi-Advocate** (used in PLAN mode):
   - Each advocate argues for a different deployment option
   - Each presents evidence, coverage estimates, readiness scores
   - System synthesizes tradeoffs and makes a recommendation
   - Planner sees the reasoning behind each option, not just the winner

**Why it matters here**: Mission planning involves genuine tradeoffs (maximum impact vs. maximum safety vs. maximum equity). A single LLM collapses these into one answer. Debate surfaces the tensions explicitly, empowering the planner to make an informed choice.

**Where it runs**: Facility Intelligence Agent (Advocate/Skeptic), Gap Finder/Mission Planner Agent (Multi-Advocate)

### 5.4 Tracing + Human-in-the-Loop

**Judging criterion**: UX — 10%

Every agent step is logged to MLflow, creating a complete audit trail from question to answer. The trace panel in the UI exposes this to the user.

**Implementation**:
- Each agent invocation is an MLflow "run" with logged inputs, outputs, and intermediate reasoning steps
- The trace panel shows: which agents ran, what data they retrieved, what reasoning they applied, what confidence they assigned
- **Human-in-the-Loop**: The planner can push back on any step. "Why did you filter out that facility?" triggers the agent to explain its reasoning and optionally include it back

**Why it matters here**: Healthcare planning decisions must be auditable. A planner can't act on a recommendation they don't understand. Tracing turns the system from an oracle into a transparent reasoning partner.

---

## 6. Data Architecture

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

### Data Pipeline (Pre-computation)

Before the chat works, you need to process the 987 facilities at ingestion time:

```
RAW CSV (987 rows, messy)
        │
        ▼
┌──────────────────────┐
│ STEP 1: Clean & Norm │
│ - Normalize 39 region│
│   values → 16        │
│ - Deduplicate        │
│ - Parse JSON arrays  │
│ - Geocode facilities │
│   (city → lat/lng)   │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ STEP 2: Fingerprint  │
│ - LLM extracts       │
│   structured caps    │
│   from free text     │
│ - Confidence score   │
│   per capability     │
│ - Anomaly flags      │
│ - Upgrade potential  │
└──────────┬───────────┘
           ▼
┌──────────────────────────────────┐
│ STEP 3: Build Knowledge Graph   │
│                                 │
│ [Region]──has──▶[Facility]      │
│ [Facility]──has_cap──▶[Surgery] │
│ [Facility]──has_equip──▶[OR]    │
│ [Facility]──LACKS──▶[NICU]     │
│ [Facility]──could_support──▶[X] │
│ [Region]──desert_for──▶[Cardio] │
└──────────┬───────────────────────┘
           ▼
┌──────────────────────────────────┐
│ STEP 4: Index for Retrieval     │
│ - SQLite: structured fields     │
│ - FAISS: embeddings of free text│
│ - NetworkX: knowledge graph     │
│ - All three queryable by agents │
└──────────────────────────────────┘
```

This runs once, takes ~10 minutes with an LLM for fingerprinting, and then the chat is fast because agents query pre-processed data.

### Index Architecture

| Index | Technology | Content | Queried By |
|---|---|---|---|
| **SQL Database** | SQLite (hackathon) / Databricks (production) | All structured fields — facility metadata, contact info, location, operator type, capacity, specialties | SQL Agent |
| **Vector Index** | FAISS | Embeddings of unstructured text fields — `procedure`, `equipment`, `capability`, `description`. Chunked at field level (not document level) so citations point to specific fields. Metadata filters on: country, region, facility type, specialty. | Vector Search Agent |
| **Knowledge Graph** | NetworkX | Entity-relationship graph — facilities, capabilities, equipment, regions, specialties. Missing edges encode gaps. | Facility Intelligence Agent, Gap Finder Agent |
| **Geospatial Index** | H3 (resolution 7, ~5km² per hex) | Pre-computed attributes per hex: population count, nearest facility per specialty, travel time to nearest facility | Geospatial Engine |

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

## 7. Confidence & Citation Framework

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

## 8. Design Gap Analysis

The agents-and-must-haves document defines a comprehensive question set but has critical gaps when mapped to real planner workflows. Here's what must be addressed:

### Gap 1: No "Readiness Assessment" Concept

The existing design treats facilities as either having or not having a capability. Real planning requires understanding **readiness** — the difference between "this facility has an operating room" and "this facility can support a 3-week ophthalmology mission starting in March."

Readiness includes: reliable electricity, water supply, sterilization equipment, anesthesia capability, post-operative ward space, local clinical staff for handoff, cold chain for medications, patient accommodation for post-op recovery.

**Resolution**: The Facility Intelligence Agent produces a mission-specific readiness report, not just a capability inventory.

### Gap 2: No Transportation/Access Layer

The existing agent design has geospatial queries for distance but no travel time modeling. In Ghana's Upper West Region, this is the difference between useful and useless. The Virtue Foundation itself identified transportation as so critical that they developed motorcycle ambulances for the Sissala District.

76% of Ghana's doctors practice in urban areas. CHPS compounds in rural areas are chronically understaffed and under-equipped. A facility that's "50km away" could be 30 minutes on a paved road from Accra or 4 hours on an unpaved road from Wa.

**Resolution**: The Geospatial Engine uses road network data with quality/speed assumptions, and the Gap Finder Agent uses travel time (not distance) as the primary access metric.

### Gap 3: No NGO Coordination Intelligence

NGO coordination failure is identified as a primary challenge in the Ghana context. Multiple organizations providing overlapping services while entire regions go unserved wastes scarce resources.

**Resolution**: The Gap Finder Agent integrates NGO operational footprints as a first-class data layer, and the Mission Planner Agent explicitly checks for duplication before recommending sites.

### Gap 4: No Temporal Dimension (Permanent vs. Visiting Services)

A facility that has an ophthalmologist visiting twice a year from Accra is fundamentally different from one with a permanent ophthalmology department. For mission planning, this distinction is critical. A facility with visiting services might be ideal for capacity building (train local staff to continue care). A facility with no services at all might need a full mission team.

**Resolution**: The Facility Intelligence Agent classifies services as permanent / visiting / camp-based / referral-only based on linguistic analysis of unstructured text, and this classification feeds into Gap Finder and Mission Planner decisions.

### Gap 5: No "Impact Per Dollar" Reasoning

The core question: "Given limited budgets, where can you maximize impact?" The existing agent design has no mechanism for comparing intervention types (equip a facility vs. train staff vs. place transport vs. send a mission).

**Resolution**: The Mission Planner Agent includes a basic cost-effectiveness framing for its recommendations. "Equipping Facility X with a portable ultrasound ($15K) would enable prenatal screening for a catchment of 40,000 women — estimated 800 screenings/year." vs. "A 2-week surgical mission at Facility Y would perform ~100 cataract surgeries at ~$150/surgery." This isn't a full health economics model, but it gives planners the framing to compare options.

### Gap 6: No Offline/Export Capability

NGO planners need to:
- Generate PDF briefing documents for team meetings
- Export data for donor reports
- Share findings with government partners who don't have system access
- Work offline in areas with poor connectivity

**Resolution**: Every agent output is exportable as a structured report (PDF/DOCX). The Mission Planner Agent produces a complete briefing document. Map visualizations are exportable as images.

---

## 9. MVP Scope & Prioritization

### Phase 1: Hackathon MVP

| Component | Scope | Rationale |
|---|---|---|
| Supervisor Agent | Intent classification + routing for 3 modes (explore/verify/plan) | Everything depends on correct routing |
| SQL Agent | Text-to-SQL for structured queries against SQLite | Foundational — every other agent depends on data access |
| Vector Search Agent (Self-RAG) | Self-reflective retrieval over unstructured fields | Core IDP innovation; powers EXPLORE mode |
| Facility Intelligence Agent (with debate) | GraphRAG verification + Advocate/Skeptic debate | Core differentiator; powers VERIFY mode |
| Knowledge Graph | NetworkX graph built at ingestion time | Enables GraphRAG, gap detection via missing edges |
| Map + Chat + Trace UI | Next.js frontend with Mapbox, WebSocket chat, trace panel | The product experience judges will evaluate |
| Citation tracking | Field-level source attribution via MLflow | Trust requires transparency |
| Gap analysis via KG traversal | `desert_for` edges + basic population overlay | Realistic for hackathon; shows PLAN mode |

### Phase 2: Post-Hackathon

| Component | Scope | Rationale |
|---|---|---|
| Full Gap Finder Agent | Supply mapping + demand estimation + access modeling | Complete gap analysis pipeline with travel time |
| Full Mission Planner Agent | Site ranking + readiness checklists + multi-advocate debate | The "last mile" from intelligence to action |
| Travel time modeling | Road network integration, isochrone generation | Upgrades distance to access — critical for rural planning |
| NGO overlap layer | NGO operational footprints + duplication detection | Coordination value |
| PDF/DOCX export | Mission briefings, donor reports | Practical workflow integration |

### Phase 3: Scale

| Component | Scope | Rationale |
|---|---|---|
| Temporal service classification | Permanent vs. visiting vs. camp detection | Deeper intelligence |
| Cross-source corroboration | Multi-source verification scoring | Higher confidence data |
| External data integration | GBD disease burden, demographic projections | Demand-side estimation |
| Multi-country expansion | Beyond Ghana to VF's other operational countries | Scale impact |

---

## 10. Technical Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend** | Next.js | Reactive map + chat + trace panel requires a real framework; no throwaway work |
| **Map** | Mapbox GL JS (dark style) | Vector tiles, reactive to chat commands, low bandwidth |
| **Chat Transport** | WebSocket | Real-time streaming of agent responses |
| **Backend** | FastAPI | Async Python, WebSocket support, lightweight |
| **Agent Orchestration** | LangGraph | Native support for agent graphs, state management, conditional routing |
| **LLM (Primary)** | Claude (Anthropic API) | Best for nuanced medical reasoning and structured outputs |
| **LLM (Preprocessing)** | GPT-4o-mini (optional) | Cost-effective for data pipeline fingerprinting step |
| **Vector Store** | FAISS | Lightweight, fast, embeddable — ideal for single-country dataset |
| **Embeddings** | OpenAI text-embedding-3-small or BGE-large | Cost-effective with good retrieval quality |
| **Knowledge Graph** | NetworkX | Python-native, sufficient for 987 facilities, fast traversal |
| **SQL Database** | SQLite (hackathon) / Databricks (production) | Zero infra cost for hackathon; abstract query layer for easy swap |
| **Geospatial** | H3 (Uber) + OSRM (routing) | Hexagonal grid for aggregation; OSRM for travel time |
| **Population Data** | WorldPop + H3 aggregation | Pre-compute population per hex for fast queries |
| **Experiment Tracking** | MLflow | Agent step tracing, citation chain logging, trace panel data |
| **Export** | python-docx + reportlab | PDF/DOCX generation for briefing documents |

---

## 11. Success Metrics

### Technical Metrics

| Metric | Target | Measurement |
|---|---|---|
| **Must-Have query accuracy** | >85% correct answers on the 15 Must-Have questions from the agent spec | Evaluated on a test set of queries with known-correct answers |
| **Anomaly detection precision** | >70% of flagged facilities confirmed as genuinely suspicious on manual review | Spot-check by VF clinical staff |
| **False positive rate (facility verification)** | <20% of flagged facilities turn out to be legitimate on ground verification | Tracked over mission cycles |

### Impact Metrics

| Metric | Target | Measurement |
|---|---|---|
| **Planning time reduction** | Reduce mission site selection from weeks → hours | Time-to-decision tracking |
| **Mission effectiveness** | >90% of missions report facility met expectations set by system | Post-mission survey |
| **Coverage gap reduction** | Increase % of missions going to previously unserved regions | Year-over-year geographic analysis |
| **Resource coordination** | Reduce reported NGO service duplication in target regions | Partner survey |

### User Metrics

| Metric | Target | Measurement |
|---|---|---|
| **Planner adoption** | 5+ active NGO planning teams using the system within 6 months | Usage tracking |
| **Query-to-action rate** | >30% of system interactions lead to a concrete planning action | Follow-up tracking |
| **Trust calibration** | Users report confidence levels align with actual data reliability | User feedback surveys |

---

## 12. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **FDR data is too stale** | High | Medium | Surface staleness prominently; prioritize re-scraping for high-demand regions; allow user-submitted updates post-mission |
| **Text-to-SQL produces wrong queries** | Medium | High | Show generated SQL; allow user correction; maintain curated query templates for common questions |
| **Users over-trust the system** | High | High | Mandatory confidence labels; "verify on ground" warnings for all Medium/Low confidence outputs; never present as ground truth |
| **Facility Intelligence flags legitimate facilities** | Medium | Medium | Frame all flags as "data suggests" not "facility is"; always recommend verification; allow facility operators to respond |
| **Travel time model is inaccurate** | High | Medium | Use conservative assumptions; clearly state that travel times are estimates; recommend local validation |
| **System used to justify decisions already made** | Medium | Low | Design outputs to challenge assumptions, not just confirm them; include counter-indicators in reports |

---

## Appendix A: Must-Have Question Coverage

Mapping from the 15 Must-Have questions to VirtueCommand's architecture:

| # | Question | Agent(s) | SOTA Technique |
|---|---|---|---|
| 1.1 | How many hospitals have cardiology? | SQL Agent | — |
| 1.2 | Hospitals in [region] that perform [procedure]? | SQL Agent + Vector Search | Self-RAG |
| 1.3 | What services does [Facility] offer? | Vector Search Agent | Self-RAG |
| 1.4 | Clinics in [Area] that do [Service]? | Vector Search Agent | Self-RAG |
| 1.5 | Region with most [Type] hospitals? | SQL Agent | — |
| 2.1 | Hospitals treating [condition] within [X] km? | SQL Agent + Geospatial Engine | — |
| 2.3 | Largest cold spots for critical procedure? | Gap Finder Agent | GraphRAG |
| 3.1 | Facility capability verification? | Facility Intelligence Agent | GraphRAG + Debate |
| 3.4 | Cross-source corroboration? | Facility Intelligence Agent | GraphRAG |
| 4.4 | Unrealistic procedures relative to size? | Facility Intelligence Agent | Advocate/Skeptic Debate |
| 4.7 | Correlated facility characteristics? | SQL Agent + Facility Intelligence | GraphRAG |
| 4.8 | High breadth with minimal infrastructure? | Facility Intelligence Agent | Advocate/Skeptic Debate |
| 4.9 | Things that shouldn't move together? | Facility Intelligence Agent | GraphRAG (co-occurrence) |
| 6.1 | Where is workforce for [specialty] practicing? | SQL Agent + Gap Finder | GraphRAG |
| 7.5 | Procedures depending on very few facilities? | SQL Agent + Gap Finder | GraphRAG |
| 7.6 | Oversupply vs. scarcity by complexity? | Gap Finder Agent | GraphRAG |
| 8.3 | Gaps where no NGOs work despite need? | Gap Finder Agent | GraphRAG + Debate |

All 15 must-have questions are covered. All 4 hackathon judging criteria are addressed through the mapped SOTA techniques.

## Appendix B: Hackathon Judging Criteria Mapping

| Criterion | Weight | How VirtueCommand Addresses It | Key Demo Moment |
|---|---|---|---|
| **Innovative Data Processing (IDP)** | 30% | Self-RAG in Vector Search Agent: self-reflective retrieval that catches referral mentions, aspirational language, and query gaps. LLM-powered fingerprinting in data pipeline. | EXPLORE mode: show the self-reflection loop filtering false positives in real time via trace panel |
| **Technical Accuracy** | 35% | GraphRAG knowledge graph with anomaly detection. Advocate/Skeptic debate for facility verification. Co-occurrence validation. Confidence scoring framework. | VERIFY mode: show a facility with suspicious claims being debated by Advocate/Skeptic agents, with graph evidence |
| **Social Impact** | 25% | Multi-Advocate debate for deployment planning. Gap analysis via knowledge graph traversal. Cost-effectiveness framing. Medical desert identification. | PLAN mode: show the 3-option deployment analysis with tradeoff visualization and coverage estimates |
| **User Experience** | 10% | MLflow tracing → trace panel. Reactive map. Human-in-the-loop push-back. Chat-driven interaction (no manual map operation). Citations on every claim. Low-bandwidth design. | Click "Trace Log" to expand full reasoning chain. Push back on a recommendation and watch the agent re-reason. |
