# Healthcare Intelligence Platform — Product Specification
## A Multi-Agent System for NGO Healthcare Planning in Resource-Constrained Settings

**Version**: 1.0 — February 2026  
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

That is what we are building.

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

## Part 3: System Architecture

### Architecture Philosophy

The agents-and-must-haves document defines 59 questions across 11 categories. Many of these are analytically interesting but don't directly drive the five core planner decisions listed above. Our architecture prioritizes the questions that support real decisions.

**Design principles**:
- Every agent must be tied to a decision the user needs to make
- Agents communicate via structured contracts, not vague "messages"
- Every output carries a confidence score and citation chain
- The system must degrade gracefully — if one agent fails, the others still work
- Natural language in, actionable answer + map + citations out

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE LAYER                       │
│  Natural Language Chat │ Map View │ Mission Planner │ Export  │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  SUPERVISOR      │
                    │  (Intent Router) │
                    └───┬──┬──┬──┬──┬─┘
            ┌───────────┘  │  │  │  └───────────┐
            ▼              ▼  ▼  ▼              ▼
    ┌──────────────┐  ┌───────┐ ┌─────────┐  ┌──────────────┐
    │ FACILITY     │  │ DATA  │ │ GAP     │  │ MISSION      │
    │ INTELLIGENCE │  │ QUERY │ │ FINDER  │  │ PLANNER      │
    │ AGENT        │  │ AGENT │ │ AGENT   │  │ AGENT        │
    └──────┬───────┘  └───┬───┘ └────┬────┘  └──────┬───────┘
           │              │          │               │
    ┌──────▼──────────────▼──────────▼───────────────▼───────┐
    │                  SHARED SERVICES LAYER                   │
    │  Medical Reasoning │ Geospatial Engine │ Citation Tracker│
    └──────────────────────────┬──────────────────────────────┘
                               │
    ┌──────────────────────────▼──────────────────────────────┐
    │                     DATA LAYER                           │
    │  FDR (Structured) │ Vector Index │ External Data Cache   │
    └─────────────────────────────────────────────────────────┘
