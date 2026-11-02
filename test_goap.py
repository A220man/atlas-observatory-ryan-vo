#!/usr/bin/env python3
"""Test script for GOAP planner."""

from app.models.goap import GOAPAction, GOAPGoal, GOAPPlanRequest
from app.services.goap_planner import synthesize_goap_plan, validate_goap_request

# Define a simple scenario: Build and deploy an application
# Initial state: no code, no tests, not deployed
initial_state = {
    "has_code": False,
    "tests_pass": False,
    "is_deployed": False,
}

# Actions
actions = [
    GOAPAction(
        id="write_code",
        name="Write Code",
        cost=5.0,
        preconditions={},
        effects={"has_code": True},
    ),
    GOAPAction(
        id="write_tests",
        name="Write Tests",
        cost=3.0,
        preconditions={"has_code": True},
        effects={"tests_pass": True},
    ),
    GOAPAction(
        id="run_tests",
        name="Run Tests",
        cost=2.0,
        preconditions={"has_code": True, "tests_pass": True},
        effects={"tests_pass": True},
    ),
    GOAPAction(
        id="deploy",
        name="Deploy Application",
        cost=4.0,
        preconditions={"has_code": True, "tests_pass": True},
        effects={"is_deployed": True},
    ),
]

# Goals
goals = [
    GOAPGoal(
        id="deployed_app",
        name="Application Deployed",
        target_state={"is_deployed": True, "tests_pass": True},
        priority=1.0,
    ),
]

request = GOAPPlanRequest(
    initial_state=initial_state,
    actions=actions,
    goals=goals,
    max_search_depth=50,
    max_iterations=10000,
)

print("Validating request...")
warnings = validate_goap_request(request)
print("Warnings:", warnings)

print("\nSynthesizing plan...")
response = synthesize_goap_plan(request)
print("Success:", response.success)
print("Plan steps:", len(response.plan))
for i, step in enumerate(response.plan):
    print(f"  Step {i+1}: {step.action_name} (cost: {step.cost})")
print("Total cost:", response.total_cost)
print("Final state:", response.final_state)
print("Nodes expanded:", response.nodes_expanded)
print("Search time (ms):", response.search_time_ms)

if not response.success:
    print("Error:", response.error_message)

