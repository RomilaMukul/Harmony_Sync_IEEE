# HarmonySync — Claim Verification Report

**Audit Date:** 2026-10-16  
**Auditor:** Senior Implementation Auditor (AI-assisted)  
**Source Materials:** Phases 2–6 audit reports; full source inspection of all .py files  
**Paper Under Review:** HarmonySync_Paper_Fixed.docx

> **INTEGRITY NOTE:** No source files were modified during this audit. All defects and findings are derived from read-only inspection of the implementation and pre-existing audit artifacts.

---

## Legend

| Status | Meaning |
|---|---|
| **VERIFIED** | Claim is accurate and supported by source code and/or test evidence |
| **PARTIALLY VERIFIED** | Claim is partially accurate; caveats or corrections required |
| **CONTRADICTED** | Claim is directly contradicted by source code or test output |
| **UNVERIFIED** | Claim cannot be confirmed from available evidence; experiment required |
| **NOT APPLICABLE** | Claim is structural/formatting |

---

## Section 1 — Title / Abstract Claims

| Claim ID | Claim | Section | Source Evidence | Observed Behavior | Status | Required Correction |
|---|---|---|---|---|---|---|
| C-001 | System is "real-time" (implied) | Title/Abstract | resolver_service/main.py:33 | 2-sec inactivity sliding window; NOT real-time | CONTRADICTED | Use "near-real-time with 2-second inactivity window" |
| C-002 | "EWMA-based on-device pre-aggregation" | Abstract | aggregator/engine.py:91 | mean_val = round(total_val / len(field_events), 2) — plain arithmetic mean; no alpha parameter anywhere | CONTRADICTED | Replace with "sliding-window arithmetic mean aggregation" |
| C-003 | Causal vector-clock conflict resolution | Abstract | resolver_service/resolver.py:42-61 | vector_clock_dominates() correct; find_causally_dominant() returns None when mixed concurrency+dominance exist; dominated updates NOT pruned | PARTIALLY VERIFIED | State pruning defect exists in 3-update mixed scenarios |
| C-004 | "Delta-only synchronization" for offline recovery | Abstract | vehicle/head_unit.py:80-106 | Calls GET /preferences/latest returning FULL snapshot JSON | CONTRADICTED | Replace with "full-snapshot version reconciliation on vehicle reconnect" |
| C-005 | Privacy-preserving: raw events never leave device | Abstract | aggregator/privacy.py:56-82 | assert_no_raw_data_leaked() enforces invariant; tested in Tests 4-5 (PASSED) | VERIFIED | No correction needed |

---

## Section 2 — Introduction Claims

| Claim ID | Claim | Section | Source Evidence | Observed Behavior | Status | Required Correction |
|---|---|---|---|---|---|---|
| C-006 | System supports phone, laptop, in-vehicle head unit | Intro | resolver_service/models.py:6 | SourceType = Literal["phone","car","laptop"]; simulators for all three | VERIFIED | None |
| C-007 | Confidence weights: Car=0.9, Phone=0.5, Laptop=0.4 | Intro | resolver_service/models.py:8-12 | CONFIDENCE_WEIGHTS dict confirmed with these values | VERIFIED | None |
| C-008 | Weights are enforced/assigned by the system | Intro/Design | resolver_service/resolver.py:77 | Weights taken from client UpdateEvent.confidence_weight; CONFIDENCE_WEIGHTS NEVER imported in resolver.py | CONTRADICTED | "Current prototype trusts client-supplied weight values without server-side enforcement" |
| C-009 | Python 3.11 environment | Implementation | requirements.txt; Phase 2 | requirements.txt has no Python version pin; actual runtime was Python 3.14.2 | CONTRADICTED | Correct to Python 3.14.2; note requirements.txt has no version constraint |

---

## Section 3 — Architecture Claims

