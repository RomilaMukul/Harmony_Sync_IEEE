# HARMONYSYNC — PHASE 2 BASELINE TEST REPORT

**Date:** 2026-10-12  
**Project Path:** `D:\projects\HarmonySync-main\HarmonySync-main`  
**Execution Context:** Clean baseline audit without application modifications or package upgrades.

---

## 1. Environment Details

* **Operating System:** Windows (Platform: win32)
* **Python Runtime:** Python 3.14.2 (`C:\Python314\python.exe`)
* **Test Runner:** pytest 9.1.1 (pluggy 1.6.0)
* **Active Plugins:** anyio 4.14.2
* **Installed Core Packages:**
  * `fastapi`: 0.141.1
  * `uvicorn`: 0.52.4
  * `paho-mqtt`: 2.1.0
  * `sqlalchemy`: 2.0.52
  * `psycopg2-binary`: 2.9.12
  * `pydantic`: 2.13.5
  * `requests`: 2.34.2
* **Version Policy Observation:** The paper explicitly claimed "Python 3.11", but no version constraint is pinned in `requirements.txt`. The test suite executed successfully under Python 3.14.2.

---

## 2. Infrastructure Status

Prior to test execution, local container infrastructure and network sockets were actively inspected and verified:

| Service | Target Port | Container Name | Container Image | Actual Verified Status | Verification Evidence |
|---|---|---|---|---|---|
| **Mosquitto MQTT Broker** | `1883` | `arc-mosquitto-1` | `eclipse-mosquitto:2` | **ACTIVE / REACHABLE** | Socket connected; Paho MQTT published test message with `mid: 1` successfully. |
| **PostgreSQL 16** | `5434` (mapped to 5432) | `music-sync-postgres` | `postgres:16-alpine` | **ACTIVE / REACHABLE** | SQLAlchemy connection confirmed: `sync_user` connected to `music_sync_db` running PostgreSQL 16.15. |
| **Docker Compose Config** | `docker-compose.yml` | N/A | Defined services: `mqtt-broker`, `postgres` | **CONSISTENT** | Port mappings (1883, 5434) match application connection strings in `resolver_service/db.py`. |

*Note: The containers were already running on the host. No destructive commands (`docker compose down -v`, volume purges, or table drops) were executed.*

---

## 3. Exact Test Command and Execution Results

### Command Executed:
```powershell
python -m pytest tests/test_resolver.py tests/test_preaggregation.py -v
```

### Execution Metrics:
* **Total Tests Collected:** 22
* **Passed:** 22
* **Failed:** 0
* **Skipped:** 0
* **Errors:** 0
* **Duration:** 7.55 seconds

### Raw Terminal Output:
```text
============================= test session starts =============================
platform win32 -- Python 3.14.2, pytest-9.1.1, pluggy-1.6.0 -- C:\Python314\python.exe
cachedir: .pytest_cache
rootdir: D:\projects\HarmonySync-main\HarmonySync-main
plugins: anyio-4.14.2
collecting ... collected 22 items

tests/test_resolver.py::test_1_identical_clocks_not_dominant PASSED      [  4%]
tests/test_resolver.py::test_2_strictly_greater_dominates PASSED         [  9%]
tests/test_resolver.py::test_3_incomparable_clocks_concurrent PASSED     [ 13%]
tests/test_resolver.py::test_4_unseen_device_key PASSED                  [ 18%]
tests/test_resolver.py::test_5_concurrent_numeric_weighted_average PASSED [ 22%]
tests/test_resolver.py::test_6_concurrent_categorical_highest_weight PASSED [ 27%]
tests/test_resolver.py::test_7_equal_weights_categorical_tie_broken_by_timestamp PASSED [ 31%]
tests/test_resolver.py::test_8_causal_dominance PASSED                   [ 36%]
tests/test_resolver.py::test_9_single_source_update PASSED               [ 40%]
tests/test_resolver.py::test_10_end_to_end_mqtt_and_postgres_round_trip PASSED [ 45%]
tests/test_resolver.py::test_14_automatic_buffer_flusher_loop_timeout PASSED [ 50%]
tests/test_resolver.py::test_11_vehicle_head_unit_offline_playback_from_cache PASSED [ 54%]
tests/test_resolver.py::test_12_vehicle_reconnect_sync_recovery_with_real_postgres PASSED [ 59%]
tests/test_resolver.py::test_13_comparison_lww_vs_weighted_merge PASSED  [ 63%]
tests/test_preaggregation.py::test_1_compute_local_delta_from_baseline PASSED [ 68%]
tests/test_preaggregation.py::test_2_multi_event_aggregation_cycle PASSED [ 72%]
tests/test_preaggregation.py::test_3_buffer_cleared_and_state_updated_after_cycle PASSED [ 77%]
tests/test_preaggregation.py::test_4_privacy_guard_passes_valid_payload PASSED [ 81%]
tests/test_preaggregation.py::test_5_privacy_guard_catches_raw_data_leakage PASSED [ 86%]
tests/test_preaggregation.py::test_6_backward_compatibility_with_unmodified_resolver PASSED [ 90%]
tests/test_preaggregation.py::test_7_numeric_averaging_across_samples PASSED [ 95%]
tests/test_preaggregation.py::test_8_categorical_mode_and_latest_selection PASSED [100%]

============================= 22 passed in 7.55s ==============================
```

