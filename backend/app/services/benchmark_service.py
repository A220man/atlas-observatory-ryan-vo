from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from app.models.swarm import (
    BenchmarkCaseResult,
    BenchmarkRunRecord,
    RoutingMode,
    SubtaskInput,
    SwarmPlanCreateRequest,
    SwarmTopology,
)
from app.services.planner_engine import evaluate_swarm_plan


@dataclass(frozen=True)
class LabeledBenchmarkWorkload:
    case_id: str
    title: str
    category: str
    topology: SwarmTopology
    max_agents: int
    expected_mode: RoutingMode
    subtasks: list[SubtaskInput]


BENCHMARK_WORKLOADS: list[LabeledBenchmarkWorkload] = [
    LabeledBenchmarkWorkload(
        case_id="gaia-single-hop-status",
        title="Single-Hop Config & Version Check",
        category="reactive-lookup",
        topology="star",
        max_agents=2,
        expected_mode="reactive_direct",
        subtasks=[
            SubtaskInput(
                id="inspect-env",
                title="Inspect local runtime version metadata",
                role="analyst",
                estimated_steps=2,
                mcp_calls=0,
                base_tokens=600,
                depends_on=[],
            ),
            SubtaskInput(
                id="format-summary",
                title="Format status check output",
                role="coder",
                estimated_steps=1,
                mcp_calls=1,
                base_tokens=450,
                depends_on=["inspect-env"],
            ),
        ],
    ),
    LabeledBenchmarkWorkload(
        case_id="syntax-lint-autofix",
        title="Two-File Import Path Lint Repair",
        category="reactive-patch",
        topology="star",
        max_agents=3,
        expected_mode="reactive_direct",
        subtasks=[
            SubtaskInput(
                id="parse-imports",
                title="Locate broken relative TypeScript import specifiers",
                role="coder",
                estimated_steps=2,
                mcp_calls=0,
                base_tokens=800,
                depends_on=[],
            ),
            SubtaskInput(
                id="patch-imports",
                title="Apply deterministic specifier rewrite",
                role="coder",
                estimated_steps=2,
                mcp_calls=1,
                base_tokens=900,
                depends_on=["parse-imports"],
            ),
        ],
    ),
    LabeledBenchmarkWorkload(
        case_id="unit-assertion-check",
        title="Parallel Smoke Assertion Verification",
        category="reactive-test",
        topology="ring",
        max_agents=3,
        expected_mode="reactive_direct",
        subtasks=[
            SubtaskInput(
                id="check-schema",
                title="Validate JSON schema keys",
                role="validator",
                estimated_steps=2,
                mcp_calls=0,
                base_tokens=520,
                depends_on=[],
            ),
            SubtaskInput(
                id="check-types",
                title="Verify interface export symbols",
                role="validator",
                estimated_steps=2,
                mcp_calls=0,
                base_tokens=540,
                depends_on=[],
            ),
        ],
    ),
    LabeledBenchmarkWorkload(
        case_id="sr2am-multi-hop-rag",
        title="Multi-Hop Temporal Vector Memory Synthesis",
        category="simulative-rag",
        topology="hierarchical",
        max_agents=5,
        expected_mode="simulative_forward_pass",
        subtasks=[
            SubtaskInput(
                id="query-decomposition",
                title="Decompose temporal entity query into sub-claims",
                role="coordinator",
                estimated_steps=2,
                mcp_calls=1,
                base_tokens=1400,
                depends_on=[],
            ),
            SubtaskInput(
                id="hnsw-retrieval",
                title="Retrieve top-K HNSW candidate chunks across sessions",
                role="researcher",
                estimated_steps=3,
                mcp_calls=3,
                base_tokens=2200,
                depends_on=["query-decomposition"],
            ),
            SubtaskInput(
                id="staleness-filter",
                title="Filter interference-aged records and resolve entity drift",
                role="analyst",
                estimated_steps=3,
                mcp_calls=1,
                base_tokens=1900,
                depends_on=["hnsw-retrieval"],
            ),
            SubtaskInput(
                id="consolidate-answer",
                title="Verify citations and consolidate grounded response",
                role="validator",
                estimated_steps=2,
                mcp_calls=1,
                base_tokens=1500,
                depends_on=["staleness-filter"],
            ),
        ],
    ),
    LabeledBenchmarkWorkload(
        case_id="witness-cross-platform-audit",
        title="Cross-Platform Release Manifest & Witness Verification",
        category="simulative-verification",
        topology="hierarchical",
        max_agents=6,
        expected_mode="simulative_forward_pass",
        subtasks=[
            SubtaskInput(
                id="build-dist",
                title="Compile workspace dist artifacts before manifest inspection",
                role="coder",
                estimated_steps=3,
                mcp_calls=1,
                base_tokens=1600,
                depends_on=[],
            ),
            SubtaskInput(
                id="verify-linux",
                title="Verify Linux SHA-256 manifest digests and Ed25519 stamp",
                role="validator",
                estimated_steps=2,
                mcp_calls=1,
                base_tokens=1300,
                depends_on=["build-dist"],
            ),
            SubtaskInput(
                id="verify-macos",
                title="Verify macOS SHA-256 manifest digests and Ed25519 stamp",
                role="validator",
                estimated_steps=2,
                mcp_calls=1,
                base_tokens=1300,
                depends_on=["build-dist"],
            ),
            SubtaskInput(
                id="verify-windows",
                title="Verify Windows SHA-256 manifest digests and Ed25519 stamp",
                role="validator",
                estimated_steps=2,
                mcp_calls=1,
                base_tokens=1300,
                depends_on=["build-dist"],
            ),
            SubtaskInput(
                id="gate-release",
                title="Aggregate platform verdicts and reject missing-artifact soft passes",
                role="coordinator",
                estimated_steps=2,
                mcp_calls=1,
                base_tokens=1400,
                depends_on=["verify-linux", "verify-macos", "verify-windows"],
            ),
        ],
    ),
    LabeledBenchmarkWorkload(
        case_id="swarm-v3-orchestrator-split",
        title="15-Agent Orchestrator DDD Decomposition & TDD Harness",
        category="simulative-architecture",
        topology="hierarchical",
        max_agents=12,
        expected_mode="simulative_forward_pass",
        subtasks=[
            SubtaskInput(
                id="ddd-boundaries",
                title="Define bounded context interfaces for coordinator and memory",
                role="architect",
                estimated_steps=3,
                mcp_calls=1,
                base_tokens=2400,
                depends_on=[],
            ),
            SubtaskInput(
                id="extract-router",
                title="Extract selective planning router module",
                role="coder",
                estimated_steps=4,
                mcp_calls=2,
                base_tokens=3100,
                depends_on=["ddd-boundaries"],
            ),
            SubtaskInput(
                id="extract-memory",
                title="Unify SQLite and HNSW searchable embedding cache",
                role="coder",
                estimated_steps=4,
                mcp_calls=2,
                base_tokens=3200,
                depends_on=["ddd-boundaries"],
            ),
            SubtaskInput(
                id="security-hardening",
                title="Replace legacy hash routines and enforce path prefix checks",
                role="validator",
                estimated_steps=3,
                mcp_calls=1,
                base_tokens=2100,
                depends_on=["extract-router", "extract-memory"],
            ),
            SubtaskInput(
                id="integration-suite",
                title="Execute end-to-end contract and regression benchmark suite",
                role="validator",
                estimated_steps=3,
                mcp_calls=2,
                base_tokens=2300,
                depends_on=["security-hardening"],
            ),
        ],
    ),
    LabeledBenchmarkWorkload(
        case_id="rabitq-quantization-migration",
        title="RaBitQ 1-Bit Vector Quantization Rollout & Recall Audit",
        category="simulative-ml-infra",
        topology="mesh",
        max_agents=6,
        expected_mode="simulative_forward_pass",
        subtasks=[
            SubtaskInput(
                id="corpus-snapshot",
                title="Sample 10k reference float32 embeddings for baseline recall",
                role="researcher",
                estimated_steps=2,
                mcp_calls=1,
                base_tokens=1700,
                depends_on=[],
            ),
            SubtaskInput(
                id="quantize-rabitq",
                title="Encode binary RaBitQ signatures and int8 rescoring tables",
                role="coder",
                estimated_steps=4,
                mcp_calls=2,
                base_tokens=2800,
                depends_on=["corpus-snapshot"],
            ),
            SubtaskInput(
                id="contrastive-recall",
                title="Evaluate top-K cosine parity and near-duplicate recall >= 0.95",
                role="analyst",
                estimated_steps=3,
                mcp_calls=2,
                base_tokens=2200,
                depends_on=["quantize-rabitq"],
            ),
        ],
    ),
    LabeledBenchmarkWorkload(
        case_id="mcp-federation-breaker",
        title="Multi-Swarm Federation Circuit Breaker & WebSocket Smoke",
        category="simulative-distributed",
        topology="ring",
        max_agents=5,
        expected_mode="simulative_forward_pass",
        subtasks=[
            SubtaskInput(
                id="probe-transport",
                title="Measure WebSocket round-trip transport latency across peers",
                role="analyst",
                estimated_steps=2,
                mcp_calls=2,
                base_tokens=1500,
                depends_on=[],
            ),
            SubtaskInput(
                id="trip-breaker",
                title="Simulate peer timeout and verify ADR-097 circuit breaker isolation",
                role="validator",
                estimated_steps=2,
                mcp_calls=2,
                base_tokens=1800,
                depends_on=["probe-transport"],
            ),
        ],
    ),
]


