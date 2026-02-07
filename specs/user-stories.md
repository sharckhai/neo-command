# NeoCommand — User Stories

---

## Epic 1: Mission Planning (core flow)

### US-1: Standard transport request
**As a** transport coordinator, **I want to** enter patient info and get a full transport recommendation, **so that** I can dispatch faster with better information.

**Flow:** Coordinator receives call → enters patient type, conditions, acuity, origin → system runs `run_debate` (tools 1–5, 8, 14, 17) → presents unified Recommendation with ranked options, trade-offs, and reasoning → coordinator reviews, calls `accept_recommendation` → Mission status moves to `dispatched`, downstream actions fire.

**Acceptance:** Recommendation appears within 30s of data entry. All constraints (weight, equipment, protocol) are evaluated. Clinician can accept, modify, or reject.

### US-2: Mode selection
**As a** coordinator, **I want** the system to evaluate air vs ground with clear reasoning, **so that** I don't have to make that judgment call with incomplete info.

**Flow:** `select_transport_mode` evaluates distance, acuity, weather, time constraints → returns recommendation with reasoning ("Air recommended: 85 mi distance, acuity 2, clear weather. Ground would add 40 min.") → coordinator confirms or overrides.

**Acceptance:** Reasoning references specific factors. When factors conflict (e.g., weather marginal but acuity critical), trade-off is explicit.

### US-3: Aircraft matching
**As a** coordinator, **I want** the system to find aircraft that fit the weight budget, **so that** I don't manually calculate whether patients + equipment + crew + fuel fit.

**Flow:** `calculate_weight_budget` sums all components → `match_aircraft` filters fleet → returns ranked options ("H145 available in 20 min, within budget by 234 lbs. H135 available now but exceeds by 116 lbs.").

**Acceptance:** Budget shows per-component breakdown. Each candidate shows fit/exceed with margin. If no aircraft fits, system flags and suggests alternatives.

---

## Epic 2: Maternal-Child Dyad (differentiator)

### US-4: Dyad transport planning
**As a** flight nurse, **I want** the system to handle two patients with competing equipment needs, **so that** I get a viable config or a clear split-transport recommendation.

**Flow:** Coordinator enters dyad mission (maternal hemorrhage + premature neonate) → `generate_equipment_config` proposes combined set → `check_exclusivity` flags conflicts → `calculate_weight_budget` checks fit → if budget exceeds, system proposes: (A) larger aircraft with wait time, (B) reduced config with risk flags via `assess_clinical_risk`, (C) split transport with coordination plan.

**Acceptance:** All three options presented when applicable. Trade-offs explicit (time vs capability vs separation). Risk flags attached to reduced configs.

### US-5: Split destination
**As a** coordinator, **I want** the system to coordinate when mother and baby need different facilities, **so that** both get optimal care without coordination falling through cracks.

**Flow:** `find_destination` identifies mother needs MFM at Hospital A, baby needs Level IV NICU at Hospital B → system generates two parallel transport plans → `coordinate_teams` preps both facilities → `alert_facility` sends patient-specific info to each → `broadcast_status_update` keeps all parties synced.

**Acceptance:** Both facilities receive correct patient info. Teams at both facilities tracked to readiness. Single mission view shows both destinations with status.

### US-6: En-route delivery
**As a** flight nurse, **I want** the system to adapt when a delivery happens mid-transport, **so that** the receiving facility is prepared for two patients instead of one.

**Flow:** Crew reports delivery en route → Mission.type updates to `dyad`, new Patient (neonatal) created → `manage_dual_protocols` generates merged protocol set → `assess_clinical_risk` re-evaluates current equipment config → `alert_facility` updates destination with revised patient count and needs → `coordinate_teams` adds NICU team to prep.

**Acceptance:** Destination alerted within 60s of status change. Equipment gaps flagged immediately. Protocol guidance updated for crew in real-time.

---

## Epic 3: Equipment Management

### US-7: Equipment config recommendation
**As a** flight nurse, **I want** the system to propose equipment based on patient conditions, **so that** I don't miss critical gear or load conflicting items.

**Flow:** Patient conditions entered → `generate_equipment_config` maps conditions to equipment → `check_exclusivity` validates no conflicts → returns recommended set with weight totals and any flags.

**Acceptance:** Config covers all patient conditions. Mutual exclusivity conflicts surfaced before loading. Weight impact shown per item.

### US-8: Equipment failure alert
**As a** flight nurse, **I want** proactive alerts when equipment is trending toward failure, **so that** I can act before it's an emergency.

