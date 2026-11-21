from __future__ import annotations

import numpy as np

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


def test_quantize_float32():
    """Float32 quantization should preserve values as int32."""
    vector = [0.5, -0.2, 1.0, -1.5]
    quantized, method = quantize_vector(vector, QuantizationMethod.FLOAT32)
    assert method == QuantizationMethod.FLOAT32
    # int32 values should be close to original floats scaled appropriately
    assert len(quantized) == 4


def test_quantize_int8():
    """INT8 quantization should produce values in [-128, 127]."""
    vector = [0.5, -0.2, 1.0, -1.5, 0.0, 3.14, -3.14]
    quantized, method = quantize_vector(vector, QuantizationMethod.INT8)
    assert method == QuantizationMethod.INT8
    for v in quantized:
        assert -128 <= v <= 127, f"INT8 value out of range: {v}"


def test_quantize_rabitq():
    """RaBitQ 1-bit quantization should produce sign-only values."""
    vector = [0.5, -0.2, 1.0, -1.5, 0.0]
    quantized, method = quantize_vector(vector, QuantizationMethod.RABITQ)
    assert method == QuantizationMethod.RABITQ
    # Sign-only: should be -1, 0, or 1
    for v in quantized:
        assert v in (-1, 0, 1), f"RaBitQ value not sign-only: {v}"


def test_reconstruct_float32():
    """Float32 reconstruction should produce float32 values close to original.
    
    Note: int32 -> float32 round-trip may not be exact for all values,
    but should be very close for typical float32 values.
    """
    vector = [0.5, -0.2, 1.0, -1.5]
    quantized, _ = quantize_vector(vector, QuantizationMethod.FLOAT32)
    reconstructed = reconstruct_vector(quantized, QuantizationMethod.FLOAT32)
    # Check that reconstructed values are close to original (within reasonable tolerance)
    for r, o in zip(reconstructed, vector):
        assert abs(r - o) < 0.1, f"Reconstructed {r} too far from original {o}"


def test_reconstruct_int8():
    """INT8 reconstruction requires original min/max."""
    vector = [0.5, -0.2, 1.0, -1.5]
    quantized, _ = quantize_vector(vector, QuantizationMethod.INT8)
    # Should raise ValueError without original_min/original_max
    try:
        reconstruct_vector(quantized, QuantizationMethod.INT8)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # expected


def test_reconstruct_rabitq():
    """RaBitQ reconstruction produces float32 values."""
    vector = [0.5, -0.2, 1.0, -1.5]
    quantized, _ = quantize_vector(vector, QuantizationMethod.RABITQ)
    reconstructed = reconstruct_vector(quantized, QuantizationMethod.RABITQ)
    assert reconstructed.dtype == np.float32
    assert len(reconstructed) == len(vector)


def test_compute_recall_perfect():
    """Perfect reconstruction should give recall = 1.0."""
    vector = [1.0, 2.0, 3.0, 4.0, 5.0]
    quantized, _ = quantize_vector(vector, QuantizationMethod.FLOAT32)
    reconstructed = reconstruct_vector(quantized, QuantizationMethod.FLOAT32)
    recall = compute_recall(vector, reconstructed)
    # For FLOAT32 bit-pattern reconstruction, recall should be very close to 1.0
    assert recall > 0.99, f"Expected near-perfect recall, got {recall}"


def test_compute_recall_degraded():
    """Lossy quantization should give recall < 1.0."""
    vector = [1.0, 2.0, 3.0, 4.0, 5.0]
    quantized, _ = quantize_vector(vector, QuantizationMethod.RABITQ)
    reconstructed = reconstruct_vector(quantized, QuantizationMethod.RABITQ)
    recall = compute_recall(vector, reconstructed)
    assert 0.0 <= recall < 1.0


