from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from app.models.witness import (
    PlatformVerificationResult,
    VerificationState,
    WitnessStampVerificationRequest,
    WitnessVerificationRequest,
)
from app.services.witness_verifier import (
    run_witness_verification,
    verify_platform_manifest,
    verify_witness_stamp_endpoint,
)


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _create_test_structure() -> tuple[Path, Path]:
    """Create a temporary directory structure with manifests and dist artifacts."""
    tmpdir = Path(tempfile.mkdtemp())
    manifest_dir = tmpdir / "verification"
    dist_dir = tmpdir / "dist"

    for platform in ("macos", "linux", "windows"):
        (manifest_dir / platform).mkdir(parents=True)

    (dist_dir / "macos" / "bin").mkdir(parents=True)
    (dist_dir / "linux" / "bin").mkdir(parents=True)
    (dist_dir / "windows" / "bin").mkdir(parents=True)

    return tmpdir, manifest_dir


def _write_manifest(manifest_dir: Path, platform: str, artifacts: dict[str, str]) -> Path:
    platform_dir = manifest_dir / platform
    platform_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = platform_dir / "manifest.md.json"
    data = {"artifacts": artifacts}
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return manifest_path


def _write_artifact(dist_dir: Path, platform: str, rel_path: str, content: bytes) -> Path:
    full_path = dist_dir / platform / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(content)
    return full_path


def _write_witness_stamp(manifest_dir: Path, platform: str, session_commit: str) -> Path:
    manifest_path = manifest_dir / platform / "manifest.md.json"
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_content = f.read()
    manifest_hash = hashlib.sha256(manifest_content.encode("utf-8")).hexdigest()
    combined = manifest_hash + session_commit
    stamp = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    witness_path = manifest_path.with_suffix(manifest_path.suffix + ".witness")
    witness_path.write_text(stamp, encoding="utf-8")
    return witness_path


def test_verified_clean_when_all_artifacts_match():
    tmpdir, manifest_dir = _create_test_structure()
    dist_dir = tmpdir / "dist"

    app_content = b"macos-app-binary-content"
    helper_content = b"macos-helper-binary-content"
    artifacts = {
        "macos/bin/app": _sha256_bytes(app_content),
        "macos/bin/helper": _sha256_bytes(helper_content),
    }
    _write_manifest(manifest_dir, "macos", artifacts)

    _write_artifact(dist_dir, "macos", "bin/app", app_content)
    _write_artifact(dist_dir, "macos", "bin/helper", helper_content)

    manifest_path = manifest_dir / "macos" / "manifest.md.json"
    import app.services.witness_verifier as wv
    manifest = wv._load_manifest(manifest_path)

    result = verify_platform_manifest(
        manifest=manifest,
        dist_root=dist_dir,
        require_dist_artifacts=True,
        session_commit=None,
    )

    assert result.state == VerificationState.VERIFIED_CLEAN
    assert result.entries_total == 2
    assert result.entries_verified == 2
    assert result.entries_missing == 0
    assert result.entries_mismatch == 0


def test_drift_detected_on_sha256_mismatch():
    tmpdir, manifest_dir = _create_test_structure()
    dist_dir = tmpdir / "dist"

    app_content = b"linux-app-binary-content"
    artifacts = {
        "linux/bin/app": _sha256_bytes(app_content),
    }
    _write_manifest(manifest_dir, "linux", artifacts)

    _write_artifact(dist_dir, "linux", "bin/app", b"wrong-content")

    manifest_path = manifest_dir / "linux" / "manifest.md.json"
    import app.services.witness_verifier as wv
    manifest = wv._load_manifest(manifest_path)

    result = verify_platform_manifest(
        manifest=manifest,
        dist_root=dist_dir,
        require_dist_artifacts=True,
        session_commit=None,
    )

    assert result.state == VerificationState.DRIFT_DETECTED
    assert result.entries_total == 1
    assert result.entries_verified == 0
    assert result.entries_mismatch == 1


def test_unverifiable_missing_build_when_all_artifacts_missing():
    tmpdir, manifest_dir = _create_test_structure()
    dist_dir = tmpdir / "dist"

    app_exe_content = b"windows-app-exe-content"
    helper_dll_content = b"windows-helper-dll-content"
    artifacts = {
        "windows/bin/app.exe": _sha256_bytes(app_exe_content),
        "windows/bin/helper.dll": _sha256_bytes(helper_dll_content),
    }
    _write_manifest(manifest_dir, "windows", artifacts)

    manifest_path = manifest_dir / "windows" / "manifest.md.json"
    import app.services.witness_verifier as wv
    manifest = wv._load_manifest(manifest_path)

    result = verify_platform_manifest(
        manifest=manifest,
        dist_root=dist_dir,
        require_dist_artifacts=True,
        session_commit=None,
    )

    assert result.state == VerificationState.UNVERIFIABLE_MISSING_BUILD
    assert result.entries_total == 2
    assert result.entries_missing == 2
    assert result.entries_verified == 0


