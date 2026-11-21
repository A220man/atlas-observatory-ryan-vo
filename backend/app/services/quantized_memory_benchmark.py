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
