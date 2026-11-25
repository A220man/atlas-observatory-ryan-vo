from __future__ import annotations

import numpy as np
from typing import Any

from app.models.quantized_memory_benchmark import (
    QuantizationMethod,
    MemoryRecord,
    QuantizationResult,
    ComparisonResult,
)


def quantize_vector(
    vector: list[float],
    method: QuantizationMethod,
) -> tuple[list[float] | list[int] | bytes, QuantizationMethod]:
    """Quantize a float32 vector using the specified method.

    Returns (quantized_data, method).
    """
    arr = np.array(vector, dtype=np.float32)
    if method == QuantizationMethod.FLOAT32:
        # FLOAT32 is the identity/ no-op quantization
        # Store as list of float32 values
        quantized = arr.tolist()
        return quantized, method
    elif method == QuantizationMethod.INT8:
        min_val = float(arr.min())
        max_val = float(arr.max())
        scale = (max_val - min_val) / 255.0 if max_val != min_val else 1.0
        quantized = np.clip(np.round((arr - min_val) / scale).astype(np.int8), -128, 127).tolist()
        return quantized, method
    elif method == QuantizationMethod.RABITQ:
        # 1-bit RaBitQ: sign-only quantization
        signs = np.sign(arr).astype(np.int8).tolist()
        return signs, method
    else:
        raise ValueError(f"Unsupported quantization method: {method}")


def reconstruct_vector(
    quantized: list[float] | list[int] | bytes,
    method: QuantizationMethod,
    original_min: float | None = None,
    original_max: float | None = None,
) -> np.ndarray:
    """Reconstruct a vector from quantized data.

    Returns float32 numpy array.
    """
    if method == QuantizationMethod.FLOAT32:
        # FLOAT32: quantized data is already float32, return as-is
        reconstructed = np.array(quantized, dtype=np.float32)
        return reconstructed
    elif method == QuantizationMethod.INT8:
        if original_min is None or original_max is None:
            raise ValueError("INT8 reconstruction requires original_min and original_max")
        scale = (original_max - original_min) / 255.0
        reconstructed = np.array(quantized, dtype=np.int8)
        return reconstructed * scale + original_min
    elif method == QuantizationMethod.RABITQ:
        # 1-bit: reconstruct from sign, use midpoint of float32 range as placeholder
        signs = np.array(quantized, dtype=np.int8)
        min_f32, max_f32 = -3.4028235e38, 3.4028235e38
        reconstructed = signs * (max_f32 - min_f32) / 2.0 + min_f32
        return reconstructed.astype(np.float32)
    else:
        raise ValueError(f"Unsupported quantization method: {method}")


def compute_recall(
    original: list[float],
    reconstructed: np.ndarray,
) -> float:
    """Compute cosine similarity (recall) between original and reconstructed vectors.

    Returns value in [0, 1] where 1 is perfect recall.
    """
    orig_arr = np.array(original, dtype=np.float32)
    recon_arr = reconstructed.astype(np.float32)
    if np.linalg.norm(orig_arr) == 0 or np.linalg.norm(recon_arr) == 0:
        return 0.0
    cosine_sim = float(np.dot(orig_arr, recon_arr) / (np.linalg.norm(orig_arr) * np.linalg.norm(recon_arr)))
    # Clamp to [0, 1] — treat negative similarity as near-zero recall
    return max(0.0, min(1.0, (cosine_sim + 1.0) / 2.0))


def compute_memory_footprint(
    quantized: list[float] | list[int] | bytes,
    method: QuantizationMethod,
    vector_length: int,
) -> int:
    """Compute memory footprint in bytes for quantized data.

    Returns bytes used to store the quantized representation.
    """
    if method == QuantizationMethod.FLOAT32:
        return vector_length * 4  # 4 bytes per float32
    elif method == QuantizationMethod.INT8:
        return vector_length * 1  # 1 byte per int8
    elif method == QuantizationMethod.RABITQ:
        # 1-bit: vector_length bits, rounded up to bytes
        return (vector_length + 7) // 8
    else:
        raise ValueError(f"Unsupported quantization method: {method}")


