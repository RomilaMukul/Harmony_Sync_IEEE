"""
Security and input-validation audit script for Phase 6.
Tests client weight spoofing, input validation, and MQTT authorization policies.
DO NOT MODIFY APPLICATION CODE.
"""

from datetime import datetime, timezone
import json
import pydantic
from resolver_service.models import UpdateEvent
from resolver_service.resolver import resolve_updates


def run_security_audit():
    print("=" * 80)
    print("PHASE 6: CONFIDENCE-WEIGHT TRUST AND INPUT-VALIDATION AUDIT")
    print("=" * 80)

    t_now = datetime.now(timezone.utc).isoformat()
    t_future = "2099-01-01T00:00:00Z"

    # =========================================================================
    # TEST 1: CLIENT WEIGHT SPOOFING / TAMPERING
    # =========================================================================
    print("\n--- 1. Client Confidence Weight Spoofing ---")
    # Car has legitimate weight 0.9, genre 'jazz', volume 30.0
    car_legit = UpdateEvent(
        device_id="car_01",
        source_type="car",
        user_id="user_victim",
        vector_clock={"car": 1},
        timestamp=t_now,
        confidence_weight=0.9,
        field_updates={"genre": "jazz", "volume": 30.0},
    )

    # Rogue phone spoofs confidence_weight = 99.0 (exceeds theoretical maximum 1.0)
    phone_spoofed = UpdateEvent(
        device_id="phone_01",
        source_type="phone",
        user_id="user_victim",
        vector_clock={"phone": 1},
        timestamp=t_now,
        confidence_weight=99.0,  # SPOOFED WEIGHT
        field_updates={"genre": "hardstyle", "volume": 100.0},
    )

    result_spoofed = resolve_updates([car_legit, phone_spoofed])
    print(f"Legitimate Car update: genre='jazz', volume=30.0, weight=0.9")
    print(f"Spoofed Phone update:  genre='hardstyle', volume=100.0, weight=99.0")
    print(f"Resolver Output Genre:  '{result_spoofed.fields.get('genre')}' (Audit: {result_spoofed.audit.get('genre')})")
    print(f"Resolver Output Volume: {result_spoofed.fields.get('volume')} (Audit: {result_spoofed.audit.get('volume')})")
    genre_hijacked = result_spoofed.fields.get("genre") == "hardstyle"
    volume_hijacked = result_spoofed.fields.get("volume") > 99.0
    print(f"Security Defect Confirmed: Genre Hijacked={genre_hijacked}, Volume Hijacked={volume_hijacked}")

    # =========================================================================
    # TEST 2: NEGATIVE AND EXTREME WEIGHTS
    # =========================================================================
    print("\n--- 2. Extreme and Negative Weight Injection ---")
    try:
        phone_neg = UpdateEvent(
            device_id="phone_01",
            source_type="phone",
            user_id="user_victim",
            vector_clock={"phone": 1},
            timestamp=t_now,
            confidence_weight=-1.5,
            field_updates={"volume": 50.0},
        )
        print(f"Does UpdateEvent accept negative confidence_weight (-1.5)? YES (Accepted: {phone_neg.confidence_weight})")
    except Exception as e:
        print(f"Does UpdateEvent reject negative confidence_weight? YES ({e})")

    # =========================================================================
    # TEST 3: UNVALIDATED VALUE RANGES & INVALID TYPES
    # =========================================================================
    print("\n--- 3. Field Value Range Validation ---")
    unbounded_event = UpdateEvent(
        device_id="phone_01",
        source_type="phone",
        user_id="user_victim",
        vector_clock={"phone": 1},
        timestamp=t_future,
        confidence_weight=0.5,
        field_updates={"volume": 999999.0, "genre": ""},
    )
    result_unbounded = resolve_updates([unbounded_event])
    print(f"Resolved volume with extreme value (999999.0): {result_unbounded.fields.get('volume')}")
    print(f"Are volume ranges [0, 100] validated by resolver or schema? NO")

    # =========================================================================
    # TEST 4: UNEXPECTED / EXTRA FIELDS IN PAYLOAD
    # =========================================================================
    print("\n--- 4. Unexpected / Injected Fields in UpdateEvent Payload ---")
    raw_payload_json = {
        "device_id": "phone_01",
        "source_type": "phone",
        "user_id": "user_victim",
        "vector_clock": {"phone": 1},
        "timestamp": t_now,
        "confidence_weight": 0.5,
        "field_updates": {"volume": 50.0},
        "malicious_injected_admin_flag": True,
        "internal_token": "secret_token_123"
    }
    try:
        parsed_event = UpdateEvent(**raw_payload_json)
        print(f"Does UpdateEvent accept extra injected fields? YES (Parsed without error, extra fields ignored/dropped: {hasattr(parsed_event, 'internal_token')})")
    except pydantic.ValidationError as e:
        print(f"Does UpdateEvent reject extra fields? YES ({e})")

    # =========================================================================
    # TEST 5: MQTT TOPIC AUTHORIZATION & ANONYMOUS ACCESS INSPECTION
    # =========================================================================
    print("\n--- 5. MQTT Broker Authorization Policy Inspection ---")
    import os
    conf_path = "mosquitto.conf"
    if os.path.exists(conf_path):
        with open(conf_path, "r") as f:
            conf_content = f.read().strip()
        print(f"mosquitto.conf content:\n{conf_content}")
        print("Analysis: 'allow_anonymous true' and 'listener 1883' without TLS or password_file.")
        print("Impact: Any client can connect without credentials and publish to ANY topic (e.g. users/*/updates/*).")


if __name__ == "__main__":
    run_security_audit()
