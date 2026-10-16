"""
Isolated deterministic experiment script to test multi-update causal dominance
and arrival-order permutations against the existing HarmonySync resolver.
DO NOT MODIFY APPLICATION CODE.
"""

import itertools
from datetime import datetime, timezone
from resolver_service.models import UpdateEvent
from resolver_service.resolver import (
    vector_clock_dominates,
    find_causally_dominant,
    group_updates_by_field,
    resolve_updates,
)


def run_experiment():
    print("=" * 80)
    print("PHASE 4: CAUSAL DOMINANCE & MULTI-UPDATE DEFECT REPRODUCTION")
    print("=" * 80)

    t_base = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat()

    # Define Updates A, B, C
    # A: Obsolete update from phone
    # B: Newer update from phone (dominates A)
    # C: Concurrent update from laptop
    update_a = UpdateEvent(
        device_id="phone_01",
        source_type="phone",
        user_id="user_test",
        vector_clock={"phone": 1, "car": 0, "laptop": 0},
        timestamp=t_base,
        confidence_weight=0.5,
        field_updates={"volume": 20.0},
    )

    update_b = UpdateEvent(
        device_id="phone_01",
        source_type="phone",
        user_id="user_test",
        vector_clock={"phone": 2, "car": 0, "laptop": 0},
        timestamp=t_base,
        confidence_weight=0.5,
        field_updates={"volume": 80.0},
    )

    update_c = UpdateEvent(
        device_id="laptop_01",
        source_type="laptop",
        user_id="user_test",
        vector_clock={"phone": 0, "car": 0, "laptop": 1},
        timestamp=t_base,
        confidence_weight=0.4,
        field_updates={"volume": 40.0},
    )

    # 1. Inspect pairwise vector clock relationships
    print("\n--- 1. Pairwise Vector Clock Dominance Inspection ---")
    print(f"B dominates A: {vector_clock_dominates(update_b.vector_clock, update_a.vector_clock)} (Expected: True)")
    print(f"A dominates B: {vector_clock_dominates(update_a.vector_clock, update_b.vector_clock)} (Expected: False)")
    print(f"B dominates C: {vector_clock_dominates(update_b.vector_clock, update_c.vector_clock)} (Expected: False)")
    print(f"C dominates B: {vector_clock_dominates(update_c.vector_clock, update_b.vector_clock)} (Expected: False)")
    print(f"A dominates C: {vector_clock_dominates(update_a.vector_clock, update_c.vector_clock)} (Expected: False)")
    print(f"C dominates A: {vector_clock_dominates(update_c.vector_clock, update_a.vector_clock)} (Expected: False)")

    # 2. Inspect find_causally_dominant() directly
    print("\n--- 2. Helper Inspection: find_causally_dominant([A, B, C]) ---")
    grouped = group_updates_by_field([update_a, update_b, update_c])
    candidates = grouped["volume"]
    print(f"Candidate count in grouped['volume']: {len(candidates)}")
    dominant_candidate = find_causally_dominant(candidates)
    print(f"find_causally_dominant() returned: {dominant_candidate} (Expected: None, because no SINGLE candidate dominates all)")

    # 3. Independent Expected Calculation
    print("\n--- 3. Independent Expected vs Observed Conflict Resolution ---")
    # Expected candidate set after correct pruning: {B, C}
    # Weighted average: (80.0 * 0.5 + 40.0 * 0.4) / (0.5 + 0.4) = (40.0 + 16.0) / 0.9 = 56.0 / 0.9 = 62.22
    expected_val = round((80.0 * 0.5 + 40.0 * 0.4) / (0.5 + 0.4), 2)
    print(f"Expected Candidate Set after Pruning: [B, C]")
    print(f"Expected Result (Pruned B and C only): {expected_val}")

    # Defective Calculation if A is mistakenly averaged:
    # (20.0 * 0.5 + 80.0 * 0.5 + 40.0 * 0.4) / (0.5 + 0.5 + 0.4) = (10.0 + 40.0 + 16.0) / 1.4 = 66.0 / 1.4 = 47.14
    erroneous_unpruned_val = round((20.0 * 0.5 + 80.0 * 0.5 + 40.0 * 0.4) / (0.5 + 0.5 + 0.4), 2)
    print(f"Calculated Defective Result (A + B + C unpruned): {erroneous_unpruned_val}")

    # Current Resolver output:
    actual_result = resolve_updates([update_a, update_b, update_c])
    actual_val = actual_result.fields.get("volume")
    actual_audit = actual_result.audit.get("volume")
    print(f"\nACTUAL Resolver Output: {actual_val}")
    print(f"ACTUAL Resolver Audit Tag: {actual_audit}")
    print(f"Defect Confirmed? {actual_val == erroneous_unpruned_val} (Matches unpruned 47.14 != expected 62.22)")

    # 4. Permutation Test
    print("\n--- 4. All 6 Input Permutations Test ---")
    items = [("A", update_a), ("B", update_b), ("C", update_c)]
    permutation_results = []
    for perm in itertools.permutations(items):
        names = [p[0] for p in perm]
        updates_list = [p[1] for p in perm]
        res = resolve_updates(updates_list)
        val = res.fields.get("volume")
        audit = res.audit.get("volume")
        permutation_results.append((names, val, audit))
        print(f"Permutation {' -> '.join(names)}: volume = {val}, audit = {audit}")

    unique_vals = set(r[1] for r in permutation_results)
    print(f"\nPermutation result count: {len(permutation_results)}")
    print(f"Unique values observed across permutations: {unique_vals}")
    print(f"Is order-dependent? {len(unique_vals) > 1}")


if __name__ == "__main__":
    run_experiment()