```

---

### Agent Definitions

#### 1. Supervisor Agent (Intent Router)

**Purpose**: Classify user intent and route to the right agent or agent combination. Not a reasoning agent — a dispatcher.

**Inputs**: User's natural language query + conversation history.

**Processing**:
- Classifies query into one of five decision categories (mission targeting, facility verification, resource allocation, coordination/deduplication, access/transport)
- Determines whether the query requires a single agent or multi-agent orchestration
- For complex queries, decomposes into sub-tasks and assigns to agents in sequence or parallel
- Maintains conversation state for follow-up queries

**Outputs**: Routing decision — which agent(s), in what order, with what parameters.

**Failure mode**: Misroutes a query. Mitigation: if an agent returns low-confidence results, Supervisor re-routes to an alternative agent and asks the user for clarification.

**Why it exists**: Without it, the user would need to know which subsystem to query. The Supervisor turns any question into a routed task.

---

#### 2. Data Query Agent (Text-to-SQL + Vector Search)

**Purpose**: Answer factual questions about facilities, NGOs, and their attributes by querying structured data or performing semantic search over unstructured fields.

**Inputs**: Structured query parameters from Supervisor (entity type, filters, geographic scope, specialty, etc.)

**Processing**:
- For structured queries (counts, comparisons, rankings): translates to SQL via Databricks Genie / Text-to-SQL against the FDR schema
- For unstructured queries (what services does Facility X offer?): performs vector search with metadata filtering over `procedure`, `equipment`, and `capability` fields
- Handles hybrid queries by combining SQL results with vector search results
- Returns raw data with source field citations

**Outputs**: Structured result set with row-level citations (facility name, field, source text).

**Validation**: Results are sanity-checked — e.g., if a query returns 0 hospitals in a region with known population >500K, flag as potentially incomplete data rather than "no facilities."

**Failure mode**: Text-to-SQL generates incorrect query. Mitigation: the agent shows the generated SQL to the user and allows correction. Vector search returns irrelevant results. Mitigation: confidence thresholding + fallback to keyword search.

**Covers must-have questions**: 1.1, 1.2, 1.3, 1.4, 1.5, 4.7

---

#### 3. Facility Intelligence Agent (Verification & Anomaly Detection)

**Purpose**: Assess whether a facility's claimed capabilities are credible, and surface anomalies that suggest misrepresentation or incomplete data.

This is the agent that transforms raw data into trustworthy intelligence. It is the critical differentiator of this platform.

**Inputs**: Facility record (structured + unstructured fields), triggered either by user query ("Can Hospital X support our mission?") or by batch verification scan.

**Processing**:

*Capability Consistency Checks*:
- **Procedure ↔ Equipment alignment**: Does the facility claim procedures that require equipment it doesn't list? Example: claims cataract surgery but no operating microscope, phacoemulsification machine, or A-scan ultrasound → flag.
- **Capability ↔ Infrastructure alignment**: Claims ICU capability but lists capacity of 15 beds and no ventilators → flag.
- **Breadth vs. depth anomaly**: Claims 200 procedures with 2 doctors → flag. Uses statistical benchmarking: procedures-per-doctor ratios, equipment-per-specialty ratios.
- **Linguistic signal analysis**: Parses unstructured text for operational vs. aspirational language. "Dr. Agyeman performs vitrectomy every Wednesday" (high confidence) vs. "We offer comprehensive retinal services" (low confidence). Detects patterns: "visiting," "camp," "twice yearly," "in collaboration with" → flags as potentially non-permanent services.

*Co-occurrence Validation*:
- Maintains a knowledge graph of what should co-occur. A facility claiming general surgery should have: anesthesia capability, blood supply or bank access, reliable electricity (generator or grid), sterilization equipment, post-operative care capacity.
- Scores each facility on a "capability completeness index" per claimed specialty.

*Cross-source Corroboration*:
- Checks how many independent sources support a claim. A procedure mentioned on the facility's website, in an NGO mission report, AND in a government registry has higher confidence than one mentioned only on Facebook.

**Outputs**: Facility verification report with:
- Overall confidence score (0-100)
- Per-capability confidence (verified / plausible / unverified / suspicious)
- Specific flags with explanations ("Claims neurosurgery but lists no imaging equipment")
- Missing capability gaps ("To support ophthalmology missions, this facility would need: [list]")
- Citations for every assessment

**Failure mode**: False negatives (flags a legitimate facility as suspicious because data is incomplete). Mitigation: always frame outputs as "data suggests" not "facility is fraudulent." Always recommend on-the-ground verification for flagged facilities.

**Covers must-have questions**: 3.1, 3.4, 4.4, 4.7, 4.8, 4.9

---

#### 4. Gap Finder Agent (Medical Desert Identification)

**Purpose**: Identify geographic regions where healthcare need exceeds available capacity — the "medical deserts" — with specificity by specialty, procedure, and population segment.

This agent answers the fundamental NGO planning question: *Where is the need greatest?*

**Inputs**: Specialty or procedure of interest, geographic scope, population parameters (optional).

**Processing**:

*Supply Mapping*:
- Queries Data Query Agent for all facilities offering the target specialty/procedure within scope
- Filters through Facility Intelligence Agent to remove low-confidence or suspicious claims
- Maps verified supply points geographically

*Demand Estimation*:
- Uses population data (WorldPop, Ghana Statistical Service) by administrative region
- Applies disease burden estimates (GBD, WHO) to estimate expected procedure volume
- Accounts for demographic structure where available (age distribution → cataract prevalence, maternal mortality → EmONC need)

*Access Modeling*:
- Calculates travel time (not just distance) from population centers to nearest verified facility for the target service
- Uses road network data (OpenStreetMap) with adjustments for road quality and seasonal accessibility
- Defines catchment areas using travel time isochrones (30min, 1hr, 2hr, 4hr)
- Identifies populations outside all catchment areas → these are the medical deserts

*NGO Overlap Check*:
- Queries Data Query Agent for NGOs currently operating in identified gap areas
- Classifies NGO presence as permanent (ongoing programs) vs. temporary (mission-based, camps)
- Flags areas with high need AND no NGO presence as highest priority

**Outputs**:
- Ranked list of underserved regions with: population affected, nearest existing service (distance + travel time), confidence in supply data, current NGO presence/absence
- Map visualization with color-coded hexagons (H3) showing supply-demand gap intensity
- Narrative summary explaining the methodology and key findings

**Failure mode**: Overestimates gap because data is incomplete (facility exists but isn't in database). Mitigation: clearly label data completeness per region. "We have data on X% of known facilities in this region."

**Covers must-have questions**: 2.1, 2.3, 6.1, 7.5, 7.6, 8.3

---

#### 5. Mission Planner Agent (Decision Synthesis & Recommendation)

**Purpose**: Synthesize outputs from all other agents into an actionable mission plan or investment recommendation. This is the "last mile" agent that turns intelligence into decisions.

**Inputs**: User's mission parameters (specialty, team size, duration, budget, available dates) + outputs from Gap Finder, Facility Intelligence, and Data Query agents.

**Processing**:

*Candidate Site Ranking*:
- Takes Gap Finder's priority regions
- Cross-references with Facility Intelligence's verified partner facilities in those regions
- Scores each candidate on: unmet need (population × gap severity), facility readiness (capability completeness for the mission type), accessibility (travel time from regional hub), prior mission history (has VF or partners worked here before?), NGO absence (bonus for areas with no current coverage)

*Readiness Assessment*:
- For top-ranked sites, generates a "mission readiness checklist": what the facility has vs. what the mission needs
- Identifies specific gaps that could be filled pre-mission (e.g., "Facility needs backup generator — $3,000 to procure locally")
- Estimates patient volume based on catchment population and procedure prevalence

*Coordination Check*:
- Identifies other NGOs active in the candidate area
- Suggests collaboration opportunities or highlights duplication risks
- References historical mission data if available

**Outputs**:
- Ranked mission site recommendations (top 3-5) with justification
- Per-site readiness report
- Estimated impact metrics (patients served, procedures possible)
- Risk factors and mitigation suggestions
- Exportable briefing document (PDF) for team and donors

**Failure mode**: Recommends a site based on incomplete data that turns out to be unsuitable. Mitigation: every recommendation carries explicit confidence levels and lists assumptions. "This recommendation assumes the facility's claimed operating room is functional — on-the-ground verification recommended."

**Covers must-have questions**: Integrates all categories; directly supports the core planning cycle.

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

## Part 4: What's Missing From the Existing Agent Design

The agents-and-must-haves document defines a comprehensive question set but has critical gaps when mapped to real planner workflows. Here's what must be added:

### Gap 1: No "Readiness Assessment" Concept

The existing design treats facilities as either having or not having a capability. Real planning requires understanding **readiness** — the difference between "this facility has an operating room" and "this facility can support a 3-week ophthalmology mission starting in March."

Readiness includes: reliable electricity, water supply, sterilization equipment, anesthesia capability, post-operative ward space, local clinical staff for handoff, cold chain for medications, patient accommodation for post-op recovery.

**Our addition**: The Facility Intelligence Agent produces a mission-specific readiness report, not just a capability inventory.

### Gap 2: No Transportation/Access Layer

The existing agent design has geospatial queries for distance but no travel time modeling. In Ghana's Upper West Region, this is the difference between useful and useless. The Virtue Foundation itself identified transportation as so critical that they developed motorcycle ambulances for the Sissala District.

76% of Ghana's doctors practice in urban areas. CHPS compounds in rural areas are chronically understaffed and under-equipped. A facility that's "50km away" could be 30 minutes on a paved road from Accra or 4 hours on an unpaved road from Wa.

**Our addition**: The Geospatial Engine uses road network data with quality/speed assumptions, and the Gap Finder Agent uses travel time (not distance) as the primary access metric.

### Gap 3: No NGO Coordination Intelligence

The existing design has Category 8 (NGO Analysis) as "Should Have," but NGO coordination failure is identified as a primary challenge in the Ghana context. Multiple organizations providing overlapping services while entire regions go unserved wastes scarce resources.

**Our addition**: The Gap Finder Agent integrates NGO operational footprints as a first-class data layer, and the Mission Planner Agent explicitly checks for duplication before recommending sites.

### Gap 4: No Temporal Dimension (Permanent vs. Visiting Services)

A facility that has an ophthalmologist visiting twice a year from Accra is fundamentally different from one with a permanent ophthalmology department. The existing agent questions reference this (5.1, 6.4, 6.5, 6.6) but classify them as "Could Have" or "Should Have."

For mission planning, this distinction is critical. A facility with visiting services might be ideal for capacity building (train local staff to continue care). A facility with no services at all might need a full mission team.

**Our addition**: The Facility Intelligence Agent classifies services as permanent / visiting / camp-based / referral-only based on linguistic analysis of unstructured text, and this classification feeds into Gap Finder and Mission Planner decisions.

### Gap 5: No "Impact Per Dollar" Reasoning

The NGO planner challenges document identifies the core question: "Given limited budgets, where can you maximize impact?" The existing agent design has no mechanism for comparing intervention types (equip a facility vs. train staff vs. place transport vs. send a mission).

**Our addition**: The Mission Planner Agent includes a basic cost-effectiveness framing for its recommendations. "Equipping Facility X with a portable ultrasound ($15K) would enable prenatal screening for a catchment of 40,000 women — estimated 800 screenings/year." vs. "A 2-week surgical mission at Facility Y would perform ~100 cataract surgeries at ~$150/surgery." This isn't a full health economics model, but it gives planners the framing to compare options.

### Gap 6: No Offline/Export Capability

The existing design assumes a real-time interactive system. NGO planners need to:
- Generate PDF briefing documents for team meetings
- Export data for donor reports
- Share findings with government partners who don't have system access
- Work offline in areas with poor connectivity

**Our addition**: Every agent output is exportable as a structured report (PDF/DOCX). The Mission Planner Agent produces a complete briefing document. Map visualizations are exportable as images.

---

## Part 5: Data Architecture

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

**SQL Database (Databricks)**: All structured fields from the FDR schema — facility metadata, contact info, location, operator type, capacity, specialties. This is what the Data Query Agent's Text-to-SQL pipeline queries.

**Vector Index (FAISS/LanceDB)**: Embeddings of unstructured text fields — `procedure`, `equipment`, `capability`, `description`, `organizationDescription`, `missionStatement`. Chunked at the field level (not document level) so citations point to specific fields. Metadata filters on: country, region, facility type, specialty.

**Geospatial Index**: H3 hexagonal grid (resolution 7, ~5km² per hex) with pre-computed attributes: population count, nearest facility per specialty, travel time to nearest facility. Enables fast spatial queries without recomputing on every request.

### Data Quality Model

Every data point in the system carries a quality assessment:

```
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