def run_quantization_comparison(
    vector: list[float],
    methods: list[QuantizationMethod] | None = None,
) -> list[QuantizationResult]:
    """Run quantization comparison across specified methods.

    Returns list of QuantizationResult for each method.
    """
    if methods is None:
        methods = [QuantizationMethod.FLOAT32, QuantizationMethod.INT8, QuantizationMethod.RABITQ]

    results: list[QuantizationResult] = []
    for method in methods:
        quantized, _ = quantize_vector(vector, method)
        memory_bytes = compute_memory_footprint(quantized, method, len(vector))

        # For INT8 and RABITQ, we need original min/max for reconstruction
        if method == QuantizationMethod.INT8:
            original_min = float(np.min(np.array(vector, dtype=np.float32)))
            original_max = float(np.max(np.array(vector, dtype=np.float32)))
            reconstructed = reconstruct_vector(quantized, method, original_min=original_min, original_max=original_max)
        elif method == QuantizationMethod.RABITQ:
            reconstructed = reconstruct_vector(quantized, method)
        else:  # FLOAT32
            # FLOAT32 is identity; reconstructed should equal original
            reconstructed = reconstruct_vector(quantized, method)

        recall = compute_recall(vector, reconstructed)
        mse = float(np.mean((np.array(vector, dtype=np.float32) - reconstructed.astype(np.float32)) ** 2))
        results.append(
            QuantizationResult(
                method=method,
                original_vector=vector,
                quantized_data=quantized,
                reconstruction_error=mse,
            )
        )
    return results


def compare_across_namespace(
    records: list[MemoryRecord],
    methods: list[QuantizationMethod] | None = None,
) -> dict[str, list[QuantizationResult]]:
    """Compare quantization methods across a namespace of memory records.

    Returns a dict mapping namespace -> list of QuantizationResult per method.
    This enables memory/recall tradeoff analysis across agent memory namespaces.
    """
    from collections import defaultdict

    grouped: dict[str, list[list[float]]] = defaultdict(list)
    for rec in records:
        grouped[rec.namespace].append(rec.vector)

    results: dict[str, list[QuantizationResult]] = {}
    for namespace, vectors in grouped.items():
        namespace_results: list[QuantizationResult] = []
        for vector in vectors:
            vec_results = run_quantization_comparison(vector, methods)
            namespace_results.extend(vec_results)
        results[namespace] = namespace_results

    return results


def diagnose_temporal_staleness(
    records: list[MemoryRecord],
    max_age_seconds: int | None = None,
) -> dict[str, Any]:
    """Diagnose temporal staleness across memory records.

    Returns per-namespace staleness statistics including:
    - oldest_record_age_seconds
    - avg_record_age_seconds
    - records_beyond_threshold
    - interference_score: fraction of record pairs with overlapping namespaces
      within a sliding age window (indicates potential interference/confusion).

    A higher interference_score suggests more temporal overlap and potential
    cross-talk between memories in the same namespace.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    if max_age_seconds is None:
        max_age_seconds = 24 * 3600  # default: 24h

    # Per-namespace stats
    ns_stats: dict[str, dict[str, Any]] = {}
    for rec in records:
        age = (now - rec.timestamp).total_seconds()
        if rec.namespace not in ns_stats:
            ns_stats[rec.namespace] = {
                "ages": [],
                "oldest": 0.0,
                "count": 0,
                "beyond_threshold": 0,
            }
        ns = ns_stats[rec.namespace]
        ns["ages"].append(age)
        ns["count"] += 1
        if age > ns["oldest"]:
            ns["oldest"] = age
        if age > max_age_seconds:
            ns["beyond_threshold"] += 1

    # Compute interference score: fraction of pairs within 24h in same namespace
    # that have overlapping recent activity
    interference_scores: dict[str, float] = {}
    for namespace, stats in ns_stats.items():
        ages = sorted(stats["ages"])
        n = len(ages)
        if n < 2:
            interference_scores[namespace] = 0.0
            continue

        # Count pairs within max_age_seconds of each other
        pair_count = 0
        total_pairs = n * (n - 1) // 2
        for i in range(n):
            for j in range(i + 1, n):
                if abs(ages[i] - ages[j]) <= max_age_seconds:
                    pair_count += 1

        interference_scores[namespace] = pair_count / total_pairs if total_pairs > 0 else 0.0

    return {
        "per_namespace": {ns: {"oldest_seconds": s["oldest"], "avg_seconds": sum(s["ages"]) / len(s["ages"]) if s["ages"] else 0, "beyond_threshold": s["beyond_threshold"], "interference_score": interference_scores.get(ns, 0.0)} for ns, s in ns_stats.items()},
        "max_age_seconds": max_age_seconds,
        "total_records": sum(s["count"] for s in ns_stats.values()),
    }
