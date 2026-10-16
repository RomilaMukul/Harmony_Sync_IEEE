"""
Edge-case audit script for Phase 5.
Tests numeric and categorical resolution edge cases against the current implementation in resolver.py.
DO NOT MODIFY APPLICATION CODE.
"""

from datetime import datetime, timezone
from resolver_service.models import UpdateEvent
from resolver_service.resolver import resolve_updates, vector_clock_dominates


def run_edge_cases():
    print("=" * 80)
    print("PHASE 5: CONFLICT-RESOLUTION EDGE-CASE AUDIT")
    print("=" * 80)
    t1 = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    t2 = datetime(2026, 9, 1, 12, 0, 5, tzinfo=timezone.utc).isoformat()

    # =========================================================================
    # NUMERIC CASES
    # =========================================================================
    print("\n--- NUMERIC EDGE CASES ---")

    # Case N1: One update only
    u1 = UpdateEvent(
        device_id="p1", source_type="phone", user_id="u1",
        vector_clock={"phone": 1}, timestamp=t1, confidence_weight=0.5,
        field_updates={"volume": 75.0}
    )
    res_n1 = resolve_updates([u1])
    print(f"N1 (Single update): volume={res_n1.fields.get('volume')}, audit={res_n1.audit.get('volume')}")

    # Case N2: Two concurrent updates, positive weights
    u2 = UpdateEvent(
        device_id="l1", source_type="laptop", user_id="u1",
        vector_clock={"laptop": 1}, timestamp=t1, confidence_weight=0.4,
        field_updates={"volume": 45.0}
    )
    # Expected: (75*0.5 + 45*0.4)/(0.5+0.4) = (37.5 + 18)/0.9 = 55.5 / 0.9 = 61.67
    res_n2 = resolve_updates([u1, u2])
    print(f"N2 (Two concurrent): volume={res_n2.fields.get('volume')}, audit={res_n2.audit.get('volume')}")

    # Case N3: Two updates with identical values
    u3 = UpdateEvent(
        device_id="l1", source_type="laptop", user_id="u1",
        vector_clock={"laptop": 1}, timestamp=t1, confidence_weight=0.4,
        field_updates={"volume": 75.0}
    )
    res_n3 = resolve_updates([u1, u3])
    print(f"N3 (Identical values): volume={res_n3.fields.get('volume')}, audit={res_n3.audit.get('volume')}")

    # Case N4: One update causally dominates another
    u4_dom = UpdateEvent(
        device_id="p1", source_type="phone", user_id="u1",
        vector_clock={"phone": 2, "laptop": 1}, timestamp=t2, confidence_weight=0.5,
        field_updates={"volume": 85.0}
    )
    res_n4 = resolve_updates([u2, u4_dom])
    print(f"N4 (Causal dominance): volume={res_n4.fields.get('volume')}, audit={res_n4.audit.get('volume')}")

    # Case N5: Phase 4 3-update scenario (1 obsolete, 2 maximal)
    u5_a = UpdateEvent(
        device_id="p1", source_type="phone", user_id="u1",
        vector_clock={"phone": 1, "laptop": 0}, timestamp=t1, confidence_weight=0.5,
        field_updates={"volume": 20.0}
    )
    u5_b = UpdateEvent(
        device_id="p1", source_type="phone", user_id="u1",
        vector_clock={"phone": 2, "laptop": 0}, timestamp=t1, confidence_weight=0.5,
        field_updates={"volume": 80.0}
    )
    u5_c = UpdateEvent(
        device_id="l1", source_type="laptop", user_id="u1",
        vector_clock={"phone": 0, "laptop": 1}, timestamp=t1, confidence_weight=0.4,
        field_updates={"volume": 40.0}
    )
    res_n5 = resolve_updates([u5_a, u5_b, u5_c])
    print(f"N5 (3 updates, 1 obsolete): volume={res_n5.fields.get('volume')}, audit={res_n5.audit.get('volume')} (Expected 62.22, Actual {res_n5.fields.get('volume')})")

    # Case N6: Equal weights and identical timestamps
    u6_1 = UpdateEvent(
        device_id="p1", source_type="phone", user_id="u1",
        vector_clock={"phone": 1}, timestamp=t1, confidence_weight=0.5,
        field_updates={"volume": 60.0}
    )
    u6_2 = UpdateEvent(
        device_id="l1", source_type="laptop", user_id="u1",
        vector_clock={"laptop": 1}, timestamp=t1, confidence_weight=0.5,
        field_updates={"volume": 80.0}
    )
    res_n6 = resolve_updates([u6_1, u6_2])
    print(f"N6 (Equal weight, same timestamp): volume={res_n6.fields.get('volume')}, audit={res_n6.audit.get('volume')}")

    # Case N7: Zero, negative weights
    u7_zero1 = UpdateEvent(
        device_id="p1", source_type="phone", user_id="u1",
        vector_clock={"phone": 1}, timestamp=t1, confidence_weight=0.0,
        field_updates={"volume": 60.0}
    )
    u7_zero2 = UpdateEvent(
        device_id="l1", source_type="laptop", user_id="u1",
        vector_clock={"laptop": 1}, timestamp=t1, confidence_weight=0.0,
        field_updates={"volume": 80.0}
    )
    res_n7_zero = resolve_updates([u7_zero1, u7_zero2])
    print(f"N7 (Zero weights total_weight=0): volume={res_n7_zero.fields.get('volume')}, audit={res_n7_zero.audit.get('volume')}")

    u7_neg1 = UpdateEvent(
        device_id="p1", source_type="phone", user_id="u1",
        vector_clock={"phone": 1}, timestamp=t1, confidence_weight=-0.5,
        field_updates={"volume": 60.0}
    )
    u7_neg2 = UpdateEvent(
        device_id="l1", source_type="laptop", user_id="u1",
        vector_clock={"laptop": 1}, timestamp=t1, confidence_weight=0.2,
        field_updates={"volume": 80.0}
    )
    res_n7_neg = resolve_updates([u7_neg1, u7_neg2])
    print(f"N7 (Negative weight present): volume={res_n7_neg.fields.get('volume')}, audit={res_n7_neg.audit.get('volume')}")

    # Case N8: Missing vector-clock entries / mismatched keys
    u8_1 = UpdateEvent(
        device_id="p1", source_type="phone", user_id="u1",
        vector_clock={"phone": 1}, timestamp=t1, confidence_weight=0.5,
        field_updates={"volume": 50.0}
    )
    u8_2 = UpdateEvent(
        device_id="custom_dev", source_type="laptop", user_id="u1",
        vector_clock={"custom_key": 1}, timestamp=t1, confidence_weight=0.5,
        field_updates={"volume": 70.0}
    )
    res_n8 = resolve_updates([u8_1, u8_2])
    print(f"N8 (Disjoint clock keys): volume={res_n8.fields.get('volume')}, audit={res_n8.audit.get('volume')}")

    # Case N9: Duplicate delivery of same update
    u9_dup = UpdateEvent(
        device_id="l1", source_type="laptop", user_id="u1",
        vector_clock={"laptop": 1}, timestamp=t1, confidence_weight=0.4,
        field_updates={"volume": 40.0}
    )
    res_n9_single = resolve_updates([u1, u9_dup]) # (75*0.5 + 40*0.4)/0.9 = 53.5/0.9 = 59.44
    res_n9_double = resolve_updates([u1, u9_dup, u9_dup]) # (75*0.5 + 40*0.4 + 40*0.4)/(0.5 + 0.4 + 0.4) = 69.5/1.3 = 53.46
    print(f"N9 (Normal 1+1): volume={res_n9_single.fields.get('volume')}")
    print(f"N9 (Duplicate 1+2): volume={res_n9_double.fields.get('volume')} (Skewed by duplicate: {res_n9_double.fields.get('volume') != res_n9_single.fields.get('volume')})")

    # =========================================================================
    # CATEGORICAL CASES
    # =========================================================================
    print("\n--- CATEGORICAL EDGE CASES ---")

    # Case C1: Two concurrent updates, different values, different weights
    c1_car = UpdateEvent(
        device_id="c1", source_type="car", user_id="u1",
        vector_clock={"car": 1}, timestamp=t1, confidence_weight=0.9,
        field_updates={"genre": "jazz"}
    )
    c1_phone = UpdateEvent(
        device_id="p1", source_type="phone", user_id="u1",
        vector_clock={"phone": 1}, timestamp=t1, confidence_weight=0.5,
        field_updates={"genre": "rock"}
    )
    res_c1 = resolve_updates([c1_car, c1_phone])
    print(f"C1 (Different weights): genre={res_c1.fields.get('genre')}, audit={res_c1.audit.get('genre')}")

    # Case C2: Equal confidence weights, different timestamps
    c2_phone1 = UpdateEvent(
        device_id="p1", source_type="phone", user_id="u1",
        vector_clock={"phone": 1}, timestamp=t1, confidence_weight=0.5,
        field_updates={"genre": "pop"}
    )
    c2_phone2 = UpdateEvent(
        device_id="p2", source_type="phone", user_id="u1",
        vector_clock={"phone": 1}, timestamp=t2, confidence_weight=0.5,
        field_updates={"genre": "lofi"}
    )
    res_c2 = resolve_updates([c2_phone1, c2_phone2])
    print(f"C2 (Equal weight, diff timestamp): genre={res_c2.fields.get('genre')}, audit={res_c2.audit.get('genre')}")

    # Case C3: Equal confidence weights AND identical timestamps (Tie-breaker test)
    c3_a = UpdateEvent(
        device_id="devA", source_type="phone", user_id="u1",
        vector_clock={"devA": 1}, timestamp=t1, confidence_weight=0.5,
        field_updates={"genre": "alpha"}
    )
    c3_b = UpdateEvent(
        device_id="devB", source_type="laptop", user_id="u1",
        vector_clock={"devB": 1}, timestamp=t1, confidence_weight=0.5,
        field_updates={"genre": "beta"}
    )
    res_c3_ab = resolve_updates([c3_a, c3_b])
    res_c3_ba = resolve_updates([c3_b, c3_a])
    print(f"C3 Order [A, B]: genre={res_c3_ab.fields.get('genre')}")
    print(f"C3 Order [B, A]: genre={res_c3_ba.fields.get('genre')} (Non-deterministic tie-break? {res_c3_ab.fields.get('genre') != res_c3_ba.fields.get('genre')})")

    # Case C4: One causally obsolete categorical update in 3-update scenario
    # A (phone: 1): "rock" (weight 0.5)
    # B (phone: 2): "pop" (weight 0.5) [B dominates A]
    # C (car: 1): "jazz" (weight 0.4) [C is concurrent with B]
    # But what if A has weight 0.9?
    # Say Car had older update A ("jazz", w=0.9), but Car changed to B ("ambient", w=0.9).
    # Phone sent concurrent update C ("metal", w=0.5).
    # If A is not pruned, does A win if A has a higher weight than B?
    # Let's test: Car A (w=0.9, "jazz", car:1), Car B (w=0.5, "lofi", car:2)
    # Phone C (w=0.6, "rock", phone:1)
    # B dominates A. Maximal set is {B (w=0.5), C (w=0.6)}. Phone C should win!
    # But if A (w=0.9) is NOT pruned: A's weight 0.9 will WIN over B (0.5) and C (0.6)!
    c4_a = UpdateEvent(
        device_id="car_01", source_type="car", user_id="u1",
        vector_clock={"car": 1, "phone": 0}, timestamp=t1, confidence_weight=0.9,
        field_updates={"genre": "jazz"}
    )
    c4_b = UpdateEvent(
        device_id="car_01", source_type="car", user_id="u1",
        vector_clock={"car": 2, "phone": 0}, timestamp=t2, confidence_weight=0.5,
        field_updates={"genre": "lofi"}
    )
    c4_c = UpdateEvent(
        device_id="phone_01", source_type="phone", user_id="u1",
        vector_clock={"car": 0, "phone": 1}, timestamp=t2, confidence_weight=0.6,
        field_updates={"genre": "rock"}
    )
    # B dominates A. Maximal set is {B ("lofi", w=0.5), C ("rock", w=0.6)}. Winner should be "rock"!
    res_c4 = resolve_updates([c4_a, c4_b, c4_c])
    print(f"C4 (Obsolete categorical update with high weight): genre={res_c4.fields.get('genre')} (Expected: 'rock', Actual: {res_c4.fields.get('genre')})")

    # Case C5: Duplicate delivery
    res_c5 = resolve_updates([c1_phone, c1_phone])
    print(f"C5 (Duplicate categorical delivery): genre={res_c5.fields.get('genre')}, audit={res_c5.audit.get('genre')}")


if __name__ == "__main__":
    run_edge_cases()
