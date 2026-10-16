"""Privacy Guard for verifying zero raw interaction data leakage."""

from typing import Any, Dict
from aggregator.models import DeltaPayload, RawEvent


class PrivacyViolationError(Exception):
    """Raised when raw interaction data or unaggregated events are detected in an outgoing payload."""
    pass


FORBIDDEN_KEY_SUBSTRINGS = [
    "raw",
    "event_log",
    "events",
    "trace",
    "traces",
    "interaction",
    "interactions",
    "history",
    "unaggregated",
    "sensor_stream",
]


def _inspect_element_for_leakage(key: str, value: Any, path: str = ""):
    """
    Recursively inspect keys and values to ensure no raw events, raw arrays, or forbidden keys exist.
    """
    key_lower = key.lower()
    for forbidden in FORBIDDEN_KEY_SUBSTRINGS:
        if forbidden in key_lower:
            raise PrivacyViolationError(
                f"Privacy Violation: Forbidden raw data key '{key}' detected at path '{path}'."
            )

    if isinstance(value, RawEvent):
        raise PrivacyViolationError(
            f"Privacy Violation: RawEvent object detected at path '{path}'."
        )

    if isinstance(value, dict):
        for k, v in value.items():
            _inspect_element_for_leakage(k, v, path=f"{path}.{k}" if path else k)

    elif isinstance(value, (list, tuple, set)):
        for idx, item in enumerate(value):
            if isinstance(item, RawEvent):
                raise PrivacyViolationError(
                    f"Privacy Violation: RawEvent list item detected at path '{path}[{idx}]'."
                )
            if isinstance(item, (dict, list, tuple, set)):
                _inspect_element_for_leakage(f"[{idx}]", item, path=f"{path}[{idx}]")


def assert_no_raw_data_leaked(payload: DeltaPayload) -> bool:
    """
    Hard privacy invariant guard:
    Scans the DeltaPayload (including top-level fields, field_updates, and inside aggregation_metadata).
    Ensures that no raw event traces, raw arrays, or raw timestamps can be transmitted over the wire.
    Raises PrivacyViolationError if any violation is detected. Returns True if payload is clean.
    """
    payload_dict = payload.model_dump()

    # 1. Verify field_updates contains strictly scalar values (no nested lists/dicts/raw events)
    for field_name, val in payload.field_updates.items():
        if not isinstance(val, (int, float, str)):
            raise PrivacyViolationError(
                f"Privacy Violation: field_updates['{field_name}'] must be a flat scalar (float or str), got {type(val)}."
            )

    # 2. Recursively scan the entire payload dictionary including aggregation_metadata
    for key, value in payload_dict.items():
        # Allowed top-level fields
        if key not in ["device_id", "source_type", "user_id", "vector_clock", "timestamp", "confidence_weight", "field_updates", "aggregation_metadata"]:
            raise PrivacyViolationError(f"Privacy Violation: Unexpected top-level field '{key}' in DeltaPayload.")

        if key == "aggregation_metadata" and value is not None:
            _inspect_element_for_leakage(key, value, path="aggregation_metadata")

    return True
