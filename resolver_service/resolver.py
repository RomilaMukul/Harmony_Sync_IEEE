"""Conflict resolution engine for distributed preference synchronization."""

from typing import List, Dict, Union, Optional, Any
from dataclasses import dataclass
from resolver_service.models import UpdateEvent, MergedSnapshot


@dataclass
class FieldCandidate:
    """Represents an individual field update candidate within an update event."""
    field_name: str
    value: Union[float, str]
    confidence_weight: float
    timestamp: str
    vector_clock: Dict[str, int]
    device_id: str
    source_type: str
    raw_event: UpdateEvent


def vector_clock_dominates(clock_a: Dict[str, int], clock_b: Dict[str, int]) -> bool:
    """
    Check if clock_a causally dominates clock_b.
    True if every element of a >= corresponding element of b,
    and at least one element of a is strictly greater than b.
    Missing keys are treated as 0.
    """
    all_devices = set(clock_a.keys()) | set(clock_b.keys())
    at_least_one_greater = False

    for device in all_devices:
        a_val = clock_a.get(device, 0)
        b_val = clock_b.get(device, 0)
        if a_val < b_val:
            return False
        if a_val > b_val:
            at_least_one_greater = True

    return at_least_one_greater


def find_causally_dominant(candidates: List[FieldCandidate]) -> Optional[FieldCandidate]:
    """
    Find a candidate whose vector clock strictly dominates all other candidates.
    Returns None if no single candidate dominates all others.
    """
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


def is_numeric_value(val: Any) -> bool:
    """Check if a value is numeric (int or float)."""
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def group_updates_by_field(updates: List[UpdateEvent]) -> Dict[str, List[FieldCandidate]]:
    """Group incoming updates by field name into FieldCandidate lists."""
    grouped: Dict[str, List[FieldCandidate]] = {}
    for update in updates:
        for field_name, value in update.field_updates.items():
            candidate = FieldCandidate(
                field_name=field_name,
                value=value,
                confidence_weight=update.confidence_weight,
                timestamp=update.timestamp,
                vector_clock=update.vector_clock,
                device_id=update.device_id,
                source_type=update.source_type,
                raw_event=update,
            )
            if field_name not in grouped:
                grouped[field_name] = []
            grouped[field_name].append(candidate)
    return grouped


def resolve_updates(updates: List[UpdateEvent], window_fields: Optional[Dict[str, Any]] = None) -> MergedSnapshot:
    """
    Resolve a list of buffered update events using causal dominance and confidence weighting.
    """
    if not updates:
        return MergedSnapshot(fields={}, audit={})

    grouped = group_updates_by_field(updates)
    merged: Dict[str, Union[float, str]] = {}
    audit_trail: Dict[str, str] = {}

    for field_name, field_candidates in grouped.items():
        if len(field_candidates) == 1:
            merged[field_name] = field_candidates[0].value
            audit_trail[field_name] = "single_source"
            continue

        dominant = find_causally_dominant(field_candidates)
        if dominant is not None:
            merged[field_name] = dominant.value
            audit_trail[field_name] = "causal_dominance"
        else:
            # Check if all candidate values for this field are numeric
            all_numeric = all(is_numeric_value(c.value) for c in field_candidates)
            if all_numeric:
                total_weight = sum(c.confidence_weight for c in field_candidates)
                if total_weight > 0:
                    weighted_val = sum(float(c.value) * c.confidence_weight for c in field_candidates) / total_weight
                    merged[field_name] = round(weighted_val, 2)
                else:
                    merged[field_name] = float(field_candidates[-1].value)
                audit_trail[field_name] = "concurrent_numeric_weighted_avg"
            else:
                # Categorical resolution: highest weight, broken by latest timestamp
                winner = max(field_candidates, key=lambda c: (c.confidence_weight, c.timestamp))
                merged[field_name] = winner.value
                audit_trail[field_name] = "concurrent_categorical_highest_weight"

    return MergedSnapshot(fields=merged, audit=audit_trail)
