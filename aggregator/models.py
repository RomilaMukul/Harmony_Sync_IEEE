"""Data structures for privacy-preserving edge pre-aggregation."""

from typing import Dict, List, Union, Optional, Any
from pydantic import BaseModel, Field
from resolver_service.models import SourceType, CONFIDENCE_WEIGHTS


class RawEvent(BaseModel):
    """
    High-frequency raw client interaction event.
    NEVER leaves the local device or published over the network.
    """
    event_type: str  # e.g., "volume_slider_drag", "genre_like", "skip_track"
    field_name: str  # e.g., "volume", "genre"
    raw_value: Union[float, str]
    raw_timestamp: str  # Local high-resolution ISO 8601 timestamp
    interaction_metadata: Dict[str, Any] = Field(default_factory=dict)


class AggregatorState(BaseModel):
    """
    Internal accumulator state maintained locally on the client device.
    """
    user_id: str
    device_id: str
    source_type: SourceType
    vector_clock: Dict[str, int] = Field(default_factory=lambda: {"phone": 0, "car": 0, "laptop": 0})
    last_published_snapshot: Dict[str, Union[float, str]] = Field(default_factory=dict)
    buffered_raw_events: List[RawEvent] = Field(default_factory=list)
    field_accumulators: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class DeltaPayload(BaseModel):
    """
    Exportable pre-aggregated delta payload.
    Strictly flattened for 100% backward compatibility with UpdateEvent and resolve_updates().
    Guaranteed to contain zero raw event traces, unaggregated sensor samples, or raw device logs.
    """
    device_id: str
    source_type: SourceType
    user_id: str
    vector_clock: Dict[str, int]
    timestamp: str  # Coarse aggregation cycle timestamp (ISO 8601 UTC)
    confidence_weight: float
    field_updates: Dict[str, Union[float, str]]  # Strictly flattened scalar values
    aggregation_metadata: Optional[Dict[str, Any]] = None  # High-level summary metrics only
