from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field
from typing import Literal


class VerificationState(str, Enum):
    VERIFIED_CLEAN = "verified_clean"
    DRIFT_DETECTED = "drift_detected"
    UNVERIFIABLE_MISSING_BUILD = "unverifiable_missing_build"


class PlatformManifest(BaseModel):
    platform: Literal["macos", "linux", "windows"]
    manifest_path: str
    entries: dict[str, str]  # artifact_path -> sha256_hex


class ArtifactVerificationResult(BaseModel):
    artifact_path: str
    expected_sha256: str
    actual_sha256: str | None
    exists: bool
    match: bool | None


class PlatformVerificationResult(BaseModel):
    platform: Literal["macos", "linux", "windows"]
    state: VerificationState
    entries_total: int
    entries_verified: int
    entries_missing: int
    entries_mismatch: int
    results: list[ArtifactVerificationResult]
    witness_stamp_valid: bool | None
    witness_stamp_detail: str | None


class WitnessVerificationRequest(BaseModel):
    manifest_dir: str = Field(default="verification")
    require_dist_artifacts: bool = Field(default=True)


class WitnessVerificationResponse(BaseModel):
    overall_state: VerificationState
    platforms: list[PlatformVerificationResult]
    summary: str


class WitnessStampVerificationRequest(BaseModel):
    manifest_path: str
    session_commit: str


class WitnessStampVerificationResponse(BaseModel):
    manifest_path: str
    witness_stamp: str
    computed_stamp: str
    valid: bool
    session_commit: str
    detail: str