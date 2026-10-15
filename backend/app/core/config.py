from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _read_version() -> str:
    candidates = [
        Path(__file__).resolve().parents[3] / "VERSION",
        Path(__file__).resolve().parents[2] / "VERSION",
    ]
    for candidate in candidates:
        if candidate.is_file():
            content = candidate.read_text(encoding="utf-8").strip()
            if content:
                return content
    return "1.0.0"


@dataclass(frozen=True)
class Settings:
    app_name: str
    version: str
    environment: str
    db_path: str
    default_horizon_threshold: int
    default_mcp_call_threshold: int
    shadow_pass_tokens: int


def get_settings() -> Settings:
    return Settings(
        app_name="Atlas Observatory",
        version=_read_version(),
        environment=os.getenv("ATLAS_ENV", "development").strip() or "development",
        db_path=os.getenv("ATLAS_DB_PATH", "backend/atlas_observatory.db").strip() or "backend/atlas_observatory.db",
        default_horizon_threshold=int(os.getenv("ATLAS_HORIZON_THRESHOLD", "5")),
        default_mcp_call_threshold=int(os.getenv("ATLAS_MCP_CALL_THRESHOLD", "2")),
        shadow_pass_tokens=int(os.getenv("ATLAS_SHADOW_PASS_TOKENS", "256")),
    )