## Part 6: Interaction Design

### Primary Interface: Conversational + Map

The interface is split-pane: natural language chat on the left, interactive map on the right. The map updates in response to conversation context.

**Example interaction flow**:

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

## Part 7: Confidence & Citation Framework

### Confidence Scoring

Every system output carries a confidence level based on:

| Factor | Weight | Scoring |
|---|---|---|
| **Source count** | 30% | How many independent sources support this claim? 1 source = Low, 2+ corroborating = Medium, 3+ with official registry = High |
| **Source quality** | 25% | Official registry > NGO mission report > Facility website > Social media > User-generated |
| **Recency** | 20% | <6 months = Fresh, 6-18 months = Aging, 18+ months = Stale |
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

## Part 8: MVP Scope & Prioritization

### MVP (Build First)

| Component | Scope | Rationale |
|---|---|---|
| Supervisor Agent | Intent classification + routing for 5 decision types | Everything depends on correct routing |
| Data Query Agent | Text-to-SQL for structured queries + vector search for unstructured | Foundational — every other agent depends on data access |
| Facility Intelligence Agent | Capability consistency checks + linguistic signal analysis | The core value proposition — turning claims into intelligence |
| Gap Finder Agent | Supply mapping + basic population overlay (without travel time) | Directly answers "where to go" |
| Map visualization | Facility locations + gap hexagons + region highlighting | Planners think spatially |
| Citation tracking | Field-level source attribution | Trust requires transparency |

