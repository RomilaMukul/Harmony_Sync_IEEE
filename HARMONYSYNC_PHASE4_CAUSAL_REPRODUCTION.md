# HARMONYSYNC — PHASE 4 CAUSAL DOMINANCE DEFECT REPRODUCTION

**Audit Date:** 2026-10-12  
**Project Path:** `D:\projects\HarmonySync-main\HarmonySync-main`  
**Test Script:** `reproduce_causal_defect.py` (isolated in-memory test; no production code modified)

---

## 1. Executive Summary

This phase experimentally verified and confirmed the critical distributed-systems defect in the HarmonySync conflict resolver (`resolver_service/resolver.py`).

* **Expected Distributed Systems Behavior:** If update $B$ causally dominates update $A$ ($B > A$), update $A$ is obsolete. If update $C$ is concurrent with $B$ ($B \parallel C$), the active candidate set must be pruned to $\{B, C\}$ before conflict resolution.
* **Actual Implemented Behavior:** The resolver's helper function `find_causally_dominant()` only checks whether a single update dominates **all** other updates. When multiple maximal concurrent updates exist, it returns `None`. The resolver then falls through to weighted averaging across **all unpruned candidates**, mistakenly including the superseded update $A$.
* **Quantitative Impact:**
  * **Expected Merged Value (Pruned candidate set $\{B, C\}$):** `62.22`
  * **Actual Output (Unpruned candidate set $\{A, B, C\}$):** `47.14`
  * **Absolute Error:** `15.08` units (stale signal pulled the merged result down by 24.2%).

---

## 2. Experimental Setup & Test Data

The reproduction experiment was executed entirely in-memory using standard `UpdateEvent` models:

| Update | Device ID | Source Type | Logical Vector Clock | Value (`volume`) | Confidence Weight | Meaning |
|---|---|---|---|---|---|---|
| **A** | `phone_01` | `phone` | `{"phone": 1, "car": 0, "laptop": 0}` | `20.0` | `0.5` | Older phone preference update. |
| **B** | `phone_01` | `phone` | `{"phone": 2, "car": 0, "laptop": 0}` | `80.0` | `0.5` | Newer phone preference update (supersedes A). |
| **C** | `laptop_01` | `laptop` | `{"phone": 0, "car": 0, "laptop": 1}` | `40.0` | `0.4` | Concurrent update from laptop. |

### Execution Command:
```powershell
python reproduce_causal_defect.py
```

---

## 3. Pairwise Vector Clock Relationships

Using the implementation's `vector_clock_dominates(clock_a, clock_b)`:

* `vector_clock_dominates(B, A)` $\to$ `True` ($B$ strictly dominates $A$).
* `vector_clock_dominates(A, B)` $\to$ `False`.
* `vector_clock_dominates(B, C)` $\to$ `False` ($B$ and $C$ are concurrent).
* `vector_clock_dominates(C, B)` $\to$ `False`.
* `vector_clock_dominates(A, C)` $\to$ `False` ($A$ and $C$ are concurrent).
* `vector_clock_dominates(C, A)` $\to$ `False`.

**Conclusion:** The pairwise comparator `vector_clock_dominates()` functions correctly. The defect lies entirely in the candidate selection and pruning logic in `find_causally_dominant()` and `resolve_updates()`.

---

## 4. Helper Inspection: `find_causally_dominant()`

