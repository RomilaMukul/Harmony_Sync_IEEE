# HarmonySync — Evidence Manifest

**Date:** 2026-10-16  
**Purpose:** Maps every important claim and numerical result in the revised paper to its exact source file, audit artifact, or test output.

---

## Source Code Files Inspected

| File | Path | Role |
|---|---|---|
| engine.py | aggregator/engine.py | On-device aggregation; confirms arithmetic mean NOT EWMA |
| models.py (aggregator) | aggregator/models.py | RawEvent, AggregatorState, DeltaPayload definitions |
| privacy.py | aggregator/privacy.py | Privacy guard implementation |
| publisher.py | aggregator/publisher.py | MQTT publish with QoS 1; silent-discard defect confirmed |
| resolver.py | resolver_service/resolver.py | Conflict resolution; causal pruning defect confirmed |
| models.py (resolver) | resolver_service/models.py | CONFIDENCE_WEIGHTS; UpdateEvent; client-weight source |
| db.py | resolver_service/db.py | PostgreSQL schema; non-atomic version allocation |
| main.py | resolver_service/main.py | FastAPI service; BufferManager; inactivity window; buffer-drain defect |
| cache.py | vehicle/cache.py | SQLite schema; no user_id column confirmed |
| head_unit.py | vehicle/head_unit.py | Recovery via GET /preferences/latest (full snapshot) |
| playback.py | vehicle/playback.py | Simulated playback from local SQLite cache |
| base_client.py | simulators/base_client.py | DeviceSimulator; simulator uses CONFIDENCE_WEIGHTS correctly |
| run_demo.py | demo/run_demo.py | Synthetic demo; hardcoded UpdateEvent values |
| test_resolver.py | tests/test_resolver.py | 14 resolver tests; confirmed content and scope |
| test_preaggregation.py | tests/test_preaggregation.py | 8 pre-aggregation tests; test_7 confirms arithmetic mean assertion |
| reproduce_causal_defect.py | reproduce_causal_defect.py | In-memory reproduction of A/B/C causal pruning defect |
| audit_edge_cases.py | audit_edge_cases.py | N1–N9, C1–C5 edge-case verification |
| test_security_audit.py | test_security_audit.py | Client weight spoofing test |
| docker-compose.yml | docker-compose.yml | Service definitions: Mosquitto v2 port 1883, PostgreSQL 16 port 5434 |
| mosquitto.conf | mosquitto.conf | allow_anonymous true; no TLS |
| requirements.txt | requirements.txt | No Python version pin; package lower bounds only |

---

## Audit Reports Inspected

| Report | File | Key Evidence |
|---|---|---|
| Phase 2 Baseline Report | HARMONYSYNC_PHASE2_BASELINE_REPORT.md | 22 tests passed; Python 3.14.2; pytest 9.1.1; duration 7.55 s; 3 integration + 1 SQLite + 18 unit |
| Phase 3 Pipeline Trace | HARMONYSYNC_PHASE3_PIPELINE_TRACE.md | Full E2E pipeline; 9 failure paths; schema compatibility table; 5 confirmed defects; 3 suspected risks |
| Phase 4 Causal Defect | HARMONYSYNC_PHASE4_CAUSAL_REPRODUCTION.md | A/B/C inputs; all 6 permutations yield 47.14; expected 62.22; absolute error 15.08 (24.2%) |
| Phase 5 Edge Cases | HARMONYSYNC_PHASE5_EDGE_CASE_AUDIT.md | N1–N9, C1–C5; 3 confirmed defects (N5, C4, C3); 2 confirmed risks (N9, N7) |
| Phase 6 Security Audit | HARMONYSYNC_PHASE6_SECURITY_AUDIT.md | 7 vulnerabilities; weight spoofing output volume=99.37, genre='hardstyle'; anonymous MQTT |

---

## Numerical Results — Traceability

| Claim / Result | Value | Source File | Source Line | Audit Phase |
|---|---|---|---|---|
| Test count total | 22 | Phase 2 terminal output | — | Phase 2 |
| Test duration | 7.55 s | Phase 2 terminal output | — | Phase 2 |
| Python version (actual) | 3.14.2 | Phase 2 §1 | — | Phase 2 |
| pytest version | 9.1.1 | Phase 2 §1 | — | Phase 2 |
| Arithmetic mean formula | sum(v)/len(v) | aggregator/engine.py | Line 91 | Phase 3 |
| Confidence weight: car | 0.9 | resolver_service/models.py | Line 9 | Phase 2 |
| Confidence weight: phone | 0.5 | resolver_service/models.py | Line 10 | Phase 2 |
| Confidence weight: laptop | 0.4 | resolver_service/models.py | Line 11 | Phase 2 |
| Causal defect actual output | 47.14 | Phase 4 §5; reproduce_causal_defect.py | — | Phase 4 |
| Causal defect expected (correct) | 62.22 | Phase 4 §5 (manual calculation) | — | Phase 4 |
| Causal defect absolute error | 15.08 (24.2%) | Phase 4 §1 | — | Phase 4 |
| Permutations tested (all defective) | 6/6 | Phase 4 §6 table | — | Phase 4 |
| N5 defect (numeric, same scenario) | 47.14 actual vs 62.22 expected | Phase 5 N5 row | — | Phase 5 |
| C4 defect (categorical: jazz wins incorrectly) | 'jazz' (wrong); 'rock' expected | Phase 5 C4 row | — | Phase 5 |
| C3 non-determinism | alpha vs beta depending on order | Phase 5 C3 row | — | Phase 5 |
| Weight spoofing numeric output | 99.37 | Phase 6 §2 | — | Phase 6 |
| Weight spoofing categorical output | 'hardstyle' | Phase 6 §2 | — | Phase 6 |
| Weight spoofing formula | (30×0.9 + 100×99.0)/(0.9+99.0) = 99.37 | Phase 6 §2 | — | Phase 6 |
| MQTT broker | Eclipse Mosquitto v2 | docker-compose.yml:3; Phase 2 | Line 3 | Phase 2 |
| MQTT port | 1883 | docker-compose.yml:6; mosquitto.conf:1 | Line 6/1 | Phase 2 |
| PostgreSQL version | 16 (16.15) | docker-compose.yml:12; Phase 2 | Line 12 | Phase 2 |
| PostgreSQL port | 5434 | docker-compose.yml:19; db.py:22 | Line 19/22 | Phase 2 |
| Buffer window | 2.0 s (inactivity sliding) | resolver_service/main.py | Line 33 | Phase 3 |
| Buffer flusher poll interval | 0.2 s | resolver_service/main.py | Line 140 | Phase 3 |

---

## Evidence NOT Available (Gaps)

| Missing Evidence | Impact on Paper |
|---|---|
| End-to-end latency measurements | Cannot claim any latency or performance values |
| Throughput benchmarks | Cannot claim scalability |
| Concurrent flush race condition reproduction | Must be disclosed as code-level risk only |
| Live MQTT QoS 1 duplicate injection test | N9 weight inflation remains mathematical rather than live demonstration |
| Production user data or real telemetry | All results are from synthetic inputs; must be labeled accordingly |
| Buffer starvation reproduction | Must be disclosed as inferred risk |
| Multi-user vehicle cache collision test | Must be disclosed as code-level structural defect |
