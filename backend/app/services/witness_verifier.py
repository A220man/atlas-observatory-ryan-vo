from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from app.models.witness import (
    ArtifactVerificationResult,
    PlatformManifest,
    PlatformVerificationResult,
    VerificationState,
    WitnessStampVerificationRequest,
    WitnessStampVerificationResponse,
    WitnessVerificationRequest,
    WitnessVerificationResponse,
)


ED25519_PUBLIC_KEY_HEX = "0000000000000000000000000000000000000000000000000000000000000000"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest(manifest_path: Path) -> PlatformManifest | None:
    try:
        with manifest_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        platform = manifest_path.parent.name
        if platform not in ("macos", "linux", "windows"):
            return None
        entries = data.get("artifacts", {})
        return PlatformManifest(platform=platform, manifest_path=str(manifest_path), entries=entries)
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def _verify_witness_stamp(manifest_path: Path, session_commit: str) -> tuple[bool, str]:
    """
    Witness stamp verification per ruflo pattern:
    sha256(sha256sum(manifest_file) + session_commit)
    """
    try:
        with manifest_path.open("r", encoding="utf-8") as f:
            manifest_content = f.read()
        manifest_hash = hashlib.sha256(manifest_content.encode("utf-8")).hexdigest()
        combined = manifest_hash + session_commit
        computed = hashlib.sha256(combined.encode("utf-8")).hexdigest()

        witness_file = manifest_path.with_suffix(manifest_path.suffix + ".witness")
        if not witness_file.exists():
            return False, f"Witness file not found: {witness_file}"

        with witness_file.open("r", encoding="utf-8") as f:
            stored = f.read().strip()

        return computed == stored, f"computed={computed}, stored={stored}"
    except OSError as e:
        return False, f"Error reading files: {e}"


def verify_platform_manifest(
    manifest: PlatformManifest,
    dist_root: Path,
    require_dist_artifacts: bool,
    session_commit: str | None = None,
) -> PlatformVerificationResult:
    results: list[ArtifactVerificationResult] = []
    entries_verified = 0
    entries_missing = 0
    entries_mismatch = 0

    for artifact_path, expected_sha256 in manifest.entries.items():
        full_path = dist_root / artifact_path
        if full_path.exists():
            actual_sha256 = _sha256_file(full_path)
            match = actual_sha256 == expected_sha256
            if match:
                entries_verified += 1
            else:
                entries_mismatch += 1
            results.append(
                ArtifactVerificationResult(
                    artifact_path=artifact_path,
                    expected_sha256=expected_sha256,
                    actual_sha256=actual_sha256,
                    exists=True,
                    match=match,
                )
            )
        else:
            entries_missing += 1
            results.append(
                ArtifactVerificationResult(
                    artifact_path=artifact_path,
                    expected_sha256=expected_sha256,
                    actual_sha256=None,
                    exists=False,
                    match=None,
                )
            )

    entries_total = len(manifest.entries)

    if entries_missing == entries_total and entries_total > 0:
        state = VerificationState.UNVERIFIABLE_MISSING_BUILD
    elif entries_mismatch > 0:
        state = VerificationState.DRIFT_DETECTED
    elif entries_verified == entries_total and entries_total > 0:
        state = VerificationState.VERIFIED_CLEAN
    elif entries_verified > 0 and entries_missing > 0:
        state = VerificationState.DRIFT_DETECTED
    else:
        state = VerificationState.UNVERIFIABLE_MISSING_BUILD

    witness_stamp_valid = None
    witness_stamp_detail = None
    if session_commit and state != VerificationState.UNVERIFIABLE_MISSING_BUILD:
        manifest_file = Path(manifest.manifest_path)
        witness_stamp_valid, witness_stamp_detail = _verify_witness_stamp(
            manifest_file, session_commit
        )
        if not witness_stamp_valid:
            state = VerificationState.DRIFT_DETECTED

    return PlatformVerificationResult(
        platform=manifest.platform,
        state=state,
        entries_total=entries_total,
        entries_verified=entries_verified,
        entries_missing=entries_missing,
        entries_mismatch=entries_mismatch,
        results=results,
        witness_stamp_valid=witness_stamp_valid,
        witness_stamp_detail=witness_stamp_detail,
    )


def run_witness_verification(request: WitnessVerificationRequest) -> WitnessVerificationResponse:
    repo_root = Path.cwd()
    manifest_dir = repo_root / request.manifest_dir
    dist_root = repo_root / "dist"

    platforms: list[PlatformVerificationResult] = []

    for platform_name in ("macos", "linux", "windows"):
        manifest_path = manifest_dir / platform_name / "manifest.md.json"
        if not manifest_path.exists():
            continue
        manifest = _load_manifest(manifest_path)
        if manifest is None:
            continue

        session_commit = None
        commit_file = repo_root / ".git" / "HEAD"
        if commit_file.exists():
            try:
                with commit_file.open("r") as f:
                    session_commit = f.read().strip()
            except OSError:
                pass

        result = verify_platform_manifest(
            manifest=manifest,
            dist_root=dist_root,
            require_dist_artifacts=request.require_dist_artifacts,
            session_commit=session_commit,
        )
        platforms.append(result)

    if not platforms:
        return WitnessVerificationResponse(
            overall_state=VerificationState.UNVERIFIABLE_MISSING_BUILD,
            platforms=[],
            summary="No platform manifests found",
        )

    states = [p.state for p in platforms]
    if all(s == VerificationState.VERIFIED_CLEAN for s in states):
        overall_state = VerificationState.VERIFIED_CLEAN
    elif any(s == VerificationState.DRIFT_DETECTED for s in states):
        overall_state = VerificationState.DRIFT_DETECTED
    else:
        overall_state = VerificationState.UNVERIFIABLE_MISSING_BUILD

    summary_parts = []
    for p in platforms:
        summary_parts.append(
            f"{p.platform}: {p.state.value} ({p.entries_verified}/{p.entries_total} verified, {p.entries_missing} missing, {p.entries_mismatch} mismatch)"
        )

    return WitnessVerificationResponse(
        overall_state=overall_state,
        platforms=platforms,
        summary="; ".join(summary_parts),
    )


def verify_witness_stamp_endpoint(request: WitnessStampVerificationRequest) -> WitnessStampVerificationResponse:
    manifest_path = Path(request.manifest_path)
    if not manifest_path.exists():
        return WitnessStampVerificationResponse(
            manifest_path=request.manifest_path,
            witness_stamp="",
            computed_stamp="",
            valid=False,
            session_commit=request.session_commit,
            detail="Manifest file not found",
        )

    valid, detail = _verify_witness_stamp(manifest_path, request.session_commit)

    witness_file = manifest_path.with_suffix(manifest_path.suffix + ".witness")
    stored_stamp = ""
    if witness_file.exists():
        with witness_file.open("r") as f:
            stored_stamp = f.read().strip()

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest_content = f.read()
    manifest_hash = hashlib.sha256(manifest_content.encode("utf-8")).hexdigest()
    combined = manifest_hash + request.session_commit
    computed = hashlib.sha256(combined.encode("utf-8")).hexdigest()

    return WitnessStampVerificationResponse(
        manifest_path=request.manifest_path,
        witness_stamp=stored_stamp,
        computed_stamp=computed,
        valid=valid,
        session_commit=request.session_commit,
        detail=detail,
    )