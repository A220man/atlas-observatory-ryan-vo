from __future__ import annotations

from app.models.goap import GOAPAction, GOAPGoal, GOAPPlanRequest, WorldState
from app.services.goap_planner import (
    _heuristic,
    _is_goal_state,
    _get_applicable_actions,
    _reconstruct_plan_with_actions,
    synthesize_goap_plan,
    validate_goap_request,
    SearchNode,
)


def test_heuristic_counts_unsatisfied_conditions() -> None:
    state = WorldState(state={"has_key": False, "door_open": False, "in_room": True})
    goal = GOAPGoal(id="open_door", target_state={"has_key": True, "door_open": True})
    h = _heuristic(state, goal)
    assert h == 2.0


def test_heuristic_zero_when_goal_satisfied() -> None:
    state = WorldState(state={"has_key": True, "door_open": True})
    goal = GOAPGoal(id="open_door", target_state={"has_key": True, "door_open": True})
    h = _heuristic(state, goal)
    assert h == 0.0


def test_is_goal_state_checks_all_goals() -> None:
    state = WorldState(state={"has_key": True, "door_open": True, "in_room": True})
    goals = [
        GOAPGoal(id="open_door", target_state={"door_open": True}),
        GOAPGoal(id="have_key", target_state={"has_key": True}),
    ]
    assert _is_goal_state(state, goals) is True


def test_is_goal_state_fails_on_missing_condition() -> None:
    state = WorldState(state={"has_key": True, "door_open": False})
    goals = [
        GOAPGoal(id="open_door", target_state={"door_open": True}),
    ]
    assert _is_goal_state(state, goals) is False


def test_get_applicable_actions_filters_by_preconditions() -> None:
    actions = [
        GOAPAction(
            id="pickup_key",
            name="Pick up key",
            cost=1.0,
            preconditions={"in_room": True},
            effects={"has_key": True},
        ),
        GOAPAction(
            id="open_door",
            name="Open door",
            cost=1.0,
            preconditions={"has_key": True},
            effects={"door_open": True},
        ),
    ]
    state = WorldState(state={"in_room": True, "has_key": False})
    applicable = _get_applicable_actions(state, actions)
    assert len(applicable) == 1
    assert applicable[0].id == "pickup_key"


def test_get_applicable_actions_empty_when_none_match() -> None:
    actions = [
        GOAPAction(
            id="open_door",
            name="Open door",
            cost=1.0,
            preconditions={"has_key": True},
            effects={"door_open": True},
        ),
    ]
    state = WorldState(state={"has_key": False})
    applicable = _get_applicable_actions(state, actions)
    assert len(applicable) == 0


def test_synthesize_goap_plan_simple_sequence() -> None:
    request = GOAPPlanRequest(
        initial_state={"in_room": True, "has_key": False, "door_open": False},
        actions=[
            GOAPAction(
                id="pickup_key",
                name="Pick up key",
                cost=1.0,
                preconditions={"in_room": True},
                effects={"has_key": True},
            ),
            GOAPAction(
                id="open_door",
                name="Open door",
                cost=1.0,
                preconditions={"has_key": True},
                effects={"door_open": True},
            ),
        ],
        goals=[GOAPGoal(id="exit_room", target_state={"door_open": True})],
        max_search_depth=10,
        max_iterations=1000,
    )
    response = synthesize_goap_plan(request)
    assert response.success is True
    assert len(response.plan) == 2
    assert response.plan[0].action_id == "pickup_key"
    assert response.plan[1].action_id == "open_door"
    assert response.total_cost == 2.0
    assert response.final_state.get("door_open") is True


def test_synthesize_goap_plan_already_at_goal() -> None:
    request = GOAPPlanRequest(
        initial_state={"door_open": True},
        actions=[],
        goals=[GOAPGoal(id="exit_room", target_state={"door_open": True})],
        max_search_depth=10,
        max_iterations=1000,
    )
    response = synthesize_goap_plan(request)
    assert response.success is True
    assert len(response.plan) == 0
    assert response.total_cost == 0.0


