"""Demo script comparing Naive Last-Write-Wins vs Weighted Conflict Resolution."""

import sys
import os
import time
import json
from datetime import datetime, timezone, timedelta

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from resolver_service.models import UpdateEvent
from resolver_service.resolver import resolve_updates
from vehicle.cache import VehicleCache
from vehicle.playback import PlaybackEngine


def run_comparison_demo():
    print("=" * 80)
    print(" DISTRIBUTED MUSIC PREFERENCE SYNC: LWW VS WEIGHTED CONFLICT RESOLUTION ")
    print("=" * 80)

    # SCENARIO 1: Concurrent Numeric Preference Conflict (Volume)
    print("\n[SCENARIO 1] Concurrent Volume Adjustments from Multiple Devices")
    print("-" * 80)
    t1 = datetime(2026, 9, 1, 14, 0, 0, tzinfo=timezone.utc).isoformat()
    t2 = datetime(2026, 9, 1, 14, 0, 1, tzinfo=timezone.utc).isoformat()

    phone_update = UpdateEvent(
        device_id="phone_01",
        source_type="phone",
        user_id="demo_user",
        vector_clock={"phone": 1, "laptop": 0},
        timestamp=t1,
        confidence_weight=0.5,
        field_updates={"volume": 80.0},
    )
    laptop_update = UpdateEvent(
        device_id="laptop_01",
        source_type="laptop",
        user_id="demo_user",
        vector_clock={"phone": 0, "laptop": 1},
        timestamp=t2,
        confidence_weight=0.4,
        field_updates={"volume": 40.0},
    )

    numeric_updates = [phone_update, laptop_update]

    # Naive LWW
    lww_numeric_winner = max(numeric_updates, key=lambda u: u.timestamp)
    lww_numeric_val = lww_numeric_winner.field_updates["volume"]

    # Weighted Merge
    weighted_numeric_result = resolve_updates(numeric_updates)
    weighted_numeric_val = weighted_numeric_result.fields["volume"]
    audit_numeric = weighted_numeric_result.audit["volume"]

    print(f"Device 1: Phone  | Volume: 80.0 | Weight: 0.5 | Timestamp: {t1}")
    print(f"Device 2: Laptop | Volume: 40.0 | Weight: 0.4 | Timestamp: {t2} (Later)")
    print(f"\n  -> Naive Last-Write-Wins (LWW): {lww_numeric_val:.2f}")
    print(f"    (Flaw: Discards high-confidence phone signal solely due to 1s clock drift)")
    print(f"  -> Causally-Aware Weighted Merge: {weighted_numeric_val:.2f} (Audit: {audit_numeric})")
    print(f"    (Benefit: Accurately reflects weighted collective preference = 62.22)")

    # SCENARIO 2: Categorical Preference Conflict (Genre - Confidence & Causal Dominance)
    print("\n\n[SCENARIO 2] Categorical Conflict: In-Vehicle Driving Context vs Phone")
    print("-" * 80)
    car_update = UpdateEvent(
        device_id="car_01",
        source_type="car",
        user_id="demo_user",
        vector_clock={"car": 1, "phone": 0},
        timestamp=t1,
        confidence_weight=0.9,
        field_updates={"genre": "jazz"},
    )
    phone_genre_update = UpdateEvent(
        device_id="phone_01",
        source_type="phone",
        user_id="demo_user",
        vector_clock={"car": 0, "phone": 1},
        timestamp=t2,
        confidence_weight=0.5,
        field_updates={"genre": "rock"},
    )

    cat_updates = [car_update, phone_genre_update]

    # Naive LWW
    lww_cat_winner = max(cat_updates, key=lambda u: u.timestamp)
    lww_cat_val = lww_cat_winner.field_updates["genre"]

    # Weighted Merge
    weighted_cat_result = resolve_updates(cat_updates)
    weighted_cat_val = weighted_cat_result.fields["genre"]
    audit_cat = weighted_cat_result.audit["genre"]

    print(f"Device 1: Car   | Genre: 'jazz' | Weight: 0.9 (Direct in-vehicle preference) | Timestamp: {t1}")
    print(f"Device 2: Phone | Genre: 'rock' | Weight: 0.5 (Background device)          | Timestamp: {t2}")
    print(f"\n  -> Naive Last-Write-Wins (LWW): '{lww_cat_val}'")
    print(f"    (Flaw: Background phone override clobbers intentional driver selection)")
    print(f"  -> Causally-Aware Weighted Merge: '{weighted_cat_val}' (Audit: {audit_cat})")
    print(f"    (Benefit: Preserves high-confidence in-vehicle driving context)")

    print("\n" + "=" * 80)
    print(" SUMMARY: WHY WEIGHTED CONFLICT RESOLUTION BEATS NAIVE LWW")
    print("=" * 80)
    print("1. Eliminates network jitter / clock skew anomalies.")
    print("2. Protects high-context driving preferences (car=0.9) from low-context drift.")
    print("3. Preserves full audit trail for explainability in connected vehicles.")
    print("=" * 80 + "\n")