def run_labeled_benchmark_suite(
    horizon_threshold: int = 5,
    mcp_call_threshold: int = 2,
    shadow_pass_tokens: int = 256,
) -> BenchmarkRunRecord:
    case_results: list[BenchmarkCaseResult] = []
    correct_count = 0
    baseline_total = 0
    routed_total = 0
    total_overhead_ms = 0.0

    for workload in BENCHMARK_WORKLOADS:
        plan_req = SwarmPlanCreateRequest(
            name=workload.title,
            objective=f"Benchmark evaluation for {workload.case_id} ({workload.category})",
            topology=workload.topology,
            max_agents=workload.max_agents,
            horizon_threshold=horizon_threshold,
            mcp_call_threshold=mcp_call_threshold,
            subtasks=workload.subtasks,
        )
        _, routing, _ = evaluate_swarm_plan(plan_req, shadow_pass_tokens=shadow_pass_tokens)
        matched = routing.mode == workload.expected_mode
        if matched:
            correct_count += 1

        baseline_total += routing.flat_tier3_tokens
        routed_total += routing.selective_routed_tokens
        total_overhead_ms += routing.estimated_routing_overhead_ms

        case_results.append(
            BenchmarkCaseResult(
                case_id=workload.case_id,
                title=workload.title,
                category=workload.category,
                expected_mode=workload.expected_mode,
                predicted_mode=routing.mode,
                matched_expectation=matched,
                critical_path_steps=routing.critical_path_steps,
                total_mcp_calls=routing.total_mcp_calls,
                baseline_flat_tokens=routing.flat_tier3_tokens,
                selective_routed_tokens=routing.selective_routed_tokens,
                token_reduction_pct=routing.token_reduction_pct,
                routing_overhead_ms=routing.estimated_routing_overhead_ms,
            )
        )

    case_count = len(case_results)
    accuracy_pct = round((correct_count / max(1, case_count)) * 100.0, 2)
    overall_reduction_pct = (
        round(((baseline_total - routed_total) / baseline_total) * 100.0, 2)
        if baseline_total > 0
        else 0.0
    )
    avg_overhead = round(total_overhead_ms / max(1, case_count), 2)

    return BenchmarkRunRecord(
        id=f"bench-{uuid.uuid4().hex[:12]}",
        suite_name="SR2AM Selective Simulative Routing Benchmark v1 (8 Labeled Workloads)",
        horizon_threshold=horizon_threshold,
        mcp_call_threshold=mcp_call_threshold,
        case_count=case_count,
        routing_accuracy_pct=accuracy_pct,
        baseline_total_tokens=baseline_total,
        routed_total_tokens=routed_total,
        overall_token_reduction_pct=overall_reduction_pct,
        avg_overhead_ms=avg_overhead,
        cases=case_results,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