**Flow:** During mission, `get_equipment_status` polls telemetry → `predict_failure` detects battery drain accelerating → Alert created: "Ventilator battery at 38%, estimated 14 min to critical. Recommend switching to backup power now." → Alert.status tracks through `pending → sent → acknowledged`.

**Acceptance:** Alert fires with time-to-failure, not just current level. Recommended action included. Alert tracked to acknowledgment.

### US-9: Config change pre-dispatch
**As a** coordinator, **I want** to recalculate when the clinical situation changes after initial config, **so that** I know if the current plan still works.

**Flow:** Initial config set → clinical update arrives (e.g., baby now needs nitric oxide) → `generate_equipment_config` re-runs → `check_exclusivity` finds conflict with cooling device already loaded → `calculate_weight_budget` re-evaluates → `assess_clinical_risk` flags impact → updated Recommendation presented.

**Acceptance:** Impact of change shown as diff from original plan. New conflicts and weight impact highlighted. Clinician decides whether to accept revised config.

---

## Epic 4: Communication & Coordination

### US-10: Receiving facility prep
**As a** coordinator, **I want** the system to prep all teams at the receiving facility in parallel, **so that** we don't arrive to "wait 20 minutes."

**Flow:** Mission dispatched → `alert_facility` sends structured alert → `coordinate_teams` contacts OR, NICU, blood bank, MFM in parallel → each team reports readiness → bottleneck team surfaced ("Blood bank needs 15 min for crossmatch") → `broadcast_status_update` keeps transport crew informed of facility readiness.

**Acceptance:** All required teams contacted within 2 min of dispatch. Per-team readiness tracked independently. Bottleneck team highlighted with ETA.

### US-11: Structured handoff
**As a** flight nurse, **I want** a handoff brief generated from mission data, **so that** I can deliver it by voice without fumbling through notes.

**Flow:** Mission ETA < 10 min → `generate_handoff_brief` compiles SBAR from mission data (patient demographics, conditions, interventions en route, current vitals, outstanding needs) → brief delivered to crew via voice interface.

**Acceptance:** Brief follows SBAR format. Content pulled from live mission data — no manual entry. Optimized for voice delivery (concise, structured, no jargon ambiguity).

### US-12: Status broadcast
**As a** coordinator, **I want** all stakeholders to get real-time updates as the mission progresses, **so that** nobody is in the dark.

**Flow:** Mission status transitions (e.g., `en_route → on_scene → transporting`) → `broadcast_status_update` fires → all stakeholders (origin facility, destination facility, coordinator, medical director) receive update with context.

**Acceptance:** Updates fire automatically on every status transition. Recipients determined by mission context. No manual "call everyone" step.

---

## Epic 5: Edge Cases & Failures

### US-13: Aircraft unavailable
**As a** coordinator, **I want** the system to search for alternatives when the primary aircraft is down, **so that** I don't waste time calling around manually.

**Flow:** `match_aircraft` returns no available aircraft in home fleet (primary in maintenance) → system expands search to regional network → returns alternatives with availability time, distance, and trade-offs ("Regional partner H145 available in 35 min, 40 mi from origin").

**Acceptance:** Regional search automatic when home fleet exhausted. Options include time/distance trade-offs. Coordinator can accept or request ground evaluation.

### US-14: Weight budget exceeded
**As a** coordinator, **I want** clear options when the dyad config exceeds the available aircraft, **so that** I can make an informed time-vs-capability decision.

**Flow:** `calculate_weight_budget` shows dyad config at 866 lbs → H135 (750 lb capacity) available in 20 min ❌ → H145 (1100 lb capacity) available in 45 min ✓ → system presents: (A) wait for H145 (+25 min), (B) split transport with two H135s, (C) reduce equipment with risk flags → `assess_clinical_risk` evaluates each option.

**Acceptance:** All viable options presented with time impact, risk assessment, and cost implications. Weight breakdown visible per option. Clinician decides.

### US-15: Protocol conflict
**As a** flight nurse, **I want** the system to surface protocol conflicts with options, **so that** I'm not caught between competing requirements.

**Flow:** `lookup_protocol` returns facility-specific protocol → `manage_dual_protocols` detects conflict with standard clinical protocol (e.g., facility requires ED check-in, but patient qualifies for scene-to-OR bypass via `check_bypass_eligibility`) → system presents conflict with options and reasoning → clinician decides.

**Acceptance:** Conflict stated clearly with both protocol sources cited. Options include: follow facility protocol, invoke bypass with justification, escalate to medical director. Decision logged with reasoning.