def test_synthesize_goap_plan_no_valid_plan() -> None:
    request = GOAPPlanRequest(
        initial_state={"has_key": False},
        actions=[
            GOAPAction(
                id="open_door",
                name="Open door",
                cost=1.0,
                preconditions={"has_key": True},
                effects={"door_open": True},
            ),
        ],
        goals=[GOAPGoal(id="exit_room", target_state={"door_open": True})],
        max_search_depth=10,
        max_iterations=1000,
    )
    response = synthesize_goap_plan(request)
    assert response.success is False
    assert response.error_message is not None
    assert "No valid plan found" in response.error_message


def test_synthesize_goap_plan_respects_max_depth() -> None:
    request = GOAPPlanRequest(
        initial_state={"step": 0},
        actions=[
            GOAPAction(
                id="increment",
                name="Increment",
                cost=1.0,
                preconditions={},
                effects={"step": 1},
            ),
        ],
        goals=[GOAPGoal(id="reach_10", target_state={"step": 10})],
        max_search_depth=5,
        max_iterations=1000,
    )
    response = synthesize_goap_plan(request)
    assert response.success is False


def test_synthesize_goap_plan_multiple_goals() -> None:
    request = GOAPPlanRequest(
        initial_state={"has_key": False, "has_map": False},
        actions=[
            GOAPAction(
                id="pickup_key",
                name="Pick up key",
                cost=1.0,
                preconditions={},
                effects={"has_key": True},
            ),
            GOAPAction(
                id="pickup_map",
                name="Pick up map",
                cost=1.0,
                preconditions={},
                effects={"has_map": True},
            ),
        ],
        goals=[
            GOAPGoal(id="have_key", target_state={"has_key": True}),
            GOAPGoal(id="have_map", target_state={"has_map": True}),
        ],
        max_search_depth=10,
        max_iterations=1000,
    )
    response = synthesize_goap_plan(request)
    assert response.success is True
    assert len(response.plan) == 2
    assert response.final_state.get("has_key") is True
    assert response.final_state.get("has_map") is True


def test_synthesize_goap_plan_prefers_lower_cost() -> None:
    request = GOAPPlanRequest(
        initial_state={"at_start": True},
        actions=[
            GOAPAction(
                id="fast_path",
                name="Fast path",
                cost=1.0,
                preconditions={"at_start": True},
                effects={"at_goal": True, "at_start": False},
            ),
            GOAPAction(
                id="slow_path",
                name="Slow path",
                cost=10.0,
                preconditions={"at_start": True},
                effects={"at_goal": True, "at_start": False},
            ),
        ],
        goals=[GOAPGoal(id="reach_goal", target_state={"at_goal": True})],
        max_search_depth=10,
        max_iterations=1000,
    )
    response = synthesize_goap_plan(request)
    assert response.success is True
    assert response.total_cost == 1.0
    assert response.plan[0].action_id == "fast_path"


def test_validate_goap_request_empty_actions_warning() -> None:
    request = GOAPPlanRequest(
        initial_state={},
        actions=[],
        goals=[GOAPGoal(id="test", target_state={"done": True})],
    )
    warnings = validate_goap_request(request)
    assert any("No actions provided" in w for w in warnings)


def test_validate_goap_request_no_goals_warning() -> None:
    request = GOAPPlanRequest(
        initial_state={},
        actions=[GOAPAction(id="a1", name="Action 1", cost=1.0, preconditions={}, effects={})],
        goals=[],
    )
    warnings = validate_goap_request(request)
    assert any("No goals provided" in w for w in warnings)


def test_validate_goap_request_unreachable_goal_warning() -> None:
    request = GOAPPlanRequest(
        initial_state={},
        actions=[GOAPAction(id="a1", name="Action 1", cost=1.0, preconditions={}, effects={"x": True})],
        goals=[GOAPGoal(id="test", target_state={"y": True})],
    )
    warnings = validate_goap_request(request)
    assert any("No action produces effect" in w for w in warnings)