In [resolver_service/resolver.py:42-61](file:///D:/projects/HarmonySync-main/HarmonySync-main/resolver_service/resolver.py#L42-L61):
```python
def find_causally_dominant(candidates: List[FieldCandidate]) -> Optional[FieldCandidate]:
    if not candidates:
        return None

    for candidate in candidates:
        dominates_all = True
        for other in candidates:
            if other is candidate:
                continue
            if not vector_clock_dominates(candidate.vector_clock, other.vector_clock):
                dominates_all = False
                break
        if dominates_all:
            return candidate

    return None
```

* **Candidate count:** 3 (`[A, B, C]`).
* **Evaluation for candidate B:**
  * Compares $B$ against $A$: `dominates(B, A)` is `True`.
  * Compares $B$ against $C$: `dominates(B, C)` is `False`.
  * `dominates_all` set to `False`. Break.
* **Evaluation for candidate C:**
  * Compares $C$ against $A$: `dominates(C, A)` is `False`. Break.
* **Evaluation for candidate A:**
  * Compares $A$ against $B$: `dominates(A, B)` is `False`. Break.
* **Result of `find_causally_dominant(candidates)`:** **`None`**.

---

## 5. Actual vs Expected Conflict Resolution

### Independent Calculation (Correct Causal Pruning)
Under standard causal semantics in distributed systems, any update $x$ for which there exists an update $y$ in the same candidate set such that $y$ causally dominates $x$ ($y > x$) must be eliminated.
* Maximal candidate set: $\text{Maximal}(A, B, C) = \{B, C\}$.
* Weighted Average of maximal set $\{B, C\}$:
  $$\text{Result} = \frac{(80.0 \times 0.5) + (40.0 \times 0.4)}{0.5 + 0.4} = \frac{40.0 + 16.0}{0.9} = \frac{56.0}{0.9} = \mathbf{62.22}$$

### Current Implemented Calculation
Because `find_causally_dominant()` returns `None`, `resolve_updates()` falls through to lines 112–121:
```python
        else:
            all_numeric = all(isinstance(c.value, (int, float)) for c in field_candidates)
            if all_numeric:
                total_weight = sum(c.confidence_weight for c in field_candidates)
                weighted_val = sum(float(c.value) * c.confidence_weight for c in field_candidates) / total_weight
                merged[field_name] = round(weighted_val, 2)
```
* Unpruned candidate set: $\{A, B, C\}$.
* Calculated value:
  $$\text{Result} = \frac{(20.0 \times 0.5) + (80.0 \times 0.5) + (40.0 \times 0.4)}{0.5 + 0.5 + 0.4} = \frac{10.0 + 40.0 + 16.0}{1.4} = \frac{66.0}{1.4} = \mathbf{47.14}$$

### Result Comparison:
* **Expected Result:** `62.22` (Audit: `concurrent_numeric_weighted_avg` across $\{B, C\}$)
* **Actual Output:** `47.14` (Audit: `concurrent_numeric_weighted_avg` across $\{A, B, C\}$)
* **Defect Confirmation:** **CONFIRMED DEFECT.** Obsolete update $A$ was not pruned.

---

## 6. Arrival-Order Permutation Test

All 6 permutations of updates $A, B,$ and $C$ were passed to `resolve_updates()`:

| Permutation Order | Emitted Value (`volume`) | Emitted Audit Tag | Matches Independent Expected? |
|---|---|---|---|
| $A \to B \to C$ | `47.14` | `concurrent_numeric_weighted_avg` | **NO (Defective)** |
| $A \to C \to B$ | `47.14` | `concurrent_numeric_weighted_avg` | **NO (Defective)** |
| $B \to A \to C$ | `47.14` | `concurrent_numeric_weighted_avg` | **NO (Defective)** |
| $B \to C \to A$ | `47.14` | `concurrent_numeric_weighted_avg` | **NO (Defective)** |
| $C \to A \to B$ | `47.14` | `concurrent_numeric_weighted_avg` | **NO (Defective)** |
| $C \to B \to A$ | `47.14` | `concurrent_numeric_weighted_avg` | **NO (Defective)** |

### Permutation Observations:
* **Order Independence:** The numeric result is invariant to buffer order (all yield `47.14`) because arithmetic addition $\sum w_i x_i$ is commutative.
* **Deterministic Inaccuracy:** The algorithm consistently produces the wrong result across all permutations.

---

## 7. Baseline Test Suite Verification (Regression Check)

To ensure no existing code or tests were altered, the baseline test suite was re-executed:

```powershell
python -m pytest tests/test_resolver.py tests/test_preaggregation.py -v
```

### Result:
* **Tests Passed:** 22
* **Failed:** 0
* **Duration:** 6.89s
* **Status:** The existing test suite remains 100% passing because none of the existing 14 tests in `test_resolver.py` cover a 3-update scenario containing both dominance and concurrency.

---

## 8. Root Cause Analysis & Proposed Fix Architecture (For Phase 12)

### Root Cause
The resolver conflates **global dominance** (one update dominates all updates) with **local pairwise dominance** (an update dominates an older update from the same causal lineage).
By only checking if one update dominates *all* updates, it ignores the fact that in distributed systems, updates from different devices are frequently concurrent, while updates within the same device (or causal history) supersede earlier updates.

### Required Algorithmic Correction
Before evaluating conflict resolution (numeric or categorical), the candidate list for each field must be filtered to keep only **maximal candidates**:

```python
# A candidate is kept if and only if NO OTHER candidate strictly dominates it
maximal_candidates = [
    c for c in field_candidates
    if not any(vector_clock_dominates(other.vector_clock, c.vector_clock) for other in field_candidates if other is not c)
]
```

1. If `len(maximal_candidates) == 1`:
   - If `len(field_candidates) == 1`: Audit tag $\to$ `"single_source"`.
   - If `len(field_candidates) > 1`: Audit tag $\to$ `"causal_dominance"` (because all other candidates were dominated).
2. If `len(maximal_candidates) > 1`:
   - If all numeric: Compute weighted average across `maximal_candidates`. Audit tag $\to$ `"concurrent_numeric_weighted_avg"`.
   - If categorical: Compute highest weight across `maximal_candidates`. Audit tag $\to$ `"concurrent_categorical_highest_weight"`.
