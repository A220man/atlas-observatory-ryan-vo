from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid

from app.core.database import DatabaseManager
from app.models.swarm import (
    AuditLogEntry,
    BenchmarkRunRecord,
    DashboardSummaryMetrics,
    SubtaskInput,
    SwarmPlanCreateRequest,
    SwarmPlanListResponse,
    SwarmPlanRecord,
)
from app.services.benchmark_service import run_labeled_benchmark_suite
from app.services.planner_engine import evaluate_swarm_plan


SEED_PLANS: list[SwarmPlanCreateRequest] = [
    SwarmPlanCreateRequest(
        name="V3 Core Orchestrator & HNSW Memory Unification",
        objective="Decompose monolithic orchestrator into bounded domain modules, unify AgentDB HNSW indexing, and verify security invariants across a 12-agent hierarchical swarm.",
        topology="hierarchical",
        max_agents=12,
        horizon_threshold=5,
        mcp_call_threshold=2,
        subtasks=[
            SubtaskInput(
                id="adr-contracts",
                title="Specify DDD bounded context contracts for swarm and memory",
                role="architect",
                estimated_steps=3,
                mcp_calls=1,
                base_tokens=2200,
                depends_on=[],
            ),
            SubtaskInput(
                id="simulative-router",
                title="Implement conditional SimulativePlanningRouter pre-execution hook",
                role="coder",
                estimated_steps=4,
                mcp_calls=2,
                base_tokens=2900,
                depends_on=["adr-contracts"],
            ),
            SubtaskInput(
                id="hnsw-cache",
                title="Build HNSW SearchableEmbeddingCache with near-duplicate recall",
                role="coder",
                estimated_steps=4,
                mcp_calls=2,
                base_tokens=3100,
                depends_on=["adr-contracts"],
            ),
            SubtaskInput(
                id="witness-gate",
                title="Enforce non-zero exit code when platform dist manifests are missing",
                role="validator",
                estimated_steps=3,
                mcp_calls=2,
                base_tokens=1950,
                depends_on=["simulative-router", "hnsw-cache"],
            ),
        ],
    ),
    SwarmPlanCreateRequest(
        name="Dream-Cycle Temporal Memory & Skill Transfer Scan",
        objective="Audit multi-session memory staleness at 1M-token scale and evaluate cross-agent reusable skill promotion criteria.",
        topology="mesh",
        max_agents=6,
        horizon_threshold=5,
        mcp_call_threshold=2,
        subtasks=[
            SubtaskInput(
                id="sample-trajectories",
                title="Collect cross-session reasoning trajectories from ReasoningBank",
                role="researcher",
                estimated_steps=3,
                mcp_calls=2,
                base_tokens=1800,
                depends_on=[],
            ),
            SubtaskInput(
                id="aging-diagnostics",
                title="Score compression and interference aging across stored skills",
                role="analyst",
                estimated_steps=4,
                mcp_calls=1,
                base_tokens=2100,
                depends_on=["sample-trajectories"],
            ),
            SubtaskInput(
                id="promote-skills",
                title="Quarantine degraded patterns and promote verified reusable skills",
                role="validator",
                estimated_steps=2,
                mcp_calls=1,
                base_tokens=1400,
                depends_on=["aging-diagnostics"],
            ),
        ],
    ),
    SwarmPlanCreateRequest(
        name="Fast CLI Flag & Help Schema Check",
        objective="Verify CLI flag aliases (--topology, --agents, --name) and output formatting without external MCP calls.",
        topology="star",
        max_agents=3,
        horizon_threshold=5,
        mcp_call_threshold=2,
        subtasks=[
            SubtaskInput(
                id="parse-flags",
                title="Validate short and long CLI flag parser definitions",
                role="coder",
                estimated_steps=2,
                mcp_calls=0,
                base_tokens=720,
                depends_on=[],
            ),
            SubtaskInput(
                id="verify-help",
                title="Assert --help and --version exit codes",
                role="validator",
                estimated_steps=1,
                mcp_calls=1,
                base_tokens=540,
                depends_on=["parse-flags"],
            ),
        ],
    ),
]