def test_reconstruct_plan_with_actions() -> None:
    state0 = WorldState(state={"start": True})
    state1 = WorldState(state={"start": True, "mid": True})
    state2 = WorldState(state={"start": True, "mid": True, "end": True})

    actions = [
        GOAPAction(id="a1", name="Action 1", cost=1.0, preconditions={}, effects={"mid": True}),
        GOAPAction(id="a2", name="Action 2", cost=2.0, preconditions={"mid": True}, effects={"end": True}),
    ]

    node0 = SearchNode(f_score=0.0, g_score=0.0, state=state0, action_id=None, parent=None, depth=0)
    node1 = SearchNode(f_score=3.0, g_score=1.0, state=state1, action_id="a1", parent=node0, depth=1)
    node2 = SearchNode(f_score=5.0, g_score=3.0, state=state2, action_id="a2", parent=node1, depth=2)

    plan = _reconstruct_plan_with_actions(node2, actions)
    assert len(plan) == 2
    assert plan[0].action_id == "a1"
    assert plan[0].action_name == "Action 1"
    assert plan[0].cost == 1.0
    assert plan[1].action_id == "a2"
    assert plan[1].action_name == "Action 2"
    assert plan[1].cost == 2.0


def test_search_node_ordering() -> None:
    state = WorldState(state={})
    node1 = SearchNode(f_score=5.0, g_score=3.0, state=state, action_id="a1", parent=None, depth=1)
    node2 = SearchNode(f_score=3.0, g_score=2.0, state=state, action_id="a2", parent=None, depth=1)
    node3 = SearchNode(f_score=3.0, g_score=1.0, state=state, action_id="a3", parent=None, depth=1)

    nodes = [node1, node2, node3]
    nodes.sort()
    assert nodes[0].f_score == 3.0
    assert nodes[0].g_score == 1.0
    assert nodes[0].action_id == "a3"
    assert nodes[1].action_id == "a2"
    assert nodes[2].action_id == "a1"


def test_world_state_equality_and_hash() -> None:
    s1 = WorldState(state={"a": 1, "b": "test"})
    s2 = WorldState(state={"b": "test", "a": 1})
    s3 = WorldState(state={"a": 1, "b": "other"})

    assert s1 == s2
    assert s1 != s3
    assert hash(s1) == hash(s2)
    assert hash(s1) != hash(s3)


def test_world_state_apply_effects() -> None:
    state = WorldState(state={"x": 1, "y": False})
    new_state = state.apply_effects({"x": 2, "y": True, "z": "new"})
    assert new_state.state["x"] == 2
    assert new_state.state["y"] is True
    assert new_state.state["z"] == "new"
    assert state.state["x"] == 1  # original unchanged


def test_world_state_satisfies() -> None:
    state = WorldState(state={"a": True, "b": 5, "c": "hello"})
    assert state.satisfies({"a": True}) is True
    assert state.satisfies({"b": 5}) is True
    assert state.satisfies({"c": "hello"}) is True
    assert state.satisfies({"a": False}) is False
    assert state.satisfies({"b": 4}) is False
    assert state.satisfies({"d": True}) is False


def test_goap_action_is_applicable() -> None:
    action = GOAPAction(
        id="test",
        name="Test Action",
        cost=1.0,
        preconditions={"a": True, "b": 5},
        effects={"c": True},
    )
    state1 = WorldState(state={"a": True, "b": 5, "other": "value"})
    state2 = WorldState(state={"a": True, "b": 4})
    state3 = WorldState(state={"a": False, "b": 5})

    assert action.is_applicable(state1) is True
    assert action.is_applicable(state2) is False
    assert action.is_applicable(state3) is False


def test_goap_action_apply() -> None:
    action = GOAPAction(
        id="test",
        name="Test Action",
        cost=1.0,
        preconditions={"a": True},
        effects={"a": False, "b": True},
    )
    state = WorldState(state={"a": True, "c": "keep"})
    new_state = action.apply(state)
    assert new_state.state["a"] is False
    assert new_state.state["b"] is True
    assert new_state.state["c"] == "keep"


