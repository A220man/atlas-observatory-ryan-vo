from __future__ import annotations

import pytest

from app.models.swarm import SubtaskInput, SwarmPlanCreateRequest
from app.services.benchmark_service import run_labeled_benchmark_suite
from app.services.planner_engine import PlannerValidationError, evaluate_swarm_plan


def test_reactive_direct_routing_for_shallow_low_mcp_plan() -> None:
    req = SwarmPlanCreateRequest(
        name="Shallow Two-Step Check",
        objective="Run quick local status check with minimal tool overhead.",
        topology="star",
        max_agents=3,
        horizon_threshold=5,
        mcp_call_threshold=2,
        subtasks=[
            SubtaskInput(
                id="step-a",
                title="Read local config",
                role="analyst",
                estimated_steps=2,
                mcp_calls=0,
                base_tokens=600,
                depends_on=[],
            ),
            SubtaskInput(
                id="step-b",
                title="Emit formatted report",
                role="coder",
                estimated_steps=1,
                mcp_calls=1,
                base_tokens=500,
                depends_on=["step-a"],
            ),
        ],
    )
    schedule, routing, topo = evaluate_swarm_plan(req)
    assert routing.mode == "reactive_direct"
    assert routing.triggered_by == []
    assert routing.critical_path_steps == 3
    assert routing.total_mcp_calls == 1
    assert routing.shadow_pass_tokens == 0
    assert len(schedule) == 2
    assert topo.topology == "star"


def test_simulative_forward_pass_triggered_by_critical_path_horizon() -> None:
    req = SwarmPlanCreateRequest(
        name="Deep Sequential Refactor",
        objective="Execute multi-stage architectural decomposition exceeding 5-step horizon.",
        topology="hierarchical",
        max_agents=6,
        horizon_threshold=5,
        mcp_call_threshold=4,
        subtasks=[
            SubtaskInput(
                id="design",
                title="Design domain boundaries",
                role="architect",
                estimated_steps=3,
                mcp_calls=0,
                base_tokens=2000,
                depends_on=[],
            ),
            SubtaskInput(
                id="implement",
                title="Implement core router service",
                role="coder",
                estimated_steps=4,
                mcp_calls=1,
                base_tokens=2800,
                depends_on=["design"],
            ),
        ],
    )
    _, routing, _ = evaluate_swarm_plan(req, shadow_pass_tokens=256)
    assert routing.mode == "simulative_forward_pass"
    assert routing.critical_path_steps == 7
    assert any("critical_path_horizon" in reason for reason in routing.triggered_by)
    assert routing.shadow_pass_tokens == 256
    assert routing.selective_routed_tokens < routing.flat_tier3_tokens
    assert routing.token_reduction_pct > 15.0


def test_simulative_forward_pass_triggered_by_mcp_call_density() -> None:
    req = SwarmPlanCreateRequest(
        name="High MCP Density Retrieval",
        objective="Coordinate multi-tool vector and federation lookups.",
        topology="ring",
        max_agents=4,
        horizon_threshold=10,
        mcp_call_threshold=2,
        subtasks=[
            SubtaskInput(
                id="rag-fetch",
                title="Query HNSW memory and federation breaker status",
                role="researcher",
                estimated_steps=2,
                mcp_calls=3,
                base_tokens=1800,
                depends_on=[],
            )
        ],
    )
    _, routing, _ = evaluate_swarm_plan(req)
    assert routing.mode == "simulative_forward_pass"
    assert routing.critical_path_steps == 2
    assert routing.total_mcp_calls == 3
    assert any("mcp_call_density" in reason for reason in routing.triggered_by)