class SwarmRepository:
    def __init__(self, db: DatabaseManager, shadow_pass_tokens: int = 256) -> None:
        self.db = db
        self.shadow_pass_tokens = shadow_pass_tokens

    def ensure_seed_data(self) -> None:
        with self.db.transaction() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM swarm_plans").fetchone()
            count = int(row["cnt"]) if row else 0
            if count > 0:
                return

        for seed_request in SEED_PLANS:
            self.create_plan(seed_request, actor="system-seed")

        self.run_and_store_benchmark(horizon_threshold=5, mcp_call_threshold=2, actor="system-seed")

    def create_plan(self, request: SwarmPlanCreateRequest, actor: str = "operator") -> SwarmPlanRecord:
        schedule, routing, topology_metrics = evaluate_swarm_plan(
            request, shadow_pass_tokens=self.shadow_pass_tokens
        )
        now = datetime.now(timezone.utc).isoformat()
        plan_id = f"plan-{uuid.uuid4().hex[:12]}"

        record = SwarmPlanRecord(
            id=plan_id,
            name=request.name,
            objective=request.objective,
            topology=request.topology,
            max_agents=request.max_agents,
            subtasks=request.subtasks,
            schedule=schedule,
            routing=routing,
            topology_metrics=topology_metrics,
            created_at=now,
            updated_at=now,
        )

        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO swarm_plans (
                    id, name, objective, topology, max_agents,
                    routing_mode, critical_path_steps, total_mcp_calls,
                    flat_tier3_tokens, selective_routed_tokens,
                    token_reduction_pct, parallel_efficiency_pct,
                    payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.name,
                    record.objective,
                    record.topology,
                    record.max_agents,
                    record.routing.mode,
                    record.routing.critical_path_steps,
                    record.routing.total_mcp_calls,
                    record.routing.flat_tier3_tokens,
                    record.routing.selective_routed_tokens,
                    record.routing.token_reduction_pct,
                    record.topology_metrics.parallel_efficiency_pct,
                    record.model_dump_json(),
                    record.created_at,
                    record.updated_at,
                ),
            )
            conn.execute(
                """
                INSERT INTO audit_logs (action, entity_type, entity_id, detail, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "create_swarm_plan",
                    "swarm_plan",
                    record.id,
                    f"Actor '{actor}' created plan '{record.name}' ({record.topology}, mode={record.routing.mode})",
                    now,
                ),
            )

        return record

    def list_plans(
        self,
        topology: str | None = None,
        routing_mode: str | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> SwarmPlanListResponse:
        clauses: list[str] = []
        params: list[object] = []

        if topology:
            clauses.append("topology = ?")
            params.append(topology)
        if routing_mode:
            clauses.append("routing_mode = ?")
            params.append(routing_mode)
        if search and search.strip():
            q = f"%{search.strip().lower()}%"
            clauses.append("(LOWER(name) LIKE ? OR LOWER(objective) LIKE ?)")
            params.extend([q, q])

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with self.db.transaction() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM swarm_plans {where_sql}",
                tuple(params),
            ).fetchone()
            total = int(total_row["cnt"]) if total_row else 0

            rows = conn.execute(
                f"""
                SELECT payload_json FROM swarm_plans
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                tuple([*params, limit, offset]),
            ).fetchall()

            summary_row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total_plans,
                    SUM(CASE WHEN routing_mode = 'simulative_forward_pass' THEN 1 ELSE 0 END) AS simulative_cnt,
                    SUM(CASE WHEN routing_mode = 'reactive_direct' THEN 1 ELSE 0 END) AS reactive_cnt,
                    AVG(token_reduction_pct) AS avg_reduction,
                    AVG(parallel_efficiency_pct) AS avg_efficiency,
                    SUM(flat_tier3_tokens - selective_routed_tokens) AS total_saved
                FROM swarm_plans
                """
            ).fetchone()

        items = [SwarmPlanRecord.model_validate_json(row["payload_json"]) for row in rows]

        summary = DashboardSummaryMetrics(
            total_plans=int(summary_row["total_plans"] or 0) if summary_row else 0,
            simulative_routed_count=int(summary_row["simulative_cnt"] or 0) if summary_row else 0,
            reactive_direct_count=int(summary_row["reactive_cnt"] or 0) if summary_row else 0,
            avg_token_reduction_pct=round(float(summary_row["avg_reduction"] or 0.0), 2) if summary_row else 0.0,
            avg_parallel_efficiency_pct=round(float(summary_row["avg_efficiency"] or 0.0), 1) if summary_row else 0.0,
            total_tokens_saved=max(0, int(summary_row["total_saved"] or 0)) if summary_row else 0,
        )

        return SwarmPlanListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            summary=summary,
        )

    def get_plan(self, plan_id: str) -> SwarmPlanRecord | None:
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT payload_json FROM swarm_plans WHERE id = ?",
                (plan_id,),
            ).fetchone()
        if not row:
            return None
        return SwarmPlanRecord.model_validate_json(row["payload_json"])

    def delete_plan(self, plan_id: str, actor: str = "operator") -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self.db.transaction() as conn:
            cursor = conn.execute("DELETE FROM swarm_plans WHERE id = ?", (plan_id,))
            deleted = cursor.rowcount > 0
            if deleted:
                conn.execute(
                    """
                    INSERT INTO audit_logs (action, entity_type, entity_id, detail, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        "delete_swarm_plan",
                        "swarm_plan",
                        plan_id,
                        f"Actor '{actor}' deleted swarm plan '{plan_id}'",
                        now,
                    ),
                )
        return deleted

    def run_and_store_benchmark(
        self,
        horizon_threshold: int = 5,
        mcp_call_threshold: int = 2,
        actor: str = "operator",
    ) -> BenchmarkRunRecord:
        result = run_labeled_benchmark_suite(
            horizon_threshold=horizon_threshold,
            mcp_call_threshold=mcp_call_threshold,
            shadow_pass_tokens=self.shadow_pass_tokens,
        )
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO benchmark_runs (
                    id, suite_name, horizon_threshold, mcp_call_threshold,
                    case_count, routing_accuracy_pct, baseline_total_tokens,
                    routed_total_tokens, overall_token_reduction_pct,
                    avg_overhead_ms, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.id,
                    result.suite_name,
                    result.horizon_threshold,
                    result.mcp_call_threshold,
                    result.case_count,
                    result.routing_accuracy_pct,
                    result.baseline_total_tokens,
                    result.routed_total_tokens,
                    result.overall_token_reduction_pct,
                    result.avg_overhead_ms,
                    result.model_dump_json(),
                    result.created_at,
                ),
            )
            conn.execute(
                """
                INSERT INTO audit_logs (action, entity_type, entity_id, detail, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "run_benchmark_suite",
                    "benchmark_run",
                    result.id,
                    (
                        f"Actor '{actor}' ran benchmark suite (accuracy={result.routing_accuracy_pct}%, "
                        f"token_reduction={result.overall_token_reduction_pct}%)"
                    ),
                    result.created_at,
                ),
            )
        return result

    def get_latest_benchmark(self) -> BenchmarkRunRecord | None:
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT payload_json FROM benchmark_runs ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        return BenchmarkRunRecord.model_validate_json(row["payload_json"])

    def list_audit_logs(self, limit: int = 25) -> list[AuditLogEntry]:
        with self.db.transaction() as conn:
            rows = conn.execute(
                """
                SELECT id, action, entity_type, entity_id, detail, created_at
                FROM audit_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            AuditLogEntry(
                id=int(r["id"]),
                action=str(r["action"]),
                entity_type=str(r["entity_type"]),
                entity_id=str(r["entity_id"]),
                detail=str(r["detail"]),
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]

    def export_plan_bundle(self, plan_id: str) -> dict[str, object] | None:
        plan = self.get_plan(plan_id)
        if plan is None:
            return None
        return {
            "schema_version": 1,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "tool": "atlas-observatory-ryan-vo",
            "plan": json.loads(plan.model_dump_json()),
        }
