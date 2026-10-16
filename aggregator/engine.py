"""Privacy-Preserving Edge Pre-Aggregation Engine."""

import time
import asyncio
from typing import List, Dict, Union, Optional, Any, Callable
from collections import Counter
from datetime import datetime, timezone
from aggregator.models import RawEvent, AggregatorState, DeltaPayload
from resolver_service.models import CONFIDENCE_WEIGHTS


def extract_signal_for_field(events: List[RawEvent], field_name: str) -> List[RawEvent]:
    """
    Extract and filter raw events specifically belonging to a given field_name.
    """
    return [e for e in events if e.field_name == field_name]


def compute_local_delta(
    state: AggregatorState,
    field_name: str,
    new_value: Union[float, str],
) -> Dict[str, Any]:
    """
    Compute the local delta of a field relative to the previous baseline stored in state.
    Reads previous_value from state.field_accumulators or state.last_published_snapshot.
    """
    field_acc = state.field_accumulators.get(field_name, {})
    previous_value = field_acc.get(
        "previous_value",
        state.last_published_snapshot.get(field_name, 0.0 if isinstance(new_value, (int, float)) else ""),
    )

    if isinstance(new_value, (int, float)) and isinstance(previous_value, (int, float)):
        delta = round(float(new_value) - float(previous_value), 4)
    else:
        delta = new_value if new_value != previous_value else None

    result = {
        "field_name": field_name,
        "new_value": new_value,
        "previous_value": previous_value,
        "delta": delta,
    }
    return result


def get_fields_touched(events: List[RawEvent]) -> List[str]:
    """
    Extract unique field names that were modified across the list of raw events.
    """
    seen = set()
    touched = []
    for e in events:
        if e.field_name not in seen:
            seen.add(e.field_name)
            touched.append(e.field_name)
    return touched


def run_aggregation_cycle(state: AggregatorState) -> Optional[DeltaPayload]:
    """
    Execute a local edge aggregation cycle:
    1. Consolidates buffered raw interaction events.
    2. Calculates mean for continuous numeric fields and mode/latest for categorical fields.
    3. Flattens field_updates to single scalar values (Dict[str, Union[float, str]]).
    4. Increments device vector clock.
    5. Updates internal accumulators and clears buffered raw events.
    6. Returns a privacy-preserving DeltaPayload (or None if buffer is empty).
    """
    if not state.buffered_raw_events:
        return None

    raw_events = list(state.buffered_raw_events)
    fields_touched = get_fields_touched(raw_events)

    flat_field_updates: Dict[str, Union[float, str]] = {}
    sample_counts: Dict[str, int] = {}

    for field in fields_touched:
        field_events = extract_signal_for_field(raw_events, field)
        if not field_events:
            continue

        sample_counts[field] = len(field_events)
        all_numeric = all(isinstance(e.raw_value, (int, float)) for e in field_events)

        if all_numeric:
            # Numeric aggregation: compute arithmetic mean across the local sample window
            total_val = sum(float(e.raw_value) for e in field_events)
            mean_val = round(total_val / len(field_events), 2)
            flat_field_updates[field] = mean_val

            # Update accumulator
            prev_val = state.last_published_snapshot.get(field, mean_val)
            state.field_accumulators[field] = {
                "previous_value": mean_val,
                "sample_count": len(field_events),
                "running_sum": total_val,
                "delta": round(mean_val - float(prev_val), 2) if isinstance(prev_val, (int, float)) else 0.0,
            }
            state.last_published_snapshot[field] = mean_val
        else:
            # Categorical aggregation: select mode (most frequent) or latest on tie
            values = [str(e.raw_value) for e in field_events]
            counter = Counter(values)
            # Find candidate with highest count; tie broken by order in field_events (latest)
            max_count = max(counter.values())
            candidates = [v for v, count in counter.items() if count == max_count]
            # Pick latest matching candidate
            winner = None
            for e in reversed(field_events):
                if str(e.raw_value) in candidates:
                    winner = str(e.raw_value)
                    break
            if winner is None:
                winner = values[-1]

            flat_field_updates[field] = winner
            state.field_accumulators[field] = {
                "previous_value": winner,
                "sample_count": len(field_events),
                "mode_counts": dict(counter),
            }
            state.last_published_snapshot[field] = winner

    # Increment vector clock for this device
    dev_key = state.source_type
    state.vector_clock[dev_key] = state.vector_clock.get(dev_key, 0) + 1

    cycle_timestamp = datetime.now(timezone.utc).isoformat()
    weight = CONFIDENCE_WEIGHTS.get(state.source_type, 0.5)

    payload = DeltaPayload(
        device_id=state.device_id,
        source_type=state.source_type,
        user_id=state.user_id,
        vector_clock=dict(state.vector_clock),
        timestamp=cycle_timestamp,
        confidence_weight=weight,
        field_updates=flat_field_updates,
        aggregation_metadata={"sample_counts": sample_counts},
    )

    # Clear processed raw events buffer
    state.buffered_raw_events.clear()

    return payload


async def scheduler_loop(
    state: AggregatorState,
    interval_seconds: float,
    publish_callback: Callable[[DeltaPayload], None],
    stop_event: asyncio.Event,
):
    """
    Periodic background loop triggering run_aggregation_cycle every interval_seconds.
    """
    while not stop_event.is_set():
        try:
            await asyncio.sleep(interval_seconds)
            payload = run_aggregation_cycle(state)
            if payload:
                publish_callback(payload)
        except Exception as e:
            pass