def test_dag_critical_path_identifies_longest_branch_not_sum() -> None:
    req = SwarmPlanCreateRequest(
        name="Diamond Dependency Graph",
        objective="Verify critical path follows longest parallel branch.",
        topology="hierarchical",
        max_agents=6,
        subtasks=[
            SubtaskInput(
                id="root",
                title="Initialize workspace",
                role="coordinator",
                estimated_steps=2,
                mcp_calls=0,
                base_tokens=1000,
                depends_on=[],
            ),
            SubtaskInput(
                id="fast-branch",
                title="Fast lint check",
                role="validator",
                estimated_steps=1,
                mcp_calls=0,
                base_tokens=800,
                depends_on=["root"],
            ),
            SubtaskInput(
                id="slow-branch",
                title="Deep HNSW index build",
                role="coder",
                estimated_steps=5,
                mcp_calls=2,
                base_tokens=2400,
                depends_on=["root"],
            ),
            SubtaskInput(
                id="join",
                title="Verify integrated build",
                role="validator",
                estimated_steps=2,
                mcp_calls=1,
                base_tokens=1200,
                depends_on=["fast-branch", "slow-branch"],
            ),
        ],
    )
    schedule, routing, _ = evaluate_swarm_plan(req)
    assert routing.critical_path_steps == 9  # 2 (root) + 5 (slow-branch) + 2 (join)
    assert routing.total_steps == 10
    by_id = {node.id: node for node in schedule}
    assert by_id["root"].on_critical_path is True
    assert by_id["slow-branch"].on_critical_path is True
    assert by_id["join"].on_critical_path is True
    assert by_id["fast-branch"].on_critical_path is False


def test_rejects_cyclic_subtask_dependencies() -> None:
    req = SwarmPlanCreateRequest(
        name="Cyclic Plan",
        objective="Should fail cycle validation.",
        topology="mesh",
        max_agents=4,
        subtasks=[
            SubtaskInput(
                id="a",
                title="Task A",
                role="coder",
                estimated_steps=2,
                mcp_calls=0,
                base_tokens=500,
                depends_on=["b"],
            ),
            SubtaskInput(
                id="b",
                title="Task B",
                role="coder",
                estimated_steps=2,
                mcp_calls=0,
                base_tokens=500,
                depends_on=["a"],
            ),
        ],
    )
    with pytest.raises(PlannerValidationError, match="cycle"):
        evaluate_swarm_plan(req)


def test_rejects_unknown_and_duplicate_dependencies() -> None:
    dup_req = SwarmPlanCreateRequest(
        name="Duplicate IDs",
        objective="Should reject duplicate subtask IDs.",
        topology="star",
        max_agents=4,
        subtasks=[
            SubtaskInput(
                id="dup",
                title="First task",
                role="coder",
                estimated_steps=1,
                mcp_calls=0,
                base_tokens=500,
            ),
            SubtaskInput(
                id="dup",
                title="Second task with same ID",
                role="validator",
                estimated_steps=1,
                mcp_calls=0,
                base_tokens=500,
            ),
        ],
    )
    with pytest.raises(PlannerValidationError, match="Duplicate subtask id"):
        evaluate_swarm_plan(dup_req)

    unknown_req = SwarmPlanCreateRequest(
        name="Unknown Dependency",
        objective="Should reject missing dependency reference.",
        topology="star",
        max_agents=4,
        subtasks=[
            SubtaskInput(
                id="only-task",
                title="Task referencing ghost parent",
                role="coder",
                estimated_steps=2,
                mcp_calls=0,
                base_tokens=500,
                depends_on=["ghost-task"],
            )
        ],
    )
    with pytest.raises(PlannerValidationError, match="unknown dependency"):
        evaluate_swarm_plan(unknown_req)


def test_mesh_topology_bottleneck_warning_on_large_agent_pool() -> None:
    subtasks = [
        SubtaskInput(
            id=f"node-{i}",
            title=f"Parallel worker task {i}",
            role="coder",
            estimated_steps=3,
            mcp_calls=1,
            base_tokens=1000,
            depends_on=[],
        )
        for i in range(8)
    ]
    req = SwarmPlanCreateRequest(
        name="8-Agent Mesh Contention Test",
        objective="Check quadratic peer link calculation and bottleneck warning.",
        topology="mesh",
        max_agents=8,
        subtasks=subtasks,
    )
    _, _, topo = evaluate_swarm_plan(req)
    assert topo.active_agents == 8
    assert topo.communication_edges == 28  # 8 * 7 / 2
    assert topo.bottleneck_warning is not None
    assert "Mesh topology" in topo.bottleneck_warning


def test_labeled_benchmark_suite_reproducibility_and_accuracy() -> None:
    run = run_labeled_benchmark_suite(horizon_threshold=5, mcp_call_threshold=2)
    assert run.case_count == 8
    assert run.routing_accuracy_pct == 100.0
    assert run.overall_token_reduction_pct >= 20.0
    assert run.routed_total_tokens < run.baseline_total_tokens
    assert all(c.matched_expectation for c in run.cases)
