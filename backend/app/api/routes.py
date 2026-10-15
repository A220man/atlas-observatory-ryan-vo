from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from app.models.swarm import (
    AuditLogEntry,
    BenchmarkRunRecord,
    BenchmarkRunRequest,
    SwarmPlanCreateRequest,
    SwarmPlanListResponse,
    SwarmPlanRecord,
)
from app.services.planner_engine import PlannerValidationError
from app.services.swarm_repository import SwarmRepository

router = APIRouter(prefix="/api/v1")


def _get_repo(request: Request) -> SwarmRepository:
    repo: SwarmRepository = request.app.state.repo
    return repo


@router.get("/health")
def get_health(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "active_feature": "simulative-swarm-planner",
    }


@router.get("/swarms/plans", response_model=SwarmPlanListResponse)
def list_swarm_plans(
    request: Request,
    topology: str | None = Query(default=None),
    routing_mode: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SwarmPlanListResponse:
    repo = _get_repo(request)
    return repo.list_plans(
        topology=topology,
        routing_mode=routing_mode,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.post("/swarms/plans", response_model=SwarmPlanRecord, status_code=status.HTTP_201_CREATED)
def create_swarm_plan(
    payload: SwarmPlanCreateRequest,
    request: Request,
) -> SwarmPlanRecord:
    repo = _get_repo(request)
    try:
        return repo.create_plan(payload, actor="operator")
    except PlannerValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/swarms/plans/{plan_id}", response_model=SwarmPlanRecord)
def get_swarm_plan(plan_id: str, request: Request) -> SwarmPlanRecord:
    repo = _get_repo(request)
    record = repo.get_plan(plan_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm plan '{plan_id}' not found.",
        )
    return record


@router.get("/swarms/plans/{plan_id}/export")
def export_swarm_plan(plan_id: str, request: Request) -> dict[str, object]:
    repo = _get_repo(request)
    bundle = repo.export_plan_bundle(plan_id)
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm plan '{plan_id}' not found.",
        )
    return bundle


@router.delete(
    "/swarms/plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_swarm_plan(plan_id: str, request: Request) -> Response:
    repo = _get_repo(request)
    deleted = repo.delete_plan(plan_id, actor="operator")
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Swarm plan '{plan_id}' not found.",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/benchmarks/latest", response_model=BenchmarkRunRecord)
def get_latest_benchmark(request: Request) -> BenchmarkRunRecord:
    repo = _get_repo(request)
    latest = repo.get_latest_benchmark()
    if latest is None:
        return repo.run_and_store_benchmark(actor="auto-init")
    return latest


@router.post("/benchmarks/run", response_model=BenchmarkRunRecord, status_code=status.HTTP_201_CREATED)
def run_benchmark_evaluation(
    payload: BenchmarkRunRequest,
    request: Request,
) -> BenchmarkRunRecord:
    repo = _get_repo(request)
    return repo.run_and_store_benchmark(
        horizon_threshold=payload.horizon_threshold,
        mcp_call_threshold=payload.mcp_call_threshold,
        actor="operator",
    )


@router.get("/audit-logs", response_model=list[AuditLogEntry])
def list_audit_logs(
    request: Request,
    limit: int = Query(default=25, ge=1, le=100),
) -> list[AuditLogEntry]:
    repo = _get_repo(request)
    return repo.list_audit_logs(limit=limit)
