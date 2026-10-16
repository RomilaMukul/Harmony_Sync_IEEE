# HarmonySync — Figure and Screenshot Placement Plan

**Document:** HarmonySync_IEEE_Revised.docx  
**Date:** 2026-10-16  
**Basis:** Source code inspection, Phase 2–6 audit artifacts, and IEEE two-column formatting conventions.

---

## Overview

Seven figures are proposed for the revised paper. Figures 1–5 can be produced from existing evidence. Figures 6–7 require author action (screenshots or additional experiments).

---

## FIGURE 1 — System Architecture Diagram

- **Figure Number:** Fig. 1
- **Insertion Point:** Section III (System Architecture), after the paragraph introducing the three-layer architecture
- **Marker:** [FIGURE 1 INSERT HERE: Verified HarmonySync three-layer system architecture]
- **Purpose:** Establish the verified component topology for readers
- **Type:** Vector architecture diagram (NOT a screenshot)
- **Components to show:**
  - Layer 1 Edge: Phone/Car/Laptop simulators → AggregatorState → run_aggregation_cycle() → assert_no_raw_data_leaked() → MQTT publish QoS 1
  - Network: Eclipse Mosquitto Broker (port 1883, anonymous)
  - Layer 2 Cloud: FastAPI Resolver Service → BufferManager (2-sec inactivity window) → resolve_updates() → PostgreSQL 16 (port 5434) → MQTT publish users/{id}/preferences
  - Layer 3 Vehicle: HeadUnit MQTT subscriber → VehicleCache (SQLite) → PlaybackEngine.tick()
  - Recovery path: sync_recovery_from_cloud() → GET /preferences/latest (full snapshot)
- **Labels required:** Component names, port numbers, MQTT topic patterns, QoS level, data type at each arrow
- **Caption:** "Fig. 1. Verified HarmonySync system architecture. Three layers communicate via MQTT (Eclipse Mosquitto, port 1883, QoS 1). Vehicle recovery fetches the complete preference snapshot from the REST endpoint, not a delta."
- **Source:** Directly derived from source code; Phase 3 pipeline diagram
- **Evidence exists:** YES (Phase 3 text-based diagram) — must be redrawn as vector for IEEE format
- **Priority:** ESSENTIAL
- **Misleading risk:** Label "anonymous MQTT" clearly; label "full snapshot recovery" clearly

---

## FIGURE 2 — Update Processing Pipeline Sequence

- **Figure Number:** Fig. 2
- **Insertion Point:** Section IV (Implementation), after the subsection describing the aggregation-to-resolution pipeline
- **Marker:** [FIGURE 2 INSERT HERE: Actual update-processing pipeline]
- **Purpose:** Show the exact data transformation steps from raw event to persisted snapshot
- **Type:** Sequence diagram or numbered flowchart
- **Steps to include:**
  1. RawEvent buffer accumulation on device
  2. run_aggregation_cycle(): arithmetic mean (numeric) / mode (categorical)
  3. Vector clock increment: state.vector_clock[source_type] += 1
  4. Privacy gate: assert_no_raw_data_leaked()
  5. MQTT publish: users/{user_id}/updates/{device_id} QoS 1
  6. BufferManager.add_update() → sliding inactivity window reset
  7. buffer_flusher_loop() detects timeout ≥ 2.0 s
  8. resolve_updates(): group by field → find_causally_dominant() → weighted average
  9. get_latest_version() + 1 (non-atomic)
  10. persist_snapshot() to PostgreSQL
  11. MQTT publish: users/{user_id}/preferences QoS 1
  12. HeadUnit._on_message() → VehicleCache.store_snapshot()
- **Label defect boxes:** Step 8 (causal pruning defect), Step 9 (race condition risk), Step 5 (data loss on disconnect)
- **Caption:** "Fig. 2. HarmonySync update-processing pipeline. Italic steps indicate confirmed defects or known risks (Section VII)."
- **Source:** Phase 3 §2 function call map; source code line numbers
- **Evidence exists:** YES — must be created as figure
- **Priority:** ESSENTIAL
- **Misleading risk:** Must label defect points

---

## FIGURE 3 — Causal Pruning Defect Counterexample

