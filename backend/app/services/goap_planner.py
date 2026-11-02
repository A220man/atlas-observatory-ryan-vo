from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from typing import Any

from app.models.goap import (
    GOAPAction,
    GOAPGoal,
    GOAPPlanRequest,
    GOAPPlanResponse,
    GOAPPlanStep,
    WorldState,
)


@dataclass(order=True)
class SearchNode:
    """A node in the A* search space."""
    f_score: float
    g_score: float = field(compare=False)
    state: WorldState = field(compare=False)
    action_id: str | None = field(compare=False, default=None)
    parent: "SearchNode | None" = field(compare=False, default=None)
    depth: int = field(compare=False, default=0)


def _heuristic(state: WorldState, goal: GOAPGoal) -> float:
    """
    Admissible heuristic: count unsatisfied goal conditions.
    Each unsatisfied condition costs at least 1 (minimum action cost).
    """
    unsatisfied = 0
    for key, expected in goal.target_state.items():
        if state.get(key) != expected:
            unsatisfied += 1
    return float(unsatisfied)


def _is_goal_state(state: WorldState, goals: list[GOAPGoal]) -> bool:
    """Check if state satisfies all goals (weighted by priority)."""
    for goal in goals:
        if not state.satisfies(goal.target_state):
            return False
    return True


def _get_applicable_actions(state: WorldState, actions: list[GOAPAction]) -> list[GOAPAction]:
    """Get all actions that can be applied in the current state."""
    return [action for action in actions if action.is_applicable(state)]


def _reconstruct_plan(node: SearchNode) -> list[GOAPPlanStep]:
    """Reconstruct the plan from the goal node back to start."""
    steps: list[GOAPPlanStep] = []
    current = node
    while current.parent is not None:
        if current.action_id is not None:
            # Find the action to get its name
            # This would need access to actions list; for now use action_id as name
            steps.append(
                GOAPPlanStep(
                    action_id=current.action_id,
                    action_name=current.action_id,  # Will be replaced with actual name
                    cost=current.g_score - (current.parent.g_score if current.parent else 0),
                    resulting_state=current.state.state,
                )
            )
        current = current.parent
    steps.reverse()
    return steps


def _reconstruct_plan_with_actions(node: SearchNode, actions: list[GOAPAction]) -> list[GOAPPlanStep]:
    """Reconstruct the plan with action names."""
    action_map = {a.id: a for a in actions}
    steps: list[GOAPPlanStep] = []
    current = node
    while current.parent is not None:
        if current.action_id is not None:
            action = action_map.get(current.action_id)
            step_cost = current.g_score - (current.parent.g_score if current.parent else 0)
            steps.append(
                GOAPPlanStep(
                    action_id=current.action_id,
                    action_name=action.name if action else current.action_id,
                    cost=step_cost,
                    resulting_state=current.state.state,
                )
            )
        current = current.parent
    steps.reverse()
    return steps


