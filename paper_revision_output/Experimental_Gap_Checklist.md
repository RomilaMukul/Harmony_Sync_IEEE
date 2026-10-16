# HarmonySync — Experimental Gap Checklist

**Date:** 2026-10-16  
**Purpose:** Prioritized list of experiments needed to close evidence gaps for the revised IEEE paper.

---

## EXP-01 — Causal Pruning Defect Reproduction ✅ COMPLETED

- **Priority:** P1 (CRITICAL)
- **Research Question:** Does find_causally_dominant() correctly handle a 3-update scenario containing both a dominance relationship and a concurrent update?
- **Status:** COMPLETED (Phase 4)
- **Command:** python reproduce_causal_defect.py
- **Inputs:** A={phone:1,val:20.0,w:0.5}, B={phone:2,val:80.0,w:0.5}, C={laptop:1,val:40.0,w:0.4}
- **Actual output:** 47.14 (all 6 permutations)
- **Expected output (correct):** 62.22
- **Absolute error:** 15.08 (24.2%)
- **How to report:** Section VI; Fig. 3; Table with all 6 permutations

---

## EXP-02 — Aggregation Formula Verification ✅ COMPLETED

- **Priority:** P1 (CRITICAL)
- **Research Question:** Does the on-device aggregator implement EWMA or arithmetic mean?
- **Status:** COMPLETED (Phase 3 + test suite)
- **Evidence:** aggregator/engine.py:91: mean_val = round(total_val / len(field_events), 2); test_preaggregation.py:218: expected_mean = round(sum(raw_vals) / len(raw_vals), 2) — test explicitly asserts arithmetic mean
- **Result:** Arithmetic mean confirmed; no EWMA anywhere in codebase
- **How to report:** Table I; Section IV algorithm subsection

---

## EXP-03 — Edge Case Audit (N1–N9, C1–C5) ✅ COMPLETED

- **Priority:** P1
- **Research Question:** Do known edge cases in numeric and categorical resolution expose further defects?
- **Status:** COMPLETED (Phase 5)
- **Command:** python audit_edge_cases.py
- **Key findings:** N5 confirms causal pruning defect (47.14 vs 62.22); C4 confirms categorical causal pruning allows obsolete high-weight update to win; C3 confirms non-deterministic tie-breaking; N7 confirms misleading audit tag on zero-weight fallback
- **How to report:** Section VI edge cases table

---

## EXP-04 — Client Weight Spoofing ✅ COMPLETED

- **Priority:** P1 (CRITICAL)
- **Research Question:** Can a client override server confidence-weight policy by injecting a spoofed weight?
- **Status:** COMPLETED (Phase 6)
- **Command:** python test_security_audit.py
- **Setup:** Car w=0.9 val={genre:'jazz',volume:30.0} vs Phone w=99.0 (spoofed) val={genre:'hardstyle',volume:100.0}
- **Observed output:** genre='hardstyle', volume=99.37
- **Expected (correct):** genre='jazz' (car should dominate by weight), volume weighted correctly
- **How to report:** Section VII (limitations) or Section VI; formula verification included

---

## EXP-05 — Recovery Path Validation ✅ COMPLETED (code-level)

- **Priority:** P2
- **Research Question:** Does vehicle recovery use delta synchronization or full snapshot fetching?
- **Status:** COMPLETED from source code (Phase 3)
- **Evidence:** vehicle/head_unit.py:86: url = f"{resolver_api_url}/users/{self.user_id}/preferences/latest" — single GET returning full snapshot; no delta endpoint exists in resolver_service/main.py
- **How to report:** Section IV (recovery subsection); Fig. 5 (sequence diagram)
- **Limitation:** test_12 confirms reconnect behavior works correctly at the functional level; it does NOT validate bandwidth savings or delta behavior

---

## EXP-06 — Buffer Data Loss on DB Failure ⚠️ PARTIALLY VERIFIED (code-level only)

- **Priority:** P2
- **Research Question:** Are buffered updates lost permanently when the database fails during flush?
- **Status:** PARTIALLY VERIFIED — defect confirmed from source code (main.py:61 pops buffer before line 82 persist); NOT reproduced by injecting a real DB failure
- **Proposed command:** Run test_10 with PostgreSQL stopped mid-flush; observe whether updates are recoverable
- **Risk:** Requires stopping a running container mid-operation; do not run in production environment
- **How to report:** Section VII limitations table (confirmed code-level defect; not experimentally reproduced by forcing DB failure)
- **Author action:** Optionally reproduce by stopping postgres container mid-test and verifying update loss