---

## 4. Test Coverage: Real Services vs Test Doubles / Mocks

The test suite does not use third-party mocking libraries (`unittest.mock`), but rather a mix of pure in-memory unit tests, local SQLite file databases, and real network integration tests against the live Mosquitto broker and PostgreSQL database:

| Test Identifier | Test Target | Execution Mode | Services Contacted |
|---|---|---|---|
| `test_resolver.py::test_1` | Clock dominance (identical) | **Unit** | None (in-memory dicts) |
| `test_resolver.py::test_2` | Clock dominance (strictly greater) | **Unit** | None (in-memory dicts) |
| `test_resolver.py::test_3` | Clock dominance (concurrent) | **Unit** | None (in-memory dicts) |
| `test_resolver.py::test_4` | Clock dominance (unseen device) | **Unit** | None (in-memory dicts) |
| `test_resolver.py::test_5` | Numeric weighted average | **Unit** | None (in-memory Pydantic models) |
| `test_resolver.py::test_6` | Categorical highest weight | **Unit** | None (in-memory Pydantic models) |
| `test_resolver.py::test_7` | Categorical timestamp tie-break | **Unit** | None (in-memory Pydantic models) |
| `test_resolver.py::test_8` | 2-update Causal dominance | **Unit** | None (in-memory Pydantic models) |
| `test_resolver.py::test_9` | Single source passthrough | **Unit** | None (in-memory Pydantic models) |
| `test_resolver.py::test_10` | E2E Update $\to$ Buffer $\to$ DB $\to$ MQTT | **Real Integration** | **Live Mosquitto (1883) + Live PostgreSQL (5434)** |
| `test_resolver.py::test_14` | Background 2-sec flusher loop | **Real Integration** | **Live Mosquitto (1883)** + Background Thread |
| `test_resolver.py::test_11` | Head unit offline playback | **Local SQLite** | Temporary SQLite DB file (`test_cache.db`) |
| `test_resolver.py::test_12` | Reconnect sync recovery | **Real Integration** | **Live PostgreSQL (5434)** + Temporary SQLite DB |
| `test_resolver.py::test_13` | LWW vs Weighted Merge proof | **Unit / Comparison** | None (in-memory Pydantic models) |
| `test_preaggregation.py::test_1` | Local delta computation | **Unit** | None (in-memory state) |
| `test_preaggregation.py::test_2` | Multi-event burst aggregation | **Unit** | None (in-memory state) |
| `test_preaggregation.py::test_3` | Buffer clear & state update | **Unit** | None (in-memory state) |
| `test_preaggregation.py::test_4` | Privacy guard valid pass | **Unit** | None (in-memory Pydantic model) |
| `test_preaggregation.py::test_5` | Privacy guard leakage block | **Unit** | None (in-memory Pydantic model) |
| `test_preaggregation.py::test_6` | Backward compatibility | **Unit** | None (in-memory models $\to$ resolver) |
| `test_preaggregation.py::test_7` | Arithmetic mean sample averaging | **Unit** | None (in-memory raw events) |
| `test_preaggregation.py::test_8` | Categorical mode selection | **Unit** | None (in-memory raw events) |

