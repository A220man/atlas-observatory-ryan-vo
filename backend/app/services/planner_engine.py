from __future__ import annotations

from collections import defaultdict, deque

from app.models.swarm import (
    SimulativeRoutingDecision,
    SubtaskInput,
    SubtaskScheduleNode,
    SwarmPlanCreateRequest,
    SwarmTopology,
    TopologyMetrics,
)


class PlannerValidationError(ValueError):
    """Raised when a swarm plan contains invalid dependency structure."""


def _validate_and_toposort(subtasks: list[SubtaskInput]) -> tuple[list[SubtaskInput], dict[str, SubtaskInput]]:
    by_id: dict[str, SubtaskInput] = {}
    for task in subtasks:
        if task.id in by_id:
            raise PlannerValidationError(f"Duplicate subtask id '{task.id}'.")
        by_id[task.id] = task

    in_degree: dict[str, int] = {task.id: 0 for task in subtasks}
    dependents: dict[str, list[str]] = defaultdict(list)

    for task in subtasks:
        seen_deps: set[str] = set()
        for dep_id in task.depends_on:
            if dep_id == task.id:
                raise PlannerValidationError(f"Subtask '{task.id}' cannot depend on itself.")
            if dep_id not in by_id:
                raise PlannerValidationError(
                    f"Subtask '{task.id}' references unknown dependency '{dep_id}'."
                )
            if dep_id in seen_deps:
                continue
            seen_deps.add(dep_id)
            in_degree[task.id] += 1
            dependents[dep_id].append(task.id)

    queue: deque[str] = deque([task.id for task in subtasks if in_degree[task.id] == 0])
    ordered: list[SubtaskInput] = []

    while queue:
        current_id = queue.popleft()
        ordered.append(by_id[current_id])
        for child_id in dependents[current_id]:
            in_degree[child_id] -= 1
            if in_degree[child_id] == 0:
                queue.append(child_id)

    if len(ordered) != len(subtasks):
        raise PlannerValidationError("Subtask dependency graph contains a cycle.")

    return ordered, by_id


def _compute_flat_and_routed_tokens(
    task: SubtaskInput,
    use_simulative_pass: bool,
    depth_level: int,
) -> tuple[int, int]:
    """
    Deterministic token cost model:
    - Flat Tier-3 routing dispatches every subtask with full unpruned context,
      incurring step-horizon expansion (18% per step beyond 1) and MCP schema/retry
      overhead (240 tokens per MCP tool call).
    - Selective Simulative Routing (SR2AM) uses the forward shadow pass to prune
      redundant reasoning branches on multi-step and MCP-heavy tasks while routing
      shallow leaf subtasks (<=2 steps, 0 MCP calls) via compact reactive execution.
    """
    step_expansion = 1.0 + 0.18 * max(0, task.estimated_steps - 1) + 0.06 * depth_level
    mcp_overhead = task.mcp_calls * 240
    flat_tokens = int(round(task.base_tokens * step_expansion + mcp_overhead))

    if use_simulative_pass:
        # Guided forward plan compresses multi-step search trajectories and tool retries
        guided_multiplier = 1.0 + 0.065 * max(0, task.estimated_steps - 1) + 0.025 * depth_level
        guided_mcp_overhead = task.mcp_calls * 95
        routed_tokens = int(round(task.base_tokens * guided_multiplier + guided_mcp_overhead))
    else:
        # Reactive direct execution avoids full Tier-3 chain-of-thought inflation on simple tasks
        if task.estimated_steps <= 2 and task.mcp_calls <= 1:
            reactive_multiplier = 1.0 + 0.08 * max(0, task.estimated_steps - 1)
            routed_tokens = int(round(task.base_tokens * reactive_multiplier + task.mcp_calls * 120))
        else:
            routed_tokens = flat_tokens

    return flat_tokens, max(64, routed_tokens)