### Phase 2 (Add Next)

| Component | Scope | Rationale |
|---|---|---|
| Travel time modeling | Road network integration, isochrone generation | Upgrades distance to access — critical for rural planning |
| Mission Planner Agent | Site ranking + readiness checklists + export | The "last mile" from intelligence to action |
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

## Part 9: Success Metrics

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

## Part 10: Risk Register

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

Mapping from the 15 Must-Have questions in the agent spec to our architecture:

| # | Question | Agent(s) | Notes |
|---|---|---|---|
| 1.1 | How many hospitals have cardiology? | Data Query | Direct SQL |
| 1.2 | Hospitals in [region] that perform [procedure]? | Data Query | SQL + vector search |
| 1.3 | What services does [Facility] offer? | Data Query | Vector search on capability fields |
| 1.4 | Clinics in [Area] that do [Service]? | Data Query | SQL + vector search |
| 1.5 | Region with most [Type] hospitals? | Data Query | SQL aggregation |
| 2.1 | Hospitals treating [condition] within [X] km? | Data Query + Geospatial | SQL + distance calc |
| 2.3 | Largest cold spots for critical procedure? | Gap Finder | Full gap analysis pipeline |
| 4.4 | Unrealistic procedures relative to size? | Facility Intelligence | Ratio analysis + medical reasoning |
| 4.7 | Correlated facility characteristics? | Data Query + Facility Intelligence | Statistical analysis |
| 4.8 | High breadth with minimal infrastructure? | Facility Intelligence | Anomaly detection |
| 4.9 | Things that shouldn't move together? | Facility Intelligence | Co-occurrence validation |
| 6.1 | Where is workforce for [specialty] practicing? | Data Query + Gap Finder | Supply mapping |
| 7.5 | Procedures depending on very few facilities? | Data Query + Gap Finder | Concentration analysis |
| 7.6 | Oversupply vs. scarcity by complexity? | Gap Finder | Supply-demand analysis |
| 8.3 | Gaps where no NGOs work despite need? | Gap Finder | NGO overlay on gap analysis |

---

## Appendix B: Technical Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Orchestration** | LangGraph | Native support for agent graphs, state management, conditional routing |
| **LLM** | Claude (via Anthropic API) or GPT-4 | Medical reasoning quality; tool calling capability |
| **Text-to-SQL** | Databricks Genie | Native integration with FDR data; SQL generation quality |
| **Vector Store** | LanceDB | Lightweight, embeddable, good for single-country datasets |
| **Embeddings** | OpenAI text-embedding-3-small or BGE-large | Cost-effective with good retrieval quality |
| **Geospatial** | H3 (Uber) + OSRM (routing) | Hexagonal grid for aggregation; OSRM for travel time |
| **Population Data** | WorldPop + H3 aggregation | Pre-compute pop per hex for fast queries |
| **Experiment Tracking** | MLflow | Agent step tracing, citation chain logging |
| **Frontend** | Streamlit or Gradio (MVP) → React (production) | Fast prototyping; map integration via Folium/Mapbox |
| **Export** | python-docx + reportlab | PDF/DOCX generation for briefing documents |
| **Data Platform** | Databricks Free Edition | FDR storage, SQL warehouse, ML model serving |