---

## 5. Failure and Defect Analysis (Why `22 passed` is Incomplete Proof)

Although pytest returned exit code `0` (`22 passed`), a rigorous engineering inspection reveals that the existing tests **mask critical application defects** by omitting adversarial and realistic multi-device test cases:

### A. The 3-Update Causal Dominance Blindspot
* **Test in Suite:** `test_8_causal_dominance` only tests **2 updates** where Car dominates Laptop ($B > A$).
* **Actual Code Defect:** In `resolver_service/resolver.py:42-61`, `find_causally_dominant(candidates)` requires a single update to dominate **all** candidates. When 3 updates arrive ($A=\{p:1\}, B=\{p:2\}, C=\{l:1\}$), $B$ dominates $A$, but $C$ is concurrent with $B$. Because $B$ does not dominate $C$, `find_causally_dominant()` returns `None`. The resolver then averages $A, B,$ and $C$ together! Obsolete update $A$ is erroneously averaged into the final volume!
* **Conclusion:** The test suite passes only because it never tests a 3-device scenario containing both dominance and concurrency.

### B. The EWMA vs Arithmetic Mean Discrepancy
* **Claim in Paper:** "EWMA-based on-device pre-aggregation".
* **Test in Suite:** `test_preaggregation.py::test_7` asserts `expected_mean = round(sum(raw_vals) / len(raw_vals), 2)` — explicitly asserting an **arithmetic mean**!
* **Conclusion:** The test passes because the test itself expects an arithmetic mean, confirming that EWMA does not exist in the codebase despite the paper's claim.

### C. Client Confidence Weight Spoofing Blindspot
* **Test in Suite:** `test_5` and `test_6` feed hardcoded confidence weights (`0.5`, `0.9`) inside `UpdateEvent`.
* **Actual Code Defect:** The cloud resolver accepts `UpdateEvent.confidence_weight` directly from the client payload without validating it against `CONFIDENCE_WEIGHTS`. No test in the suite tests whether a malicious client submitting `confidence_weight: 99.0` is rejected or sanitized.

### D. Single-Update E2E Test Masking Multi-User Version Race Conditions
* **Test in Suite:** `test_10` tests a single update from a single device for a single synthetic user.
* **Actual Code Defect:** Database version allocation (`get_latest_version(db, user_id) + 1`) in `resolver_service/db.py:77` lacks pessimistic row locks or atomic sequence increments. Concurrent flushes for the same user will generate identical versions and crash on primary key collision.

---

## 6. Comparison with Paper Test-Count Claims

* **Paper Claim:** "An automated suite of 14 core resolver tests and 8 pre-aggregation tests".
* **Actual Implementation:**
  * `tests/test_resolver.py`: Exactly 14 test functions (numbered `test_1` through `test_14`).
  * `tests/test_preaggregation.py`: Exactly 8 test functions (`test_1` through `test_8`).
  * Total Collected: **22 test functions**.
* **Distinction:**
  * There are **no parameterized test cases** (each test function is a single execution).
  * There are **3 real integration tests** (`test_10`, `test_14`, `test_12`), **1 local SQLite test** (`test_11`), and **18 pure unit/in-memory tests**.

---

## 7. Recommended Next Steps for Phase 3

1. **Phase 3:** Formally trace the update pipeline across all schemas, identifying exact field transformations and failure-handling boundaries.
2. **Phase 4 & 5:** Write independent test scripts (without altering the original codebase) to reproduce the 3-update vector clock failure, weight tampering vulnerability, and missing EWMA implementation.
3. **Phase 12 (After Full Audit):** Prepare targeted fixes to filter dominated candidates in `resolver.py`, enforce server-side confidence weights, and correct the research paper claims.