- **Figure Number:** Fig. 3
- **Insertion Point:** Section V (Experimental Methodology) or Section VI (Results), after the paragraph describing the A/B/C reproduction
- **Marker:** [FIGURE 3 INSERT HERE: Reproducible causal-pruning counterexample]
- **Purpose:** Visually demonstrate the defect with exact numerical inputs and outputs
- **Type:** Annotated diagram or formatted table (two side-by-side panels)
- **Panel A — Correct behavior:**
  - Show: A={phone:1}, val=20.0, w=0.5; B={phone:2}, val=80.0, w=0.5; C={laptop:1}, val=40.0, w=0.4
  - Show: B dominates A (B > A); B concurrent with C (B || C)
  - Prune A → candidate set = {B, C}
  - Result = (80×0.5 + 40×0.4) / (0.5+0.4) = 56/0.9 = 62.22
- **Panel B — Actual implementation:**
  - find_causally_dominant([A,B,C]) returns None
  - All three enter weighted average pool
  - Result = (20×0.5 + 80×0.5 + 40×0.4) / (0.5+0.5+0.4) = 66/1.4 = 47.14
- **Required annotations:** Vector clock values, dominance arrows, formula, absolute error = 15.08 (24.2%)
- **Caption:** "Fig. 3. Causal pruning defect: three-update scenario. Correct causal semantics require pruning the superseded update A before weighted averaging, yielding 62.22. The current implementation omits this pruning step, yielding 47.14. This result was reproduced for all six input permutations using reproduce_causal_defect.py."
- **Source:** Phase 4 §5; reproduce_causal_defect.py (in-memory execution)
- **Evidence exists:** YES — Phase 4 report documents all values
- **Priority:** ESSENTIAL
- **Misleading risk:** Must clarify this is a controlled in-memory reproduction, not a production measurement

---

## FIGURE 4 — Aggregation Formula Comparison Table

- **Figure Number:** Fig. 4 (or Table I)
- **Insertion Point:** Section IV (Algorithms), after the aggregation subsection
- **Marker:** [FIGURE 4 INSERT HERE: Aggregation formula comparison — claimed vs implemented]
- **Purpose:** Make the EWMA vs arithmetic-mean discrepancy concrete and unambiguous
- **Type:** Formatted two-column table (IEEE Table I style)
- **Columns:** Aspect | Claimed in Paper | Actual Implementation
- **Rows:**
  - Formula | EWMA: S_t = α·x_t + (1-α)·S_{t-1} | Arithmetic mean: v̂ = (1/n)Σr_i
  - Parameter | α ∈ (0,1) (smoothing factor) | n (sample count in window)
  - Memory of prior cycles | YES (S_{t-1} retained) | NO (fresh mean each cycle)
  - Source file | (claimed) | aggregator/engine.py:88–102
  - Test assertion | — | test_preaggregation.py:test_7 asserts arithmetic mean
- **Caption:** "Table I. Claimed versus implemented on-device aggregation formula. The prototype computes a plain per-cycle arithmetic mean; exponential smoothing is absent from the codebase."
- **Source:** aggregator/engine.py:88–102; test_preaggregation.py:218
- **Evidence exists:** YES — source code
- **Priority:** ESSENTIAL
- **Misleading risk:** None if presented as a factual comparison

---

## FIGURE 5 — Test Suite Coverage Summary Table

- **Figure Number:** Table II
- **Insertion Point:** Section V (Experimental Methodology), after the test-suite description
- **Marker:** [FIGURE 5 INSERT HERE: Test suite coverage summary table]
- **Purpose:** Accurately characterize what the 22 tests do and do not cover
- **Type:** Formatted table
- **Columns:** Test ID | Description | Mode | Services Used | Defects Exercised
- **Key rows to include:** Tests 1–9 (unit), Test 10 (E2E with real MQTT+PG), Test 11 (local SQLite), Test 12 (reconnect recovery with real PG), Test 13 (LWW comparison), Test 14 (auto-flush loop)
- **Footer note:** "No test covers 3-device mixed dominance+concurrency (D-01), EWMA behavior (D-02), weight spoofing (D-03), or delta recovery (D-09)."
- **Caption:** "Table II. HarmonySync baseline test suite (22 tests; Python 3.14.2; pytest 9.1.1; 7.55 s). Three tests require live Mosquitto and PostgreSQL. No test exercises the confirmed causal-pruning defect or client-weight spoofing vulnerability."
- **Source:** Phase 2 test coverage table; tests/test_resolver.py; tests/test_preaggregation.py
- **Evidence exists:** YES — Phase 2 report
- **Priority:** ESSENTIAL
- **Misleading risk:** Must include the defect-coverage gap note

