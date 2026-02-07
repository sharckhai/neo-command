# NEO — Network Emergency Orchestration
**Product name:** NeoCommand

---

## 1. What does this thing do?

Maternal-neonatal emergency care fails because of coordination, not medicine.
Transport professionals spend more cognitive load on logistics — "what buttons to push, who to talk to" — than on clinical decisions.

Nothing exists today for inter-facility critical care transport coordination. Decisions are made in real time without complete information about asset availability, facility capabilities, equipment status, or environmental conditions.

**NeoCommand** is an AI coordination system that orchestrates emergency transport: aircraft selection, equipment configuration, destination matching, stakeholder alerts, and protocol navigation. It starts with the maternal-child dyad (the hardest scenario) and expands to all critical care transfers.

---

## 2. Who is it for?

**Primary users:** Transport coordinators and flight nurses. They run 3-8 transports per shift and are overloaded by logistics, not medicine. They need faster decisions with better information, especially in loud, hands-occupied environments.

**Economic buyers:** Hospital administrators and medical directors. They care about mortality metrics, liability exposure, and the $8M+ in annual write-offs from failed or delayed transfers.

**Target customers:** Well-funded hospitals with a strategic priority around maternal outcomes.

---

## 3. How does it work?

Four AI agents debate trade-offs in real time, then present a unified recommendation:

1. **Dispatch & Access Planner** — mode selection (air vs. ground), aircraft capacity matching, facility capability lookup, weight/space constraint checks
2. **Equipment Monitor** — tracks equipment status, predicts failures, manages mutually exclusive configurations (maternal gear vs. neonatal gear within certified limits)
3. **Communication Coordinator** — eliminates "you have to wait 20 minutes" delays, preps multi-facility teams in parallel, structures handoffs
4. **Clinical Knowledge Agent** — navigates overlapping protocols (aviation, clinical, facility-specific, regulatory), manages dual-protocol complexity for mother and child

**Voice-first interface.** The environment is loud and hands are occupied — screens are secondary.

**Human-in-loop.** Agents recommend with reasoning; the clinician always decides. Non-negotiable for regulatory and clinical correctness.

---

## 4. Key architectural decisions

1. **Multi-agent debate over rules engine** — too many interacting variables (weather, weight, equipment, protocols, availability) for static rules to handle
2. **Voice-first** — the only viable primary modality in a transport environment
3. **Human-in-loop for all clinical decisions** — required by regulation, and correct by principle
4. **Start with the hardest scenario** (maternal-child dyad) — if it handles two patients with conflicting needs, everything simpler is a subset; this is the competitive moat
5. **Software coordination, not hardware** — no FAA certification barriers; hardware innovation is slow and expensive, software is not
6. **Reasoning transparency** — every recommendation shows the constraints considered, trade-offs made, and alternatives rejected