---

## EXP-07 — Version Allocation Race Condition ❌ NOT REPRODUCED

- **Priority:** P2
- **Research Question:** Do concurrent flushes for the same user_id collide on the primary key?
- **Status:** NOT REPRODUCED experimentally; confirmed as risk from code inspection
- **Why needed:** Paper should not claim atomic versioning
- **Proposed procedure:**
  1. Spawn 2+ concurrent asyncio tasks in a test calling flush_user() for the same user_id simultaneously
  2. Assert whether a primary key constraint violation (IntegrityError) occurs
- **Existing reuse:** test_10 infrastructure (BufferManager, real PostgreSQL); extend with threading
- **How to report:** Section VII as "potential risk confirmed from code inspection; experimental reproduction pending"

---

## EXP-08 — Buffer Inactivity Starvation ❌ NOT REPRODUCED

- **Priority:** P3
- **Research Question:** Can a high-frequency update stream prevent the buffer from ever flushing?
- **Status:** NOT REPRODUCED; inferred from main.py:54 (last_update_time resets on every update)
- **Proposed procedure:**
  1. Submit updates at rate > 0.5 Hz continuously for 10 seconds
  2. Assert that no flush occurs during that period (buffer grows indefinitely)
  3. Stop updates; assert flush occurs within 2.1 seconds
- **How to report:** Section VII as "suspected risk; reproduction pending"

---

## EXP-09 — MQTT Duplicate Weight Inflation ⚠️ PARTIALLY VERIFIED

- **Priority:** P3
- **Status:** PARTIALLY VERIFIED — Phase 5 N9 shows math confirming duplicate inflates weight; not tested against live MQTT QoS 1 re-delivery
- **Evidence:** Phase 5 N9: 53.46 (with duplicate) vs 59.44 (without); confirmed mathematically
- **How to report:** Section VII as "confirmed computational risk; live MQTT re-delivery test pending"

---

## EXP-10 — End-to-End Latency Measurement ❌ NOT STARTED

- **Priority:** P3 (required for any latency claim)
- **Research Question:** What is the end-to-end latency from device update to vehicle cache update under defined conditions?
- **Status:** NO measurement exists anywhere in codebase or audit reports
- **Proposed procedure:**
  1. Timestamp at MQTT publish in DeviceSimulator.publish_update()
  2. Timestamp at VehicleCache.store_snapshot() in HeadUnit._on_message()
  3. Run 30+ trials; record min/median/max/p95
  4. Vary: number of concurrent devices (1, 2, 3); update frequency (1 Hz, 5 Hz)
- **How to report:** If run, include latency table in Section VI; if not run, mark [AUTHOR ACTION REQUIRED] and remove latency claims

---

## EXP-11 — User Isolation Test (Vehicle Cache) ❌ NOT STARTED

- **Priority:** P3
- **Research Question:** Do two users sharing a vehicle head unit (same SQLite file) cause version collision?
- **Status:** NOT TESTED; defect confirmed from schema (no user_id column)
- **How to report:** Section VII limitation

---

## Summary Table

| ID | Experiment | Priority | Status |
|---|---|---|---|
| EXP-01 | Causal pruning defect (A/B/C counterexample) | P1 | ✅ COMPLETED |
| EXP-02 | Aggregation formula (EWMA vs mean) | P1 | ✅ COMPLETED |
| EXP-03 | Edge cases N1–N9, C1–C5 | P1 | ✅ COMPLETED |
| EXP-04 | Client weight spoofing | P1 | ✅ COMPLETED |
| EXP-05 | Recovery path (delta vs full snapshot) | P2 | ✅ COMPLETED (code-level) |
| EXP-06 | Buffer data loss on DB failure | P2 | ⚠️ Code-confirmed; not force-reproduced |
| EXP-07 | Version allocation race condition | P2 | ❌ Not reproduced |
| EXP-08 | Buffer inactivity starvation | P3 | ❌ Not reproduced |
| EXP-09 | MQTT duplicate weight inflation | P3 | ⚠️ Mathematically confirmed; not live-tested |
| EXP-10 | End-to-end latency measurement | P3 | ❌ Not started — REQUIRED to make any latency claim |
| EXP-11 | User isolation / vehicle cache collision | P3 | ❌ Not started |
