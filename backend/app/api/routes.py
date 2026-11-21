from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.models.quantized_memory_benchmark import (
    QuantizationMethod,
    QuantizationResult,
    ComparisonResult,
)
from app.services.quantized_memory_benchmark import (
    run_quantization_comparison,
    quantize_vector,
    reconstruct_vector,
    compute_recall,
    compute_memory_footprint,
)

router = APIRouter(prefix="/api/v1")


class QuantizationCompareRequest(BaseModel):
    vector: list[float] = Field(..., min_items=1, max_items=4096)
    methods: list[QuantizationMethod] | None = Field(
        None,
        description="Quantization methods to compare; defaults to [float32, int8, rabitq]",
    )


@router.post(
    "/quantized-memory-benchmark/compare",
    response_model=list[QuantizationResult],
    summary="Compare float32, int8, and 1-bit RaBitQ vector quantization",
)
def compare_quantization(
    payload: QuantizationCompareRequest,
    request: Request,
) -> list[QuantizationResult]:
    """Run quantization comparison across specified methods and return
    per-result records including reconstruction error, quantized data, and
    implicit memory footprint (computable from method + vector length).

    The endpoint performs:
    1. Quantize the input vector using each requested method
    2. Reconstruct the vector from quantized representation
    3. Compute cosine-similarity recall (0–1) between original and reconstructed
    4. Compute per-method MSE reconstruction error
    5. Return full QuantizationResult for each method
    """
    results = run_quantization_comparison(payload.vector, payload.methods)
    return results


@router.get(
    "/quantized-memory-benchmark/comparison",
    response_model=list[ComparisonResult],
    summary="Return averaged comparison results per quantization method",
)
def get_comparison_summary(
    request: Request,
) -> list[ComparisonResult]:
    """Return a summary ComparisonResult per method based on the most recent
    quantization comparison stored in the application state.

    In a full implementation this would query a database of past runs;
    here we simply return an empty list pending backend persistence.
    """
    # Placeholder: return empty summary; real impl would accumulate per-run stats
    return []


# ──────────────────────────────────────────────────────────
# Small utility endpoints
# ──────────────────────────────────────────────────────────


@router.post(
    "/quantized-memory-benchmark/quantize",
    response_model=QuantizationResult,
    summary="Quantize a vector using a single method",
)
def quantize_single(
    payload: QuantizationCompareRequest,
    request: Request,
) -> QuantizationResult:
    """Quantize the given vector using the first requested method and return
    a single QuantizationResult.

    Useful for quick prototyping or client-side method selection.
    """
    methods = payload.methods or [QuantizationMethod.FLOAT32]
    if not methods:
        methods = [QuantizationMethod.FLOAT32]
    results = run_quantization_comparison(payload.vector, methods)
    return results[0] if results else QuantizationResult(
        method=QuantizationMethod.FLOAT32,
        original_vector=payload.vector,
        quantized_data=[],
        reconstruction_error=0.0,
    )


@router.get(
    "/quantized-memory-benchmark/method-info",
    response_model=dict[QuantizationMethod, dict[str, Any]],
    summary="Get memory footprint info per quantization method",
)
def method_info() -> dict[QuantizationMethod, dict[str, Any]]:
    """Return per-method memory footprint formula and example bytes for a
    128-dimensional vector.

    This helps clients understand the tradeoff between recall and storage
    for each quantization method.
    """
    vec_len = 128
    return {
        QuantizationMethod.FLOAT32: {
            "bytes_per_vector": vec_len * 4,
            "description": "32-bit floating point, full precision",
        },
        QuantizationMethod.INT8: {
            "bytes_per_vector": vec_len * 1,
            "description": "8-bit integer with affine scaling, good recall",
        },
        QuantizationMethod.RABITQ: {
            "bytes_per_vector": (vec_len + 7) // 8,
            "description": "1-bit RaBitQ sign-only, minimal storage, lower recall",
        },
    }
