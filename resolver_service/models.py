"""Data models for distributed music preference synchronization."""

from typing import Dict, Literal, Union, Optional, Any
from pydantic import BaseModel, Field

SourceType = Literal["phone", "car", "laptop"]

CONFIDENCE_WEIGHTS: Dict[str, float] = {
    "car": 0.9,
    "phone": 0.5,
    "laptop": 0.4,
}


class UpdateEvent(BaseModel):
    """Event published by device clients representing preference updates."""
    device_id: str
    source_type: SourceType
    user_id: str
    vector_clock: Dict[str, int]
    timestamp: str  # ISO 8601 string
    confidence_weight: float = 0.5
    field_updates: Dict[str, Union[float, str]]
    aggregation_metadata: Optional[Dict[str, Any]] = None


class MergedSnapshot(BaseModel):
    """Merged preference state resulting from conflict resolution."""
    user_id: Optional[str] = None
    version: Optional[int] = None
    fields: Dict[str, Union[float, str]] = Field(default_factory=dict)
    audit: Dict[str, str] = Field(default_factory=dict)
    created_at: Optional[str] = None
