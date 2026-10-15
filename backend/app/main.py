from __future__ import annotations

from dataclasses import replace
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.database import DatabaseManager
from app.services.swarm_repository import SwarmRepository


def create_app(db_path: str | None = None, seed: bool = True) -> FastAPI:
    base_settings = get_settings()
    settings = replace(base_settings, db_path=db_path) if db_path is not None else base_settings

    application = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=(
            "Atlas Observatory: Multi-agent swarm topology analyzer and "
            "selective simulative planning router."
        ),
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    db_manager = DatabaseManager(settings.db_path)
    repo = SwarmRepository(db=db_manager, shadow_pass_tokens=settings.shadow_pass_tokens)
    if seed:
        repo.ensure_seed_data()

    application.state.settings = settings
    application.state.db = db_manager
    application.state.repo = repo

    application.include_router(router)
    return application


app = create_app()
