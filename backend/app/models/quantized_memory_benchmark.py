from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QuantizationMethod(str, Enum):
    FLOAT32 = "float32"
    INT8 = "int8"
    RABITQ = "rabitq"


class MemoryRecord(BaseModel):
    namespace: str = Field(..., min_length=1, max_length=64)
    vector: list[float] = Field(..., min_items=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuantizationResult(BaseModel):
    method: QuantizationMethod
    original_vector: list[float]
    quantized_data: list[int] | bytes | None = None
    reconstruction_error: float = Field(ge=0.0)


class ComparisonResult(BaseModel):
    method: QuantizationMethod
    avg_recall: float = Field(ge=0.0, le=1.0)
    avg_memory_bytes: int = Field(ge=0)
