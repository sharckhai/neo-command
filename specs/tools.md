# NeoCommand — Tools / API Surface

Organized by agent. Each tool: name, trigger, inputs, output, behavior.

---

## Dispatch & Access Planner

### 1. select_transport_mode
- **Trigger:** New mission created
- **Inputs:** origin, destination, patient acuity, time constraints, weather
- **Output:** Recommended mode (`air_rotor` | `air_fixed` | `ground`) with reasoning
- **Behavior:** Evaluates distance, acuity, time-to-treatment, weather conditions. Air preferred for high-acuity + distance > 30 mi. Ground preferred when weather grounds aircraft or distance < 15 mi. Surfaces trade-offs when answer isn't clear-cut.

### 2. match_aircraft
- **Trigger:** Mode selected as air
- **Inputs:** weight budget result, required dimensions, current fleet status
- **Output:** Ranked list of aircraft options with availability time and fit assessment
- **Behavior:** Filters fleet by status `available`, checks capacity against weight budget, ranks by availability time + proximity to origin. Flags if no aircraft fits — triggers split-transport evaluation.

### 3. calculate_weight_budget
- **Trigger:** Patients + equipment config + crew assigned
- **Inputs:** patients[].weight, equipment_config[].weight, crew[].weight, distance (for fuel estimate), aircraft model
- **Output:** Budget breakdown by component, total, fit/exceed per candidate aircraft
- **Behavior:** Sums all components including fuel estimate. Compares against each candidate aircraft's capacity_lbs. Returns per-component breakdown so clinician sees what drives overages.

### 4. find_destination
- **Trigger:** Patient conditions identified
- **Inputs:** required capabilities, patient conditions, origin location, time constraints
- **Output:** Ranked facilities with match score, bed availability, distance, ETA
- **Behavior:** Matches patient needs to facility capabilities. Checks real-time bed availability. For dyad missions, may return two facilities if no single facility meets both maternal + neonatal needs. Flags split-destination scenarios.

### 5. estimate_transport_time
- **Trigger:** Origin, destination, and mode known
- **Inputs:** origin, destination, transport mode, weather, time of day
- **Output:** Time estimate with confidence range and variables affecting estimate
- **Behavior:** Calculates base time from distance + mode speed. Adjusts for weather, airspace restrictions, ground traffic. Returns range (best/expected/worst) with factors that could shift it.

---

## Equipment Monitor

### 6. get_equipment_status
- **Trigger:** Periodic poll (every 60s during mission) or on-demand
- **Inputs:** equipment_config[] (the loaded set)
- **Output:** Per-item status: battery %, O2 level, condition flags
- **Behavior:** Reads telemetry from each device. Returns structured status. Triggers Alert if any value crosses threshold.

### 7. predict_failure
- **Trigger:** Equipment telemetry shows declining trend
- **Inputs:** equipment item, recent telemetry history
- **Output:** Alert with predicted time-to-failure, severity, recommended action
- **Behavior:** Trends battery drain rate, O2 consumption rate. Predicts when threshold will be breached. Proactive alert: "Battery at 40%, estimated 12 min to critical — switch now" vs. reactive "battery dead."

### 8. generate_equipment_config
- **Trigger:** Mission type + patient conditions entered
- **Inputs:** mission type, patient conditions[], aircraft model
- **Output:** Recommended equipment set with per-item weight, total weight, space assessment
- **Behavior:** Maps conditions to required equipment. Checks mutual exclusivity. Calculates total weight/space. If config exceeds aircraft limits, proposes alternatives (drop optional items, suggest larger aircraft).

### 9. check_exclusivity
- **Trigger:** Equipment config proposed or modified
- **Inputs:** proposed equipment set
- **Output:** Conflicts list with explanation (e.g., "cooling_device and nitric_oxide share mounting_point A")
- **Behavior:** Cross-references Equipment.excludes[] and mounting_point fields. Returns conflicts with which items conflict and why. Suggests resolution (which to keep based on patient priority).

---

## Communication Coordinator

### 10. alert_facility
- **Trigger:** Destination selected and mission dispatched
- **Inputs:** facility_id, patient summary, ETA, required preparations
- **Output:** Confirmation status per facility contact
- **Behavior:** Sends structured alert to receiving facility with patient info, ETA, and prep needs. Tracks acknowledgment. Escalates if no acknowledgment within threshold.

