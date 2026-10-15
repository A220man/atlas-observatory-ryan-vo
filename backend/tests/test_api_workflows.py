from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def _make_client() -> TestClient:
    app = create_app(db_path=":memory:", seed=True)
    return TestClient(app)


def test_health_endpoint_returns_version_and_active_feature() -> None:
    client = _make_client()
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == "1.0.0"
    assert body["active_feature"] == "simulative-swarm-planner"


def test_seeded_swarm_plans_list_and_filtering() -> None:
    client = _make_client()
    resp = client.get("/api/v1/swarms/plans")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["summary"]["total_plans"] == 3
    assert data["summary"]["simulative_routed_count"] == 2
    assert data["summary"]["reactive_direct_count"] == 1

    # Filter by topology
    hier_resp = client.get("/api/v1/swarms/plans", params={"topology": "hierarchical"})
    assert hier_resp.status_code == 200
    assert hier_resp.json()["total"] == 1

    # Filter by routing_mode
    reactive_resp = client.get(
        "/api/v1/swarms/plans", params={"routing_mode": "reactive_direct"}
    )
    assert reactive_resp.status_code == 200
    assert reactive_resp.json()["total"] == 1
    assert reactive_resp.json()["items"][0]["topology"] == "star"


def test_create_get_export_and_delete_swarm_plan_workflow() -> None:
    client = _make_client()
    payload = {
        "name": "Cross-Agent Skill Lifecycle Validation",
        "objective": "Evaluate experience-aware skill creation, quarantine, and transfer across 5 agents.",
        "topology": "hierarchical",
        "max_agents": 5,
        "horizon_threshold": 5,
        "mcp_call_threshold": 2,
        "subtasks": [
            {
                "id": "extract-skill",
                "title": "Distill candidate skill from verified trajectory",
                "role": "researcher",
                "estimated_steps": 3,
                "mcp_calls": 1,
                "base_tokens": 1600,
                "depends_on": [],
            },
            {
                "id": "sandbox-eval",
                "title": "Run regression test harness on candidate skill",
                "role": "validator",
                "estimated_steps": 4,
                "mcp_calls": 2,
                "base_tokens": 2200,
                "depends_on": ["extract-skill"],
            },
        ],
    }

    create_resp = client.post("/api/v1/swarms/plans", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    plan_id = created["id"]
    assert created["routing"]["mode"] == "simulative_forward_pass"
    assert created["routing"]["critical_path_steps"] == 7
    assert created["routing"]["token_reduction_pct"] > 15.0

    # Fetch detail
    detail_resp = client.get(f"/api/v1/swarms/plans/{plan_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["name"] == payload["name"]

    # Export bundle
    export_resp = client.get(f"/api/v1/swarms/plans/{plan_id}/export")
    assert export_resp.status_code == 200
    bundle = export_resp.json()
    assert bundle["schema_version"] == 1
    assert bundle["plan"]["id"] == plan_id

    # Delete plan
    del_resp = client.delete(f"/api/v1/swarms/plans/{plan_id}")
    assert del_resp.status_code == 204

    # Verify 404 after deletion
    missing_resp = client.get(f"/api/v1/swarms/plans/{plan_id}")
    assert missing_resp.status_code == 404


def test_create_plan_rejects_cycle_and_malformed_inputs_with_422() -> None:
    client = _make_client()
    cyclic_payload = {
        "name": "Invalid Cycle Workflow",
        "objective": "Verify API returns 422 on dependency cycle.",
        "topology": "ring",
        "max_agents": 4,
        "subtasks": [
            {
                "id": "node-1",
                "title": "First subtask",
                "role": "coder",
                "estimated_steps": 2,
                "mcp_calls": 0,
                "base_tokens": 500,
                "depends_on": ["node-2"],
            },
            {
                "id": "node-2",
                "title": "Second subtask",
                "role": "coder",
                "estimated_steps": 2,
                "mcp_calls": 0,
                "base_tokens": 500,
                "depends_on": ["node-1"],
            },
        ],
    }
    resp = client.post("/api/v1/swarms/plans", json=cyclic_payload)
    assert resp.status_code == 422
    assert "cycle" in resp.json()["detail"].lower()


def test_benchmark_run_and_audit_log_recording() -> None:
    client = _make_client()
    latest_resp = client.get("/api/v1/benchmarks/latest")
    assert latest_resp.status_code == 200
    latest = latest_resp.json()
    assert latest["case_count"] == 8
    assert latest["routing_accuracy_pct"] == 100.0

    # Trigger custom threshold run
    custom_run = client.post(
        "/api/v1/benchmarks/run",
        json={"horizon_threshold": 4, "mcp_call_threshold": 2},
    )
    assert custom_run.status_code == 201
    assert custom_run.json()["horizon_threshold"] == 4

    # Check audit log entries
    logs_resp = client.get("/api/v1/audit-logs")
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert len(logs) >= 4
    assert logs[0]["action"] == "run_benchmark_suite"
