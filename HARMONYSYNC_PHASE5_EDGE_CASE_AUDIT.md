# HARMONYSYNC — PHASE 5 CONFLICT-RESOLUTION EDGE-CASE AUDIT REPORT

**Audit Date:** 2026-10-12  
**Project Path:** `D:\projects\HarmonySync-main\HarmonySync-main`  
**Execution Context:** Read-only edge-case audit. Application source files and baseline test files remain unmodified.  
**Supporting Experiment:** `audit_edge_cases.py` (executed in-memory without network side-effects).

---

## 1. Scope & Inspected Source Files

1. `resolver_service/resolver.py`: Core resolution functions (`vector_clock_dominates`, `find_causally_dominant`, `group_updates_by_field`, `resolve_updates`).
2. `resolver_service/models.py`: Data models (`UpdateEvent`, `MergedSnapshot`, `CONFIDENCE_WEIGHTS`).
3. `tests/test_resolver.py`: Existing baseline unit & integration tests (`test_1` to `test_14`).
4. `audit_edge_cases.py`: Deterministic test harness executing edge cases N1–N9 and C1–C5.

---

## 2. Numeric Conflict-Resolution Edge Cases (N1–N9)

| Case ID | Scenario Description | Inputs / Clocks / Weights | Expected Mathematical Behavior | Actual Implemented Behavior | Audit Tag Emitted | Defect Status |
|---|---|---|---|---|---|---|
| **N1** | Single update only | $v_1=75.0, w_1=0.5, \text{clock}=\{p:1\}$ | Output: $75.0$ | Output: $75.0$ | `single_source` | **PASS** |
| **N2** | Two concurrent updates, positive weights | $v_1=75.0, w_1=0.5, \text{clock}=\{p:1\}$<br>$v_2=45.0, w_2=0.4, \text{clock}=\{l:1\}$ | $\frac{75(0.5) + 45(0.4)}{0.5 + 0.4} = \mathbf{61.67}$ | Output: $61.67$ | `concurrent_numeric_weighted_avg` | **PASS** |
| **N3** | Two concurrent updates, identical values | $v_1=75.0, w_1=0.5, \text{clock}=\{p:1\}$<br>$v_2=75.0, w_2=0.4, \text{clock}=\{l:1\}$ | Output: $75.0$ | Output: $75.0$ | `concurrent_numeric_weighted_avg` | **PASS** |
| **N4** | Two updates, one causally dominates | $v_1=45.0, w_1=0.4, \text{clock}=\{l:1\}$<br>$v_2=85.0, w_2=0.5, \text{clock}=\{p:2, l:1\}$ | $v_2$ dominates $v_1$. Output: $\mathbf{85.0}$ | Output: $85.0$ | `causal_dominance` | **PASS** |
| **N5** | Three updates: 1 obsolete, 2 maximal | $A: v_A=20.0, w_A=0.5, \text{clock}=\{p:1, l:0\}$<br>$B: v_B=80.0, w_B=0.5, \text{clock}=\{p:2, l:0\}$<br>$C: v_C=40.0, w_C=0.4, \text{clock}=\{p:0, l:1\}$ | Prune $A$. Average $\{B, C\}$:<br>$\frac{80(0.5) + 40(0.4)}{0.9} = \mathbf{62.22}$ | Averages $\{A, B, C\}$:<br>$\frac{20(0.5) + 80(0.5) + 40(0.4)}{1.4} = \mathbf{47.14}$ | `concurrent_numeric_weighted_avg` | **CONFIRMED DEFECT** (Stale update included) |
| **N6** | Equal weights, identical timestamps | $v_1=60.0, w_1=0.5, t=T$<br>$v_2=80.0, w_2=0.5, t=T$ | $\frac{60(0.5) + 80(0.5)}{1.0} = \mathbf{70.0}$ | Output: $70.0$ | `concurrent_numeric_weighted_avg` | **PASS** |
| **N7** | Zero or non-positive total weight | $v_1=60.0, w_1=0.0$<br>$v_2=80.0, w_2=0.0$ | Fallback to latest or safe default; do not label as weighted avg. | Falls back to `float(candidates[-1].value)` ($80.0$). Labels as `concurrent_numeric_weighted_avg`. | `concurrent_numeric_weighted_avg` | **PARTIAL DEFECT** (Misleading audit tag on non-weighted fallback) |
| **N8** | Disjoint clock keys (unseen devices) | $v_1=50.0, \text{clock}=\{p:1\}$<br>$v_2=70.0, \text{clock}=\{custom:1\}$ | Treated as concurrent ($50(0.5)+70(0.5) = \mathbf{60.0}$) | Output: $60.0$ | `concurrent_numeric_weighted_avg` | **PASS** (Missing keys treated as 0) |
| **N9** | Duplicate delivery (QoS 1 retry) | $v_1=75.0, w_1=0.5$ (Phone)<br>$v_2=40.0, w_2=0.4$ (Laptop delivered twice) | Deduplicate by `(device_id, vector_clock)`. Expected: $59.44$ | Sums duplicate into weight: $\frac{75(0.5) + 40(0.4) + 40(0.4)}{1.3} = \mathbf{53.46}$ | `concurrent_numeric_weighted_avg` | **CONFIRMED RISK** (Weight inflated by duplicate) |

---

## 3. Categorical Conflict-Resolution Edge Cases (C1–C5)