---

## FIGURE 6 — Running Application Screenshot (AUTHOR ACTION REQUIRED)

- **Figure Number:** Fig. 4 (renumber if Tables I–II are used)
- **Insertion Point:** Section III (Architecture) or Section V (Methodology), after the demo description
- **Marker:** [FIGURE 6 INSERT HERE: Demo terminal output screenshot — AUTHOR ACTION REQUIRED]
- **Purpose:** Provide visual evidence of the system running
- **Type:** Terminal screenshot
- **Capture instructions:**
  1. Ensure Mosquitto and PostgreSQL containers are running: docker compose up -d
  2. Start the resolver service: uvicorn resolver_service.main:app --reload --port 8000
  3. In a second terminal: python demo/run_demo.py --live
  4. Capture both terminals (resolver log + demo output) in a single clean screenshot
  5. Crop to show: demo scenario output, merged fields, audit trail, and resolver log lines showing buffer flush
  6. Redact no sensitive data (no credentials visible in demo mode)
- **Caption:** "Fig. 4. Representative demo run: HarmonySync resolver executing weighted conflict resolution for concurrent phone, car, and laptop updates. Terminal output from demo/run_demo.py --live against live Mosquitto and PostgreSQL."
- **Evidence exists:** NO — must be captured by author
- **Priority:** OPTIONAL (adds credibility; not mathematically essential)
- **Misleading risk:** Ensure demo uses the known-defective code (do NOT fix defects before screenshot)

---

## FIGURE 7 — Recovery Workflow Diagram (AUTHOR ACTION REQUIRED or create from code)

- **Figure Number:** Fig. 5 (or last figure)
- **Insertion Point:** Section IV (Implementation), after the recovery subsection
- **Marker:** [FIGURE 7 INSERT HERE: Vehicle recovery workflow — full-snapshot reconciliation]
- **Purpose:** Show the actual recovery path; contrast with claimed delta-sync
- **Type:** Simple sequence diagram
- **Steps:**
  1. Vehicle HeadUnit detects reconnect
  2. sync_recovery_from_cloud() called
  3. GET /users/{user_id}/preferences/latest → full JSON snapshot returned
  4. Compare cloud_version > local_version
  5. VehicleCache.store_snapshot(cloud_version, full_snapshot)
  6. PlaybackEngine.tick() reads updated cache
- **Annotation:** "Full snapshot returned (no delta negotiation or incremental patch)"
- **Caption:** "Fig. 5. Vehicle head unit recovery workflow. On reconnect, the head unit fetches the complete latest preference snapshot via REST. No delta synchronization protocol is implemented; all field values are overwritten."
- **Evidence exists:** YES from code (vehicle/head_unit.py:80-106)
- **Priority:** OPTIONAL (strongly recommended given the contradicted delta-sync claim)
- **Misleading risk:** None if described accurately

---

## Figure Status Summary

| Figure | Type | Status | Author Action Required? |
|---|---|---|---|
| Fig. 1 (Architecture) | Vector diagram | Must be created | Redraw from Phase 3 text diagram |
| Fig. 2 (Pipeline) | Sequence diagram | Must be created | Derive from Phase 3 function map |
| Fig. 3 (Causal defect) | Annotated diagram | Evidence exists (Phase 4) | Create visual from Phase 4 data |
| Table I (Aggregation formula) | Table | Evidence exists (source code) | Format for IEEE |
| Table II (Test suite) | Table | Evidence exists (Phase 2) | Format for IEEE |
| Fig. 4 (Demo screenshot) | Terminal screenshot | MISSING | Author must capture |
| Fig. 5 (Recovery diagram) | Sequence diagram | Must be created | Derive from head_unit.py:80-106 |
