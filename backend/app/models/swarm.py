from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field, field_validator

AgentRole = Literal[
    "coordinator",
    "architect",
    "coder",
    "analyst",
    "validator",
    "researcher",
]

SwarmTopology = Literal["hierarchical", "mesh", "ring", "star"]

RoutingMode = Literal["simulative_forward_pass", "reactive_direct"]


class SubtaskInput(BaseModel):
    id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    title: str = Field(..., min_length=2, max_length=140)
    role: AgentRole = "coder"
    estimated_steps: int = Field(..., ge=1, le=50)
    mcp_calls: int = Field(default=0, ge=0, le=30)
    base_tokens: int = Field(..., ge=64, le=65536)
    depends_on: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("Subtask title must contain at least 2 non-whitespace characters.")
        return cleaned


class SwarmPlanCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    objective: str = Field(..., min_length=5, max_length=600)
    topology: SwarmTopology = "hierarchical"
    max_agents: int = Field(default=6, ge=2, le=64)
    horizon_threshold: int = Field(default=5, ge=1, le=30)
    mcp_call_threshold: int = Field(default=2, ge=1, le=20)
    subtasks: list[SubtaskInput] = Field(..., min_length=1, max_length=40)

    @field_validator("name", "objective")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be blank.")
        return cleaned


class SubtaskScheduleNode(BaseModel):
    id: str
    title: str
    role: AgentRole
    assigned_agent_slot: str
    depth_level: int
    start_step: int
    end_step: int
    on_critical_path: bool
    estimated_steps: int
    mcp_calls: int
    flat_tokens: int
    routed_tokens: int
    depends_on: list[str]


class SimulativeRoutingDecision(BaseModel):
    mode: RoutingMode
    triggered_by: list[str]
    horizon_threshold: int
    mcp_call_threshold: int
    critical_path_steps: int
    total_steps: int
    total_mcp_calls: int
    shadow_pass_tokens: int
    flat_tier3_tokens: int
    selective_routed_tokens: int
    token_savings: int
    token_reduction_pct: float
    estimated_routing_overhead_ms: float


class TopologyMetrics(BaseModel):
    topology: SwarmTopology
    max_agents: int
    active_agents: int
    communication_edges: int
    coordination_latency_ms: float
    parallel_speedup: float
    parallel_efficiency_pct: float
    role_distribution: dict[str, int]
    bottleneck_warning: str | None = None


class SwarmPlanRecord(BaseModel):
    id: str
    name: str
    objective: str
    topology: SwarmTopology
    max_agents: int
    subtasks: list[SubtaskInput]
    schedule: list[SubtaskScheduleNode]
    routing: SimulativeRoutingDecision
    topology_metrics: TopologyMetrics
    created_at: str
    updated_at: str


class DashboardSummaryMetrics(BaseModel):
    total_plans: int
    simulative_routed_count: int
    reactive_direct_count: int
    avg_token_reduction_pct: float
    avg_parallel_efficiency_pct: float
    total_tokens_saved: int


class SwarmPlanListResponse(BaseModel):
    items: list[SwarmPlanRecord]
    total: int
    limit: int
    offset: int
    summary: DashboardSummaryMetrics


class BenchmarkRunRequest(BaseModel):
    horizon_threshold: int = Field(default=5, ge=1, le=20)
    mcp_call_threshold: int = Field(default=2, ge=1, le=15)


class BenchmarkCaseResult(BaseModel):
    case_id: str
    title: str
    category: str
    expected_mode: RoutingMode
    predicted_mode: RoutingMode
    matched_expectation: bool
    critical_path_steps: int
    total_mcp_calls: int
    baseline_flat_tokens: int
    selective_routed_tokens: int
    token_reduction_pct: float
    routing_overhead_ms: float


class BenchmarkRunRecord(BaseModel):
    id: str
    suite_name: str
    horizon_threshold: int
    mcp_call_threshold: int
    case_count: int
    routing_accuracy_pct: float
    baseline_total_tokens: int
    routed_total_tokens: int
    overall_token_reduction_pct: float
    avg_overhead_ms: float
    cases: list[BenchmarkCaseResult]
    created_at: str


class AuditLogEntry(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: str
    detail: str
    created_at: str