def _compute_topology_metrics(
    topology: SwarmTopology,
    max_agents: int,
    subtasks: list[SubtaskInput],
    critical_path_steps: int,
    total_steps: int,
) -> TopologyMetrics:
    role_counts: dict[str, int] = defaultdict(int)
    for task in subtasks:
        role_counts[task.role] += 1

    active_agents = min(max_agents, max(2, len(subtasks)))

    if topology == "hierarchical":
        edges = max(1, (active_agents - 1) + max(0, (active_agents - 2) // 3))
        per_edge_ms = 1.8
    elif topology == "mesh":
        edges = max(1, (active_agents * (active_agents - 1)) // 2)
        per_edge_ms = 2.4
    elif topology == "ring":
        edges = active_agents if active_agents > 2 else 1
        per_edge_ms = 2.1
    else:  # star
        edges = max(1, active_agents - 1)
        per_edge_ms = 2.6

    coordination_latency_ms = round(3.0 + edges * per_edge_ms, 2)

    ideal_parallelism = total_steps / max(1, critical_path_steps)
    capacity_factor = min(1.0, active_agents / max(1.0, ideal_parallelism))
    topology_penalty = min(0.35, (edges * 0.008))
    effective_speedup = max(1.0, round(ideal_parallelism * capacity_factor * (1.0 - topology_penalty), 2))
    efficiency_pct = round(min(100.0, (effective_speedup / max(1, active_agents)) * 100.0), 1)

    bottleneck_warning: str | None = None
    if topology == "mesh" and active_agents >= 8:
        bottleneck_warning = (
            f"Mesh topology with {active_agents} agents requires {edges} peer links; "
            "switch to hierarchical topology to reduce quadratic coordination overhead."
        )
    elif topology == "star" and len(subtasks) >= 6:
        bottleneck_warning = (
            "Star hub serializes state updates across subtasks; consider hierarchical clusters."
        )
    elif critical_path_steps == total_steps and len(subtasks) > 1:
        bottleneck_warning = (
            "Subtasks form a purely sequential chain (speedup 1.0x); decouple independent steps."
        )

    return TopologyMetrics(
        topology=topology,
        max_agents=max_agents,
        active_agents=active_agents,
        communication_edges=edges,
        coordination_latency_ms=coordination_latency_ms,
        parallel_speedup=effective_speedup,
        parallel_efficiency_pct=efficiency_pct,
        role_distribution=dict(sorted(role_counts.items())),
        bottleneck_warning=bottleneck_warning,
    )


def evaluate_swarm_plan(
    request: SwarmPlanCreateRequest,
    shadow_pass_tokens: int = 256,
) -> tuple[list[SubtaskScheduleNode], SimulativeRoutingDecision, TopologyMetrics]:
    ordered_tasks, by_id = _validate_and_toposort(request.subtasks)

    earliest_start: dict[str, int] = {}
    earliest_end: dict[str, int] = {}
    depth_map: dict[str, int] = {}

    for task in ordered_tasks:
        if not task.depends_on:
            earliest_start[task.id] = 0
            depth_map[task.id] = 0
        else:
            earliest_start[task.id] = max(earliest_end[dep_id] for dep_id in task.depends_on)
            depth_map[task.id] = 1 + max(depth_map[dep_id] for dep_id in task.depends_on)
        earliest_end[task.id] = earliest_start[task.id] + task.estimated_steps

    critical_path_steps = max(earliest_end.values()) if earliest_end else 0
    total_steps = sum(t.estimated_steps for t in ordered_tasks)
    total_mcp_calls = sum(t.mcp_calls for t in ordered_tasks)

    # Backward pass to mark critical path nodes
    latest_end: dict[str, int] = {t.id: critical_path_steps for t in ordered_tasks}
    latest_start: dict[str, int] = {}
    for task in reversed(ordered_tasks):
        children = [
            candidate.id
            for candidate in ordered_tasks
            if task.id in candidate.depends_on
        ]
        if children:
            latest_end[task.id] = min(latest_start[c_id] for c_id in children)
        latest_start[task.id] = latest_end[task.id] - task.estimated_steps

    triggered_by: list[str] = []
    if critical_path_steps > request.horizon_threshold:
        triggered_by.append(
            f"critical_path_horizon ({critical_path_steps} > {request.horizon_threshold} steps)"
        )
    if total_mcp_calls >= request.mcp_call_threshold:
        triggered_by.append(
            f"mcp_call_density ({total_mcp_calls} >= {request.mcp_call_threshold} calls)"
        )

    use_simulative = len(triggered_by) > 0
    routing_mode = "simulative_forward_pass" if use_simulative else "reactive_direct"

    role_counters: dict[str, int] = defaultdict(int)
    schedule_nodes: list[SubtaskScheduleNode] = []
    flat_total = 0
    subtask_routed_total = 0

    for task in ordered_tasks:
        slot_idx = (role_counters[task.role] % request.max_agents) + 1
        role_counters[task.role] += 1
        depth = depth_map[task.id]
        flat_t, routed_t = _compute_flat_and_routed_tokens(task, use_simulative, depth)
        flat_total += flat_t
        subtask_routed_total += routed_t
        is_critical = earliest_start[task.id] == latest_start[task.id]

        schedule_nodes.append(
            SubtaskScheduleNode(
                id=task.id,
                title=task.title,
                role=task.role,
                assigned_agent_slot=f"{task.role}-{slot_idx}",
                depth_level=depth,
                start_step=earliest_start[task.id],
                end_step=earliest_end[task.id],
                on_critical_path=is_critical,
                estimated_steps=task.estimated_steps,
                mcp_calls=task.mcp_calls,
                flat_tokens=flat_t,
                routed_tokens=routed_t,
                depends_on=list(dict.fromkeys(task.depends_on)),
            )
        )

    applied_shadow_tokens = shadow_pass_tokens if use_simulative else 0
    selective_total = subtask_routed_total + applied_shadow_tokens
    token_savings = max(0, flat_total - selective_total)
    reduction_pct = (
        round((token_savings / flat_total) * 100.0, 2) if flat_total > 0 else 0.0
    )

    # Overhead: shadow pass takes ~14.5ms + 1.6ms per critical step; reactive dispatch is ~1.8ms
    overhead_ms = (
        round(14.5 + 1.6 * critical_path_steps + 0.9 * total_mcp_calls, 2)
        if use_simulative
        else round(1.8 + 0.3 * len(ordered_tasks), 2)
    )

    routing_decision = SimulativeRoutingDecision(
        mode=routing_mode,
        triggered_by=triggered_by,
        horizon_threshold=request.horizon_threshold,
        mcp_call_threshold=request.mcp_call_threshold,
        critical_path_steps=critical_path_steps,
        total_steps=total_steps,
        total_mcp_calls=total_mcp_calls,
        shadow_pass_tokens=applied_shadow_tokens,
        flat_tier3_tokens=flat_total,
        selective_routed_tokens=selective_total,
        token_savings=token_savings,
        token_reduction_pct=reduction_pct,
        estimated_routing_overhead_ms=overhead_ms,
    )

    topology_metrics = _compute_topology_metrics(
        topology=request.topology,
        max_agents=request.max_agents,
        subtasks=ordered_tasks,
        critical_path_steps=critical_path_steps,
        total_steps=total_steps,
    )

    return schedule_nodes, routing_decision, topology_metrics