def test_mixed_verified_and_missing_is_drift():
    tmpdir, manifest_dir = _create_test_structure()
    dist_dir = tmpdir / "dist"

    app_content = b"macos-app-binary-content"
    artifacts = {
        "macos/bin/app": _sha256_bytes(app_content),
        "macos/bin/missing": "g" * 64,
    }
    _write_manifest(manifest_dir, "macos", artifacts)

    _write_artifact(dist_dir, "macos", "bin/app", app_content)

    manifest_path = manifest_dir / "macos" / "manifest.md.json"
    import app.services.witness_verifier as wv
    manifest = wv._load_manifest(manifest_path)

    result = verify_platform_manifest(
        manifest=manifest,
        dist_root=dist_dir,
        require_dist_artifacts=True,
        session_commit=None,
    )

    assert result.state == VerificationState.DRIFT_DETECTED
    assert result.entries_verified == 1
    assert result.entries_missing == 1


def test_witness_stamp_verification_valid():
    tmpdir, manifest_dir = _create_test_structure()
    session_commit = "abc123"

    artifacts = {"macos/bin/app": "h" * 64}
    _write_manifest(manifest_dir, "macos", artifacts)
    _write_witness_stamp(manifest_dir, "macos", session_commit)

    request = WitnessStampVerificationRequest(
        manifest_path=str(manifest_dir / "macos" / "manifest.md.json"),
        session_commit=session_commit,
    )
    result = verify_witness_stamp_endpoint(request)

    assert result.valid is True
    assert result.session_commit == session_commit


def test_witness_stamp_verification_invalid_commit():
    tmpdir, manifest_dir = _create_test_structure()
    session_commit = "abc123"

    artifacts = {"macos/bin/app": "h" * 64}
    _write_manifest(manifest_dir, "macos", artifacts)
    _write_witness_stamp(manifest_dir, "macos", session_commit)

    request = WitnessStampVerificationRequest(
        manifest_path=str(manifest_dir / "macos" / "manifest.md.json"),
        session_commit="wrong-commit",
    )
    result = verify_witness_stamp_endpoint(request)

    assert result.valid is False


def test_run_witness_verification_all_platforms():
    tmpdir, manifest_dir = _create_test_structure()
    dist_dir = tmpdir / "dist"

    # macOS: all match
    macos_app_content = b"macos-app-binary-content"
    macos_artifacts = {"macos/bin/app": _sha256_bytes(macos_app_content)}
    _write_manifest(manifest_dir, "macos", macos_artifacts)
    _write_artifact(dist_dir, "macos", "bin/app", macos_app_content)

    # Linux: drift
    linux_app_content = b"linux-app-binary-content"
    linux_artifacts = {"linux/bin/app": _sha256_bytes(linux_app_content)}
    _write_manifest(manifest_dir, "linux", linux_artifacts)
    _write_artifact(dist_dir, "linux", "bin/app", b"wrong")

    # Windows: all missing
    windows_app_content = b"windows-app-exe-content"
    windows_artifacts = {"windows/bin/app.exe": _sha256_bytes(windows_app_content)}
    _write_manifest(manifest_dir, "windows", windows_artifacts)

    # Change cwd to tmpdir
    import os
    old_cwd = os.getcwd()
    os.chdir(tmpdir)
    try:
        request = WitnessVerificationRequest(manifest_dir="verification", require_dist_artifacts=True)
        result = run_witness_verification(request)

        assert result.overall_state == VerificationState.DRIFT_DETECTED
        assert len(result.platforms) == 3
        states = {p.platform: p.state for p in result.platforms}
        assert states["macos"] == VerificationState.VERIFIED_CLEAN
        assert states["linux"] == VerificationState.DRIFT_DETECTED
        assert states["windows"] == VerificationState.UNVERIFIABLE_MISSING_BUILD
    finally:
        os.chdir(old_cwd)


def test_run_witness_verification_no_manifests():
    tmpdir, manifest_dir = _create_test_structure()

    import os
    old_cwd = os.getcwd()
    os.chdir(tmpdir)
    try:
        request = WitnessVerificationRequest(manifest_dir="verification", require_dist_artifacts=True)
        result = run_witness_verification(request)

        assert result.overall_state == VerificationState.UNVERIFIABLE_MISSING_BUILD
        assert len(result.platforms) == 0
        assert "No platform manifests found" in result.summary
    finally:
        os.chdir(old_cwd)


def test_witness_stamp_missing_file():
    tmpdir, manifest_dir = _create_test_structure()
    session_commit = "abc123"

    artifacts = {"macos/bin/app": "h" * 64}
    _write_manifest(manifest_dir, "macos", artifacts)
    # No witness file written

    request = WitnessStampVerificationRequest(
        manifest_path=str(manifest_dir / "macos" / "manifest.md.json"),
        session_commit=session_commit,
    )
    result = verify_witness_stamp_endpoint(request)

    assert result.valid is False
    assert "Witness file not found" in result.detail