### 11. generate_handoff_brief
- **Trigger:** Mission approaching destination (`transporting` status, ETA < 10 min)
- **Inputs:** mission data (patients, conditions, interventions en route, vitals)
- **Output:** Structured handoff document — SBAR format
- **Behavior:** Compiles mission data into handoff brief. Designed for voice delivery in noisy environment. Includes: Situation, Background, Assessment, Recommendation.

### 12. coordinate_teams
- **Trigger:** Facility alerted, teams need parallel preparation
- **Inputs:** facility_id, required teams (OR, NICU, MFM, blood bank, etc.)
- **Output:** Readiness status per team with ETA to ready
- **Behavior:** Contacts each team in parallel. Tracks prep status independently. Surfaces bottleneck team. For dyad missions, coordinates across two specialty teams simultaneously.

### 13. broadcast_status_update
- **Trigger:** Mission status changes
- **Inputs:** mission_id, new status, additional context
- **Output:** Notification delivery status per stakeholder
- **Behavior:** Determines recipients from mission context (crew, facilities, coordinators). Sends status update. All stakeholders get real-time visibility into mission progress.

---

## Clinical Knowledge Agent

### 14. lookup_protocol
- **Trigger:** Patient conditions identified or scenario changes
- **Inputs:** clinical scenario, facility_id (for facility-specific protocols)
- **Output:** Applicable protocols with steps, priority order, source
- **Behavior:** Matches scenario to protocol database. Returns facility-specific protocols where they exist, falls back to standard protocols. Flags when multiple protocols apply.

### 15. check_bypass_eligibility
- **Trigger:** Destination selected
- **Inputs:** patient conditions, destination facility, transport crew certifications
- **Output:** Bypass eligible (yes/no), bypass type (scene-to-OR, direct admit), requirements
- **Behavior:** Evaluates if patient qualifies for ED bypass. Checks crew certifications match requirements. Returns specific bypass pathway with steps and contacts ("who to talk to, what buttons to push").

### 16. manage_dual_protocols
- **Trigger:** Dyad mission — maternal + neonatal conditions present
- **Inputs:** maternal conditions[], neonatal conditions[]
- **Output:** Merged protocol set with conflict resolution and priority ordering
- **Behavior:** Identifies overlapping or conflicting protocol requirements. Resolves conflicts with clinical priority rules. Flags unresolvable conflicts for clinician decision. Example: mag sulfate for mother may affect neonatal resuscitation approach.

### 17. assess_clinical_risk
- **Trigger:** Recommendation proposed, or config changes mid-planning
- **Inputs:** current equipment config, patient conditions, transport plan
- **Output:** Risk flags with severity, alternatives, reasoning
- **Behavior:** Evaluates whether current plan adequately addresses patient needs. Flags gaps (e.g., "no cooling device loaded but patient at risk for HIE"). Suggests specific alternatives with trade-off explanation.

---

## Cross-Agent (Orchestrator)

### 18. run_debate
- **Trigger:** Sufficient mission data entered to generate recommendation
- **Inputs:** mission details (patients, origin, constraints, preferences)
- **Output:** Unified Recommendation with options, trade-offs, reasoning from all 4 agents
- **Behavior:** Each agent evaluates mission from its domain. Agents surface conflicts (e.g., Dispatch says H135 available now, Equipment says config won't fit H135). Orchestrator synthesizes into ranked options with explicit trade-offs. Returns Recommendation entity.

### 19. accept_recommendation
- **Trigger:** Clinician approves recommendation via voice or UI
- **Inputs:** recommendation_id, selected option (if multiple)
- **Output:** Updated Mission with all downstream actions triggered
- **Behavior:** Sets Recommendation.status = `accepted`. Updates Mission with selected aircraft, equipment, destination. Triggers: aircraft dispatch, equipment loading, facility alerts, team coordination.

### 20. override_recommendation
- **Trigger:** Clinician modifies or rejects recommendation
- **Inputs:** recommendation_id, modifications, clinician reasoning
- **Output:** Updated Recommendation, re-evaluated constraints
- **Behavior:** Logs clinician reasoning (required). Re-runs affected constraint checks against modified plan. Surfaces new risks if override introduces them. Does NOT block override — clinician always decides.
