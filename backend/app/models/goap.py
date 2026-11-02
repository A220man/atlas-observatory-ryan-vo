from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class WorldStateKey(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    value: bool | int | float | str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v in ("true", "false", "none"):
            raise ValueError(f"Reserved keyword '{v}' cannot be used as state name")
        return v


class WorldState(BaseModel):
    state: dict[str, bool | int | float | str] = Field(default_factory=dict)

    def get(self, key: str, default=None):
        return self.state.get(key, default)

    def set(self, key: str, value: bool | int | float | str) -> "WorldState":
        new_state = self.state.copy()
        new_state[key] = value
        return WorldState(state=new_state)

    def satisfies(self, conditions: dict[str, bool | int | float | str]) -> bool:
        for key, expected in conditions.items():
            actual = self.state.get(key)
            if actual != expected:
                return False
        return True

    def apply_effects(self, effects: dict[str, bool | int | float | str]) -> "WorldState":
        new_state = self.state.copy()
        new_state.update(effects)
        return WorldState(state=new_state)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorldState):
            return NotImplemented
        return self.state == other.state

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.state.items())))


class GOAPAction(BaseModel):
    id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=120)
    cost: float = Field(default=1.0, ge=0.01, le=1000.0)
    preconditions: dict[str, bool | int | float | str] = Field(default_factory=dict)
    effects: dict[str, bool | int | float | str] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if v in ("start", "goal"):
            raise ValueError(f"Reserved action ID '{v}'")
        return v

    def is_applicable(self, state: WorldState) -> bool:
        return state.satisfies(self.preconditions)

    def apply(self, state: WorldState) -> WorldState:
        return state.apply_effects(self.effects)


class GOAPGoal(BaseModel):
    id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=120)
    target_state: dict[str, bool | int | float | str] = Field(default_factory=dict)
    priority: float = Field(default=1.0, ge=0.01, le=100.0)


class GOAPPlanCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    initial_state: dict[str, bool | int | float | str] = Field(default_factory=dict)
    actions: list[GOAPAction] = Field(..., min_length=1)
    goals: list[GOAPGoal] = Field(..., min_length=1)
    max_search_depth: int = Field(default=50, ge=1, le=200)
    max_iterations: int = Field(default=10000, ge=1, le=100000)


class GOAPPlanRequest(BaseModel):
    initial_state: dict[str, bool | int | float | str] = Field(default_factory=dict)
    actions: list[GOAPAction] = Field(..., min_length=1)
    goals: list[GOAPGoal] = Field(..., min_length=1)
    max_search_depth: int = Field(default=50, ge=1, le=200)
    max_iterations: int = Field(default=10000, ge=1, le=100000)


class GOAPPlanStep(BaseModel):
    action_id: str
    action_name: str
    cost: float
    resulting_state: dict[str, bool | int | float | str]


class GOAPPlanResponse(BaseModel):
    success: bool
    plan: list[GOAPPlanStep] = Field(default_factory=list)
    total_cost: float = 0.0
    final_state: dict[str, bool | int | float | str] = Field(default_factory=dict)
    nodes_expanded: int = 0
    search_time_ms: float = 0.0
    error_message: str | None = None


class GOAPPlanRecord(BaseModel):
    id: str
    name: str
    initial_state: dict[str, bool | int | float | str]
    actions: list[GOAPAction]
    goals: list[GOAPGoal]
    plan: list[GOAPPlanStep]
    total_cost: float
    final_state: dict[str, bool | int | float | str]
    nodes_expanded: int
    search_time_ms: float
    success: bool
    error_message: str | None
    created_at: str
    updated_at: str


class GOAPPlanListResponse(BaseModel):
    items: list[GOAPPlanRecord]
    total: int


class GOAPPlanDetailResponse(BaseModel):
    record: GOAPPlanRecord
    state_transitions: list[dict[str, object]]

