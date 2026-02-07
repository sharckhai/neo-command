# NeoCommand — Data Model

---

## Entities

### Mission
The core entity — one per transport request.

| Field | Type | Notes |
|---|---|---|
| id | string | unique identifier |
| type | enum | `maternal` · `neonatal` · `dyad` |
| acuity | int | 1 (critical) – 5 (stable) |
| status | enum | see status flow below |
| origin_facility | Facility.id | sending facility |
| destination_facility | Facility.id | receiving facility |
| patients | Patient.id[] | 1–2 patients |
| aircraft | Aircraft.id | assigned aircraft |
| crew | CrewMember.id[] | assigned crew |
| equipment_config | Equipment.id[] | loaded equipment set |
| active_protocols | string[] | protocol identifiers in effect |
| created_at | timestamp | |
| timestamps | map | keyed by status — records each transition |

**Status flow:**
`requested → planning → dispatched → en_route → on_scene → transporting → arrived → completed`
Terminal branches: `cancelled`, `aborted` (reachable from any pre-`arrived` status)

---

### Aircraft

| Field | Type | Notes |
|---|---|---|
| id | string | |
| model | enum | `H135` · `H145` · `fixed_wing` |
| capacity_lbs | int | H135 ~750, H145 ~1100 |
| dimensions | object | interior width, height, stretcher clearance |
| location | geo | current lat/lng |
| status | enum | see below |
| maintenance_schedule | object[] | upcoming service windows |
| cost_per_hour | int | operating cost |

**Status flow:** `available → dispatched → in_flight → returning` · also `maintenance`, `grounded`

---

### Equipment

| Field | Type | Notes |
|---|---|---|
| id | string | |
| type | enum | `isolette` · `ventilator` · `fetal_monitor` · `iv_pump` · `nitric_oxide` · `cooling_device` · `hemorrhage_kit` |
| weight_lbs | int | e.g. isolette ~120–150, maternal monitoring ~50–85 |
| mounting_point | string | physical mount location — drives exclusivity |
| battery_pct | int | 0–100, null if not battery-powered |
| o2_level | int | 0–100, null if N/A |
| status | enum | see below |
| excludes | Equipment.id[] | mutual exclusivity (e.g. cooling ↔ nitric oxide on same mount) |

**Status flow:** `ready → loaded → in_use → needs_service`

---

### Facility

| Field | Type | Notes |
|---|---|---|
| id | string | |
| name | string | |
| location | geo | |
| capabilities | string[] | `nicu_level_1`–`nicu_level_4`, `mfm`, `or`, `cath_lab`, `ir` |
| bed_availability | object | by unit — real-time counts |
| protocols | string[] | facility-specific protocol IDs |
| contact_info | object | phone, radio freq, on-call contacts |

---

### Patient

| Field | Type | Notes |
|---|---|---|
| id | string | |
| type | enum | `maternal` · `neonatal` |
| weight_lbs | int | maternal 100–350+, neonatal 1–10 |
| acuity | int | 1–5 |
| conditions | string[] | clinical conditions driving transport |
| gestational_age | int? | weeks — neonatal/prenatal only |
| mission_id | Mission.id | |

---

### CrewMember

| Field | Type | Notes |
|---|---|---|
| id | string | |
| role | enum | `flight_nurse` · `paramedic` · `pilot` |
| certifications | string[] | NRP, STABLE, CAMTS, etc. |
| weight_lbs | int | for weight budget calc |
| status | enum | `available` · `on_mission` · `off_duty` |

---

### Recommendation
Output of agent debate — ties back to a mission.

| Field | Type | Notes |
|---|---|---|
| id | string | |
| mission_id | Mission.id | |
| options | object[] | ranked options with reasoning |
| selected_option | object | the option chosen (null until decision) |
| constraints_evaluated | string[] | weight, time, equipment, protocol, etc. |
| trade_offs | string[] | explicit trade-offs surfaced to clinician |
| reasoning | string | narrative explanation |
| status | enum | `proposed → accepted · rejected · modified` |

---

### Alert

| Field | Type | Notes |
|---|---|---|
| id | string | |
| mission_id | Mission.id | |
| type | enum | `equipment_failure` · `status_change` · `facility_prep` · `protocol_conflict` |
| recipients | string[] | role or individual identifiers |
| message | string | |
| status | enum | `pending → sent → acknowledged` |

---

## Key Relationships

- **Mission** has 1–2 Patients, 1 Aircraft, 1+ CrewMembers, 1 equipment config (set of Equipment), 1+ Recommendations
- **Equipment.excludes[]** references other Equipment (mutual exclusivity — same mounting point)
- **Mission** references origin + destination Facility
- **Recommendation** belongs to exactly one Mission

## Weight Budget (derived, not stored)

```
patients[].weight + equipment_config[].weight + crew[].weight + fuel_estimate
───────────────────────────────────────────────────────────────────────────────
                        vs. aircraft.capacity_lbs
```

Result: `fits` | `exceeds` (with per-component breakdown).
Fuel estimate is a function of distance and aircraft model.