def synthesize_goap_plan(request: GOAPPlanRequest) -> GOAPPlanResponse:
    """
    Synthesize a minimum-cost action sequence using A* search.

    Returns a GOAPPlanResponse with the plan, total cost, and search statistics.
    """
    start_time = time.perf_counter()

    initial_state = WorldState(state=request.initial_state)
    goals = request.goals

    # Check if initial state already satisfies all goals
    if _is_goal_state(initial_state, goals):
        return GOAPPlanResponse(
            success=True,
            plan=[],
            total_cost=0.0,
            final_state=initial_state.state,
            nodes_expanded=0,
            search_time_ms=0.0,
        )

    # Priority queue for A* (min-heap by f_score)
    open_set: list[SearchNode] = []
    # Track visited states with best g_score
    closed_set: dict[WorldState, float] = {}

    start_node = SearchNode(
        f_score=_heuristic(initial_state, goals[0]),  # Use primary goal for heuristic
        g_score=0.0,
        state=initial_state,
        action_id=None,
        parent=None,
        depth=0,
    )
    heapq.heappush(open_set, start_node)
    closed_set[initial_state] = 0.0

    nodes_expanded = 0
    goal_node: SearchNode | None = None

    while open_set and nodes_expanded < request.max_iterations:
        current = heapq.heappop(open_set)
        nodes_expanded += 1

        # Check depth limit
        if current.depth >= request.max_search_depth:
            continue

        # Check if we reached a goal state
        if _is_goal_state(current.state, goals):
            goal_node = current
            break

        # Expand applicable actions
        applicable = _get_applicable_actions(current.state, request.actions)
        for action in applicable:
            new_state = action.apply(current.state)
            new_g_score = current.g_score + action.cost

            # Check if we've seen this state with a better or equal g_score
            if new_state in closed_set and closed_set[new_state] <= new_g_score:
                continue

            # Compute heuristic (use first goal as primary, could be improved with weighted goals)
            h_score = _heuristic(new_state, goals[0])
            f_score = new_g_score + h_score

            new_node = SearchNode(
                f_score=f_score,
                g_score=new_g_score,
                state=new_state,
                action_id=action.id,
                parent=current,
                depth=current.depth + 1,
            )

            heapq.heappush(open_set, new_node)
            closed_set[new_state] = new_g_score

    search_time_ms = (time.perf_counter() - start_time) * 1000

    if goal_node is None:
        return GOAPPlanResponse(
            success=False,
            plan=[],
            total_cost=0.0,
            final_state=initial_state.state,
            nodes_expanded=nodes_expanded,
            search_time_ms=search_time_ms,
            error_message="No valid plan found within search limits",
        )

    # Reconstruct plan with action names
    plan = _reconstruct_plan_with_actions(goal_node, request.actions)
    total_cost = goal_node.g_score
    final_state = goal_node.state.state

    return GOAPPlanResponse(
        success=True,
        plan=plan,
        total_cost=total_cost,
        final_state=final_state,
        nodes_expanded=nodes_expanded,
        search_time_ms=search_time_ms,
    )


def validate_goap_request(request: GOAPPlanRequest) -> list[str]:
    """
    Validate a GOAP request for common issues.
    Returns a list of warnings (empty if no issues).
    """
    warnings: list[str] = []

    # Check for duplicate action IDs
    action_ids = [a.id for a in request.actions]
    if len(action_ids) != len(set(action_ids)):
        warnings.append("Duplicate action IDs detected")

    # Check for duplicate goal IDs
    goal_ids = [g.id for g in request.goals]
    if len(goal_ids) != len(set(goal_ids)):
        warnings.append("Duplicate goal IDs detected")

    # Check if any goal has empty target state
    for goal in request.goals:
        if not goal.target_state:
            warnings.append(f"Goal '{goal.id}' has empty target state")

    # Check if actions have empty preconditions and effects (no-op actions)
    for action in request.actions:
        if not action.preconditions and not action.effects:
            warnings.append(f"Action '{action.id}' has no preconditions and no effects (no-op)")

    # Check if all goal conditions are potentially achievable
    all_effects: set[str] = set()
    for action in request.actions:
        all_effects.update(action.effects.keys())

    for goal in request.goals:
        for key in goal.target_state:
            if key not in all_effects and key not in request.initial_state:
                warnings.append(f"Goal condition '{key}' is not produced by any action and not in initial state")

    # Check for unreachable preconditions (preconditions not in initial state and not produced by any action)
    all_precond_keys: set[str] = set()
    for action in request.actions:
        all_precond_keys.update(action.preconditions.keys())

    for action in request.actions:
        for precond_key in action.preconditions:
            if precond_key not in request.initial_state and precond_key not in all_effects:
                warnings.append(f"Precondition '{precond_key}' for action '{action.id}' is not in initial state and not produced by any action")

    # Warn about actions that produce effects not needed by any goal or other action
    for action in request.actions:
        produces_needed = any(eff_key in all_precond_keys for eff_key in action.effects)
        produces_for_goal = any(eff_key in goal.target_state for goal in request.goals for eff_key in action.effects)
        if not produces_needed and not produces_for_goal and action.effects:
            warnings.append(f"Action '{action.id}' produces effects that are not needed by any other action or goal")

    return warnings