| Claim ID | Claim | Section | Source Evidence | Observed Behavior | Status | Required Correction |
|---|---|---|---|---|---|---|
| C-010 | Three-layer architecture: Edge/Cloud Resolver/Vehicle | Architecture | aggregator/, resolver_service/, vehicle/ | All three layers exist | VERIFIED | None |
| C-011 | MQTT transport via Eclipse Mosquitto | Architecture | docker-compose.yml; mosquitto.conf | Mosquitto v2 on port 1883; allow_anonymous true; no TLS | VERIFIED (with caveats) | Add: "anonymous access; no TLS or ACL in current prototype" |
| C-012 | PostgreSQL cloud persistence | Architecture | resolver_service/db.py:20-23 | PostgreSQL 16 on port 5434; verified in Phase 2 | VERIFIED | None |
| C-013 | SQLite vehicle-side cache | Architecture | vehicle/cache.py:28-34 | preferences_cache table: version, snapshot, synced_at — no user_id column | PARTIALLY VERIFIED | Add: "no multi-user partitioning; single-user per database file" |
| C-014 | 2-second buffer window | Architecture | resolver_service/main.py:54,121 | Sliding inactivity timeout; timer resets on every new arrival; high-frequency streams delay flush indefinitely | PARTIALLY VERIFIED | "2-second inactivity sliding window (starvation risk)" |

---

## Section 4 — Algorithm Claims

| Claim ID | Claim | Section | Source Evidence | Observed Behavior | Status | Required Correction |
|---|---|---|---|---|---|---|
| C-015 | EWMA with smoothing factor alpha | Algorithm | aggregator/engine.py:88-102 | Line 91: mean_val = round(total_val / len(field_events), 2); no alpha; no prior-value smoothing | CONTRADICTED | Remove EWMA equations; replace with arithmetic mean formula |
| C-016 | Vector clock dominance correctly defined | Algorithm | resolver_service/resolver.py:21-39 | Correctly implemented; missing keys treated as 0; Tests 1-4 PASSED | VERIFIED | None |
| C-017 | Causal dominance selects single globally dominant update | Algorithm | resolver_service/resolver.py:42-61 | Correct for 2-update case; Test 8 PASSED | PARTIALLY VERIFIED | Add scope limitation: "only when one update dominates ALL others simultaneously" |
| C-018 | Weighted average formula for numeric concurrent updates | Algorithm | resolver_service/resolver.py:115-118 | Formula: sum(w*v)/sum(w) — correct implementation | VERIFIED | None |
| C-019 | Dominated updates excluded before weighted average | Algorithm | resolver_service/resolver.py:90-128 | NOT IMPLEMENTED; 3-update scenario A/B/C where B>A and B||C causes all three to enter pool; actual=47.14 expected=62.22 | CONTRADICTED | Disclose defect; document actual vs expected values from Phase 4 |
| C-020 | Categorical tie-broken by timestamp | Algorithm | resolver_service/resolver.py:124 | max() by (weight, timestamp); identical timestamps are buffer-order dependent (non-deterministic) | PARTIALLY VERIFIED | Add: "identical-timestamp tie-breaking is input-order dependent" |

---

## Section 5 — Implementation Claims

| Claim ID | Claim | Section | Source Evidence | Observed Behavior | Status | Required Correction |
|---|---|---|---|---|---|---|
| C-021 | MQTT publish with QoS 1 | Implementation | aggregator/publisher.py:17,30; main.py:107 | QoS 1 confirmed | VERIFIED | Add caveat about duplicate weight inflation on QoS 1 re-delivery |
| C-022 | Resilient publish on disconnect | Implementation | aggregator/publisher.py:29-35 | Silent discard when broker unreachable; no local queue; returns False with warning log | CONTRADICTED | "Pre-aggregated delta silently discarded when MQTT broker unreachable; no local retry mechanism" |
| C-023 | Buffer safely persisted before drain | Implementation | resolver_service/main.py:61,82-88 | Buffer popped on line 61 BEFORE persist_snapshot() on line 82; DB failure = permanent data loss | CONTRADICTED | Disclose: "Known data-loss defect: buffer drained before database commit" |
| C-024 | Atomic version allocation | Implementation | resolver_service/db.py:77-86 | Non-atomic SELECT then +1; concurrent flushes for same user cause PK collision | CONTRADICTED | Disclose: "Non-atomic version allocation; concurrent flushes may cause primary key collision" |
| C-025 | Vehicle cache stores user_id | Implementation | vehicle/cache.py:28-34 | No user_id column in preferences_cache table | CONTRADICTED | "Vehicle cache does not store user_id; single-user per database file assumed" |
| C-026 | Vector clock preserved in MergedSnapshot | Implementation | resolver_service/resolver.py:98-128; models.py:27 | Vector clock NOT in MergedSnapshot; persisted separately in device_vector_clocks table | CONTRADICTED | "Vector clock maintained per device in device_vector_clocks; not embedded in preference snapshots" |
| C-027 | Privacy guard prevents raw event leakage | Implementation | aggregator/privacy.py:56-82 | Guard enforced; Tests 4-5 PASSED | VERIFIED | None |
| C-028 | Simulated vs live telemetry | Implementation | vehicle/playback.py; demo/run_demo.py | Synthetic UpdateEvent objects with hardcoded values; no real music player or sensor integration | CONTRADICTED | Label explicitly as "simulated playback using synthetic preference values" |