| Case ID | Scenario Description | Inputs / Clocks / Weights | Expected Behavior | Actual Implemented Behavior | Audit Tag Emitted | Defect Status |
|---|---|---|---|---|---|---|
| **C1** | Concurrent updates, different weights | $g_1=\text{'jazz'}, w_1=0.9$ (Car)<br>$g_2=\text{'rock'}, w_2=0.5$ (Phone) | Highest weight wins: $\text{'jazz'}$ | Output: $\text{'jazz'}$ | `concurrent_categorical_highest_weight` | **PASS** |
| **C2** | Equal weights, different timestamps | $g_1=\text{'pop'}, w_1=0.5, t_1=T$<br>$g_2=\text{'lofi'}, w_2=0.5, t_2=T+5s$ | Latest timestamp wins: $\text{'lofi'}$ | Output: $\text{'lofi'}$ | `concurrent_categorical_highest_weight` | **PASS** |
| **C3** | Equal weights AND identical timestamps | $g_A=\text{'alpha'}, w=0.5, t=T$<br>$g_B=\text{'beta'}, w=0.5, t=T$ | Deterministic documented tie-breaker (e.g. `device_id`). | In-memory buffer order dependent:<br>Order $[A, B] \to \text{'alpha'}$<br>Order $[B, A] \to \text{'beta'}$ | `concurrent_categorical_highest_weight` | **CONFIRMED DEFECT** (Non-deterministic tie-break) |
| **C4** | Obsolete categorical update with higher weight | $A: \text{'jazz'}, w=0.9, \text{clock}=\{car:1\}$<br>$B: \text{'lofi'}, w=0.5, \text{clock}=\{car:2\}$ ($B > A$)<br>$C: \text{'rock'}, w=0.6, \text{clock}=\{phone:1\}$ | Prune $A$. Between maximal updates $B (0.5)$ and $C (0.6)$, $C$ wins: $\mathbf{'rock'}$ | Obsolete update $A$ not pruned. $A$ has weight $0.9 > 0.6$. Output: $\mathbf{'jazz'}$ | `concurrent_categorical_highest_weight` | **CONFIRMED CRITICAL DEFECT** (Obsolete update overrides newer updates) |
| **C5** | Duplicate categorical delivery | $g_1=\text{'rock'}, w=0.5$ delivered twice | Highest weight selection is idempotent: $\text{'rock'}$ | Output: $\text{'rock'}$ | `concurrent_categorical_highest_weight` | **PASS** |

---

## 4. Confirmed Defects vs Potential Risks

### Confirmed Defects (Mathematically & Experimentally Proven)
1. **Causal Pruning Failure in Both Numeric and Categorical Resolvers (N5 & C4):**
   * Whenever a buffered window contains both a causal supersession ($B > A$) and a concurrent update ($B \parallel C$), `find_causally_dominant()` returns `None`.
   * In numeric mode (N5), obsolete update $A$ ($20.0$) distorts the output value from $62.22$ down to $47.14$.
   * In categorical mode (C4), if obsolete update $A$ had a higher confidence weight than the maximal updates ($0.9 > 0.6$), obsolete update $A$ **wins outright**, clobbering both its own dominating successor $B$ and concurrent update $C$!
2. **Non-Deterministic Categorical Tie-Breaking on Identical Timestamps (C3):**
   * When weights and ISO timestamps collide, `max()` in Python returns the first encountered element. The winner depends strictly on array insertion order.
3. **Misleading Audit Tagging on Non-Positive Weight Fallback (N7):**
   * When `total_weight <= 0`, line 120 falls back to `float(field_candidates[-1].value)` (last element in array), yet emits audit tag `"concurrent_numeric_weighted_avg"` despite performing no weighting.

### Potential Architecture & Ingestion Risks
1. **Numeric Weight Inflation via Redelivery (N9):**
   * If an update event is redelivered over MQTT QoS 1 or retried via HTTP, it is appended to the buffer as an independent candidate, duplicating its weight in the weighted average sum.
2. **Missing Weight & Value Range Validation:**
   * `UpdateEvent` Pydantic model defines `confidence_weight: float = 0.5` without `gt=0` constraints. Negative weights can cause arithmetic underflows or invert value directions.

---

## 5. Test Evidence & Command Execution

1. **Edge-Case Reproduction Command:**
   ```powershell
   python audit_edge_cases.py
   ```
   * Result: Exited with code 0. Demonstrated N5 discrepancy ($47.14 \ne 62.22$), C3 order flip (`alpha` vs `beta`), and C4 obsolete override (`jazz` over `rock`).

2. **Baseline Regression Verification Command:**
   ```powershell
   python -m pytest tests/test_resolver.py tests/test_preaggregation.py -v
   ```
   * Result: **22 passed in 6.68 seconds**.
   * Confirmation: Clean read-only audit; zero impact on existing test suite.

---

## 6. Recommended Regression Tests for Phase 12

When implementing fixes in Phase 12, the following automated regression tests must be added to `tests/test_resolver.py`:

1. `test_causal_pruning_numeric_multi_update`: Assert $\{A(20, w=0.5, c=\{p:1\}), B(80, w=0.5, c=\{p:2\}), C(40, w=0.4, c=\{l:1\})\} \implies 62.22$.
2. `test_causal_pruning_categorical_multi_update`: Assert $\{A('jazz', w=0.9, c=\{c:1\}), B('lofi', w=0.5, c=\{c:2\}), C('rock', w=0.6, c=\{p:1\})\} \implies 'rock'$.
3. `test_categorical_deterministic_tie_breaker`: Assert equal weight and timestamp resolves deterministically regardless of `[A, B]` vs `[B, A]` input order (e.g. tie-broken by `device_id`).
4. `test_duplicate_update_deduplication`: Assert identical `(device_id, vector_clock)` updates within the same buffer window are deduplicated before computing weighted average.
