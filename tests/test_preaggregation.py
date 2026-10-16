"""Test suite for Privacy-Preserving Edge Pre-Aggregation Layer."""

import pytest
from datetime import datetime, timezone
from aggregator.models import RawEvent, AggregatorState, DeltaPayload
from aggregator.engine import (
    extract_signal_for_field,
    compute_local_delta,
    get_fields_touched,
    run_aggregation_cycle,
)
from aggregator.privacy import assert_no_raw_data_leaked, PrivacyViolationError
from resolver_service.resolver import resolve_updates
from resolver_service.models import UpdateEvent


def test_1_compute_local_delta_from_baseline():
    """
    TEST 1: compute_local_delta() calculates delta relative to previous baseline stored in state.
    """
    state = AggregatorState(
        user_id="user_test",
        device_id="phone_01",
        source_type="phone",
        last_published_snapshot={"volume": 50.0, "genre": "jazz"},
        field_accumulators={
            "volume": {"previous_value": 50.0, "sample_count": 10},
            "genre": {"previous_value": "jazz", "sample_count": 1},
        },
    )

    # Test numeric delta
    res_numeric = compute_local_delta(state, "volume", 65.0)
    assert res_numeric["field_name"] == "volume"
    assert res_numeric["new_value"] == 65.0
    assert res_numeric["previous_value"] == 50.0
    assert res_numeric["delta"] == 15.0

    # Test categorical delta
    res_cat = compute_local_delta(state, "genre", "rock")
    assert res_cat["field_name"] == "genre"
    assert res_cat["new_value"] == "rock"
    assert res_cat["previous_value"] == "jazz"
    assert res_cat["delta"] == "rock"


def test_2_multi_event_aggregation_cycle():
    """
    TEST 2: run_aggregation_cycle() aggregates a burst of raw events across multiple fields into flat fields.
    """
    state = AggregatorState(
        user_id="user_test_2",
        device_id="phone_01",
        source_type="phone",
        vector_clock={"phone": 0, "car": 0, "laptop": 0},
    )

    t_now = datetime.now(timezone.utc).isoformat()
    state.buffered_raw_events.extend([
        RawEvent(event_type="slider_move", field_name="volume", raw_value=70.0, raw_timestamp=t_now),
        RawEvent(event_type="slider_move", field_name="volume", raw_value=75.0, raw_timestamp=t_now),
        RawEvent(event_type="slider_release", field_name="volume", raw_value=80.0, raw_timestamp=t_now),
        RawEvent(event_type="genre_tap", field_name="genre", raw_value="pop", raw_timestamp=t_now),
        RawEvent(event_type="genre_tap", field_name="genre", raw_value="pop", raw_timestamp=t_now),
    ])

    payload = run_aggregation_cycle(state)
    assert payload is not None
    assert payload.device_id == "phone_01"
    assert payload.source_type == "phone"
    assert payload.vector_clock["phone"] == 1
    assert payload.field_updates["volume"] == 75.0
    assert payload.field_updates["genre"] == "pop"
    assert payload.aggregation_metadata["sample_counts"]["volume"] == 3
    assert payload.aggregation_metadata["sample_counts"]["genre"] == 2


def test_3_buffer_cleared_and_state_updated_after_cycle():
    """
    TEST 3: run_aggregation_cycle() clears buffered_raw_events and updates internal state snapshot.
    """
    state = AggregatorState(
        user_id="user_test_3",
        device_id="laptop_01",
        source_type="laptop",
    )
    t_now = datetime.now(timezone.utc).isoformat()
    state.buffered_raw_events.append(
        RawEvent(event_type="volume_up", field_name="volume", raw_value=60.0, raw_timestamp=t_now)
    )

    payload = run_aggregation_cycle(state)
    assert payload is not None
    assert len(state.buffered_raw_events) == 0
    assert state.last_published_snapshot["volume"] == 60.0
    assert state.field_accumulators["volume"]["previous_value"] == 60.0

    second_payload = run_aggregation_cycle(state)
    assert second_payload is None


def test_4_privacy_guard_passes_valid_payload():
    """
    TEST 4: assert_no_raw_data_leaked() returns True for cleanly aggregated DeltaPayload.
    """
    payload = DeltaPayload(
        device_id="car_01",
        source_type="car",
        user_id="user_priv_test",
        vector_clock={"car": 1},
        timestamp=datetime.now(timezone.utc).isoformat(),
        confidence_weight=0.9,
        field_updates={"volume": 65.0, "genre": "jazz"},
        aggregation_metadata={"sample_counts": {"volume": 5, "genre": 1}},
    )
    assert assert_no_raw_data_leaked(payload) is True