---

## Section 6 — Results Claims

| Claim ID | Claim | Section | Source Evidence | Observed Behavior | Status | Required Correction |
|---|---|---|---|---|---|---|
| C-029 | 22 tests pass: 14 resolver + 8 preaggregation | Results | Phase 2 terminal output | 22 collected, 22 passed, 7.55s; Python 3.14.2, pytest 9.1.1 | VERIFIED | Add full execution context |
| C-030 | Tests prove causal pruning correctness | Results (implied) | test_resolver.py:test_8 | Test 8 only covers 2-update scenario; no 3-device mixed test exists | CONTRADICTED | "Suite does not cover 3-device mixed-dominance-and-concurrency; confirmed defect in untested path" |
| C-031 | Causal defect: actual=47.14, expected=62.22 | Results | reproduce_causal_defect.py; Phase 4 | All 6 input permutations yield 47.14; expected with correct pruning is 62.22; absolute error = 15.08 (24.2%) | VERIFIED (reproduction) | Include with inputs, formula, and scope disclaimer |
| C-032 | Weight spoofing: phone with 99.0 overrides car at 0.9 | Results | test_security_audit.py; Phase 6 | Numeric output = 99.37; categorical = 'hardstyle'; formula verified | VERIFIED (controlled test) | Include with full test setup and note |
| C-033 | Performance/latency measurements | Results | Entire codebase | NO latency measurement exists anywhere | UNVERIFIED | Remove all performance claims; mark [AUTHOR ACTION REQUIRED] |

---

## Defect Summary Table

| ID | Defect | Severity | Phase | Code Status |
|---|---|---|---|---|
| D-01 | Causal pruning failure in 3-update mixed scenarios | HIGH | 4, 5 | PRESENT — unfixed |
| D-02 | Arithmetic mean instead of claimed EWMA | HIGH | 3, 2 | PRESENT — unfixed |
| D-03 | Client-controlled confidence weights (no server enforcement) | CRITICAL | 6 | PRESENT — unfixed |
| D-04 | Silent data loss on MQTT disconnect | HIGH | 3 | PRESENT — unfixed |
| D-05 | Buffer drained before DB commit (data loss on DB failure) | CRITICAL | 3, 6 | PRESENT — unfixed |
| D-06 | Non-atomic version allocation race condition | HIGH | 3, 2 | PRESENT — unfixed |
| D-07 | Vehicle cache lacks user_id (multi-user collision risk) | MEDIUM | 3 | PRESENT — unfixed |
| D-08 | Vector clock not stored in MergedSnapshot | MEDIUM | 3 | PRESENT — unfixed |
| D-09 | Recovery uses full snapshot, not delta | MEDIUM | 3 | PRESENT — unfixed |
| D-10 | Non-deterministic categorical tie-breaking on identical timestamps | MEDIUM | 5 | PRESENT — unfixed |
| D-11 | Misleading audit tag on zero-weight fallback | LOW | 5 | PRESENT — unfixed |
| D-12 | Anonymous MQTT broker; no TLS or ACL | HIGH | 6 | PRESENT — unfixed |
| D-13 | Negative and unbounded confidence weights accepted | HIGH | 6 | PRESENT — unfixed |
| D-14 | Unbounded numeric field values (no range validation) | MEDIUM | 6 | PRESENT — unfixed |
| D-15 | Inactivity-window starvation risk | MEDIUM | 3 | PRESENT — unfixed |