def run_live_demo():
    print("=" * 80)
    print(" STARTING LIVE END-TO-END SIMULATION WITH LOCAL SQLITE VEHICLE CACHE ")
    print("=" * 80)

    db_path = "demo_vehicle_cache.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    cache = VehicleCache(db_path=db_path)
    playback = PlaybackEngine(cache=cache)

    print("\n[Step 1] Initial Playback State (Reading purely from local vehicle cache):")
    state = playback.tick()
    print(f"  Head Unit State: Volume={state['volume']}, Genre='{state['genre']}', Version={state['version']}")

    print("\n[Step 2] Simulating incoming concurrent updates from Phone, Car, and Laptop...")
    t_now = datetime.now(timezone.utc).isoformat()
    phone_up = UpdateEvent(
        device_id="phone_01",
        source_type="phone",
        user_id="user_live_demo",
        vector_clock={"phone": 1, "car": 0, "laptop": 0},
        timestamp=t_now,
        confidence_weight=0.5,
        field_updates={"volume": 80.0, "genre": "rock"},
    )
    car_up = UpdateEvent(
        device_id="car_01",
        source_type="car",
        user_id="user_live_demo",
        vector_clock={"phone": 0, "car": 1, "laptop": 0},
        timestamp=t_now,
        confidence_weight=0.9,
        field_updates={"genre": "jazz"},
    )
    laptop_up = UpdateEvent(
        device_id="laptop_01",
        source_type="laptop",
        user_id="user_live_demo",
        vector_clock={"phone": 0, "car": 0, "laptop": 1},
        timestamp=t_now,
        confidence_weight=0.4,
        field_updates={"volume": 40.0},
    )

    buffered = [phone_up, car_up, laptop_up]
    print(f"  Buffered {len(buffered)} updates in 2-second resolution window.")

    print("\n[Step 3] Resolver Engine flushes and executes causally-aware resolution:")
    resolved = resolve_updates(buffered)
    print(f"  Merged Fields: {resolved.fields}")
    print(f"  Audit Trail:   {resolved.audit}")

    print("\n[Step 4] Vehicle receives merged snapshot and updates local SQLite cache:")
    version = 1
    cache.store_snapshot(version=version, snapshot=resolved.fields)
    print(f"  Saved version {version} to {db_path}.")

    print("\n[Step 5] Vehicle Playback Engine executes next tick (non-blocking offline-first):")
    new_state = playback.tick()
    print(f"  Head Unit State: Volume={new_state['volume']:.2f}, Genre='{new_state['genre']}', Version={new_state['version']}")

    print("\n" + "=" * 80)
    print(" LIVE END-TO-END DEMO COMPLETED SUCCESSFULLY ")
    print("=" * 80 + "\n")

    if os.path.exists(db_path):
        os.remove(db_path)


if __name__ == "__main__":
    if "--live" in sys.argv:
        run_live_demo()
    else:
        run_comparison_demo()