def test_5_privacy_guard_catches_raw_data_leakage():
    """
    TEST 5: assert_no_raw_data_leaked() raises PrivacyViolationError if raw data or forbidden fields leak.
    """
    # 1. Leak inside aggregation_metadata
    leaky_metadata_payload = DeltaPayload(
        device_id="phone_01",
        source_type="phone",
        user_id="user_priv_test",
        vector_clock={"phone": 1},
        timestamp=datetime.now(timezone.utc).isoformat(),
        confidence_weight=0.5,
        field_updates={"volume": 70.0},
        aggregation_metadata={"raw_slider_events": [70.0, 71.0, 72.0]},
    )
    with pytest.raises(PrivacyViolationError):
        assert_no_raw_data_leaked(leaky_metadata_payload)

    # 2. Leak forbidden key inside nested dict
    leaky_trace_payload = DeltaPayload(
        device_id="laptop_01",
        source_type="laptop",
        user_id="user_priv_test",
        vector_clock={"laptop": 1},
        timestamp=datetime.now(timezone.utc).isoformat(),
        confidence_weight=0.4,
        field_updates={"volume": 40.0},
        aggregation_metadata={"client_stats": {"interaction_traces": ["click", "drag"]}},
    )
    with pytest.raises(PrivacyViolationError):
        assert_no_raw_data_leaked(leaky_trace_payload)


def test_6_backward_compatibility_with_unmodified_resolver():
    """
    STEP 5 / TEST 6: Feed a real DeltaPayload from run_aggregation_cycle() directly into
    the unmodified resolve_updates() function from resolver_service/resolver.py.
    Proves that pre-aggregation is 100% backward compatible and purely additive.
    """
    # Simulate Phone edge aggregator generating DeltaPayload
    phone_state = AggregatorState(
        user_id="user_compat_test",
        device_id="phone_01",
        source_type="phone",
        vector_clock={"phone": 0, "car": 0, "laptop": 0},
    )
    t_now = datetime.now(timezone.utc).isoformat()
    phone_state.buffered_raw_events.extend([
        RawEvent(event_type="slider_drag", field_name="volume", raw_value=78.0, raw_timestamp=t_now),
        RawEvent(event_type="slider_drag", field_name="volume", raw_value=82.0, raw_timestamp=t_now),
    ])
    phone_delta: DeltaPayload = run_aggregation_cycle(phone_state)
    assert phone_delta is not None
    assert phone_delta.field_updates["volume"] == 80.0

    # Simulate Laptop edge aggregator generating DeltaPayload
    laptop_state = AggregatorState(
        user_id="user_compat_test",
        device_id="laptop_01",
        source_type="laptop",
        vector_clock={"phone": 0, "car": 0, "laptop": 0},
    )
    laptop_state.buffered_raw_events.append(
        RawEvent(event_type="key_press", field_name="volume", raw_value=40.0, raw_timestamp=t_now)
    )
    laptop_delta: DeltaPayload = run_aggregation_cycle(laptop_state)
    assert laptop_delta is not None
    assert laptop_delta.field_updates["volume"] == 40.0

    # Feed DeltaPayloads directly to existing unmodified resolve_updates()
    # Notice: UpdateEvent(**phone_delta.model_dump()) or passing UpdateEvent-compatible objects
    update_1 = UpdateEvent(**phone_delta.model_dump())
    update_2 = UpdateEvent(**laptop_delta.model_dump())

    merged = resolve_updates([update_1, update_2])
    # Expected weighted merge: (80*0.5 + 40*0.4)/(0.5+0.4) = 62.22
    assert "volume" in merged.fields
    assert abs(merged.fields["volume"] - 62.22) <= 0.01
    assert merged.audit["volume"] == "concurrent_numeric_weighted_avg"


def test_7_numeric_averaging_across_samples():
    """
    TEST 7: Numeric averaging accurately computes mean across raw values [80, 82, 84, 86, 90] -> 84.4.
    """
    state = AggregatorState(
        user_id="user_test_7",
        device_id="car_01",
        source_type="car",
    )
    t_now = datetime.now(timezone.utc).isoformat()
    raw_vals = [80.0, 82.0, 84.0, 86.0, 90.0]
    for v in raw_vals:
        state.buffered_raw_events.append(
            RawEvent(event_type="sensor_tick", field_name="volume", raw_value=v, raw_timestamp=t_now)
        )

    payload = run_aggregation_cycle(state)
    assert payload is not None
    expected_mean = round(sum(raw_vals) / len(raw_vals), 2)  # 422.0 / 5 = 84.4
    assert payload.field_updates["volume"] == expected_mean
    assert payload.confidence_weight == 0.9


def test_8_categorical_mode_and_latest_selection():
    """
    TEST 8: Categorical aggregation chooses the mode (e.g., ["lofi", "lofi", "pop"] -> "lofi").
    """
    state = AggregatorState(
        user_id="user_test_8",
        device_id="phone_01",
        source_type="phone",
    )
    t_now = datetime.now(timezone.utc).isoformat()
    genres = ["lofi", "pop", "lofi"]
    for g in genres:
        state.buffered_raw_events.append(
            RawEvent(event_type="button_press", field_name="genre", raw_value=g, raw_timestamp=t_now)
        )

    payload = run_aggregation_cycle(state)
    assert payload is not None
    assert payload.field_updates["genre"] == "lofi"
