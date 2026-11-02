from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid
from typing import Any

from app.core.database import DatabaseManager
from app.models.goap import (
    GOAPAction,
    GOAPGoal,
    GOAPPlanListResponse,
    GOAPPlanRecord,
    GOAPPlanRequest,
    GOAPPlanResponse,
    GOAPPlanStep,
)


class GOAPRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def create_plan(self, name: str, request: GOAPPlanRequest, response: GOAPPlanResponse, actor: str = "operator") -> GOAPPlanRecord:
        now = datetime.now(timezone.utc).isoformat()
        plan_id = str(uuid.uuid4())

        with self.db.transaction() as conn:
            conn.execute(
                """INSERT INTO goap_plans
                   (id, name, initial_state_json, actions_json, goals_json, plan_json,
                    total_cost, final_state_json, nodes_expanded, search_time_ms, success,
                    error_message, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    plan_id,
                    name,
                    json.dumps(request.initial_state),
                    json.dumps([a.model_dump() for a in request.actions]),
                    json.dumps([g.model_dump() for g in request.goals]),
                    json.dumps([step.model_dump() for step in response.plan]),
                    response.total_cost,
                    json.dumps(response.final_state),
                    response.nodes_expanded,
                    response.search_time_ms,
                    1 if response.success else 0,
                    response.error_message,
                    now,
                    now,
                ),
            )
            conn.execute(
                "INSERT INTO audit_logs (action, entity_type, entity_id, detail, created_at) VALUES (?, ?, ?, ?, ?)",
                ("create", "goap_plan", plan_id, f"Created GOAP plan by {actor}", now),
            )

        return GOAPPlanRecord(
            id=plan_id,
            name=name,
            initial_state=request.initial_state,
            actions=request.actions,
            goals=request.goals,
            plan=response.plan,
            total_cost=response.total_cost,
            final_state=response.final_state,
            nodes_expanded=response.nodes_expanded,
            search_time_ms=response.search_time_ms,
            success=response.success,
            error_message=response.error_message,
            created_at=now,
            updated_at=now,
        )

    def list_plans(self, limit: int = 50, offset: int = 0, success_filter: bool | None = None) -> GOAPPlanListResponse:
        clauses = []
        params: list[Any] = []

        if success_filter is not None:
            clauses.append("success = ?")
            params.append(1 if success_filter else 0)

        where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""

        with self.db.transaction() as conn:
            total_row = conn.execute(f"SELECT COUNT(*) as count FROM goap_plans{where_sql}", params).fetchone()
            total = total_row["count"] if total_row else 0

            params.extend([limit, offset])
            rows = conn.execute(
                f"SELECT * FROM goap_plans{where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params,
            ).fetchall()

        items = []
        for row in rows:
            plan_steps = [GOAPPlanStep.model_validate(s) for s in json.loads(row["plan_json"])]
            items.append(
                GOAPPlanRecord(
                    id=row["id"],
                    name=row["name"],
                    initial_state=json.loads(row["initial_state_json"]),
                    actions=[GOAPAction.model_validate(a) for a in json.loads(row["actions_json"])],
                    goals=[GOAPGoal.model_validate(g) for g in json.loads(row["goals_json"])],
                    plan=plan_steps,
                    total_cost=row["total_cost"],
                    final_state=json.loads(row["final_state_json"]),
                    nodes_expanded=row["nodes_expanded"],
                    search_time_ms=row["search_time_ms"],
                    success=bool(row["success"]),
                    error_message=row["error_message"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )

        return GOAPPlanListResponse(items=items, total=total)

    def get_plan(self, plan_id: str) -> GOAPPlanRecord | None:
        with self.db.transaction() as conn:
            row = conn.execute("SELECT * FROM goap_plans WHERE id = ?", (plan_id,)).fetchone()
            if not row:
                return None

            plan_steps = [GOAPPlanStep.model_validate(s) for s in json.loads(row["plan_json"])]
            return GOAPPlanRecord(
                id=row["id"],
                name=row["name"],
                initial_state=json.loads(row["initial_state_json"]),
                actions=[GOAPAction.model_validate(a) for a in json.loads(row["actions_json"])],
                goals=[GOAPGoal.model_validate(g) for g in json.loads(row["goals_json"])],
                plan=plan_steps,
                total_cost=row["total_cost"],
                final_state=json.loads(row["final_state_json"]),
                nodes_expanded=row["nodes_expanded"],
                search_time_ms=row["search_time_ms"],
                success=bool(row["success"]),
                error_message=row["error_message"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def delete_plan(self, plan_id: str, actor: str = "operator") -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.transaction() as conn:
            cursor = conn.execute("DELETE FROM goap_plans WHERE id = ?", (plan_id,))
            deleted = cursor.rowcount > 0
            if deleted:
                conn.execute(
                    "INSERT INTO audit_logs (action, entity_type, entity_id, detail, created_at) VALUES (?, ?, ?, ?, ?)",
                    ("delete", "goap_plan", plan_id, f"Deleted GOAP plan by {actor}", now),
                )
        return deleted