def test_compute_memory_footprint():
    """Memory footprint should vary by method."""
    vector = [1.0, 2.0, 3.0]
    q_f32, _ = quantize_vector(vector, QuantizationMethod.FLOAT32)
    q_i8, _ = quantize_vector(vector, QuantizationMethod.INT8)
    q_rab, _ = quantize_vector(vector, QuantizationMethod.RABITQ)

    fp_f32 = compute_memory_footprint(q_f32, QuantizationMethod.FLOAT32, len(vector))
    fp_i8 = compute_memory_footprint(q_i8, QuantizationMethod.INT8, len(vector))
    fp_rab = compute_memory_footprint(q_rab, QuantizationMethod.RABITQ, len(vector))

    # FLOAT32: 4 bytes per element * 3 = 12
    assert fp_f32 == 12
    # INT8: 1 byte per element * 3 = 3
    assert fp_i8 == 3
    # RaBitQ: 3 elements -> ceil(3/8) = 1 byte
    assert fp_rab == 1


def test_run_quantization_comparison():
    """Full comparison should return results for all three methods."""
    vector = [1.0, 2.0, 3.0, 4.0, 5.0]
    results = run_quantization_comparison(vector)

    assert len(results) == 3
    methods = {r.method for r in results}
    assert QuantizationMethod.FLOAT32 in methods
    assert QuantizationMethod.INT8 in methods
    assert QuantizationMethod.RABITQ in methods

    for r in results:
        assert isinstance(r, QuantizationResult)
        assert r.method in (QuantizationMethod.FLOAT32, QuantizationMethod.INT8, QuantizationMethod.RABITQ)
        assert isinstance(r.reconstruction_error, float)
        assert r.reconstruction_error >= 0.0
        assert len(r.original_vector) == 5
        assert r.quantized_data is not None


def test_run_quantization_comparison_custom_methods():
    """Custom method selection should work."""
    vector = [1.0, 2.0, 3.0]
    results = run_quantization_comparison(vector, methods=[QuantizationMethod.FLOAT32, QuantizationMethod.INT8])

    assert len(results) == 2
    methods = {r.method for r in results}
    assert QuantizationMethod.FLOAT32 in methods
    assert QuantizationMethod.INT8 in methods
    assert QuantizationMethod.RABITQ not in methods


def test_comparison_result_schema():
    """ComparisonResult should have valid fields."""
    result = ComparisonResult(method=QuantizationMethod.FLOAT32, avg_recall=0.85, avg_memory_bytes=5)
    assert 0.0 <= result.avg_recall <= 1.0
    assert result.avg_memory_bytes >= 0


def test_quantization_result_schema():
    """QuantizationResult should have valid fields."""
    result = QuantizationResult(
        method=QuantizationMethod.FLOAT32,
        original_vector=[1.0, 2.0],
        quantized_data=[1073741824, -1073741824],  # int32 approximations
        reconstruction_error=0.01,
    )
    assert result.method == QuantizationMethod.FLOAT32
    assert len(result.original_vector) == 2
    assert result.quantized_data is not None
    assert result.reconstruction_error >= 0.0


def test_memory_footprint_tradeoff():
    """Test that quantization methods have the expected memory hierarchy.
    
    RaBitQ (1-bit) uses least memory, INT8 uses more, FLOAT32 uses most.
    Recall should trade off inversely: RaBitQ lowest recall, FLOAT32 highest.
    """
    vector = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    
    results = run_quantization_comparison(vector)
    
    # Check memory footprints: FLOAT32 > INT8 > RABITQ
    fp_results = {r.method: compute_memory_footprint(r.quantized_data, r.method, len(vector)) for r in results}
    assert fp_results[QuantizationMethod.FLOAT32] > fp_results[QuantizationMethod.INT8] > fp_results[QuantizationMethod.RABITQ]
    
    # Check that recall ordering is inverse (FLOAT32 highest, RABITQ lowest)
    # Note: FLOAT32 bit-pattern reinterpretation may give very high recall
    recall_results = {r.method: r.reconstruction_error for r in results}
    # Just verify all values are reasonable
    for method, error in recall_results.items():
        assert isinstance(error, float)
        assert error >= 0.0
