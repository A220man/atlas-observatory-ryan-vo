export type AgentRole =
  | "coordinator"
  | "architect"
  | "coder"
  | "analyst"
  | "validator"
  | "researcher";

export type SwarmTopology = "hierarchical" | "mesh" | "ring" | "star";

export type RoutingMode = "simulative_forward_pass" | "reactive_direct";

export interface SubtaskInput {
  id: string;
  title: string;
  role: AgentRole;
  estimated_steps: number;
  mcp_calls: number;
  base_tokens: number;
  depends_on: string[];
}

export interface SwarmPlanCreateRequest {
  name: string;
  objective: string;
  topology: SwarmTopology;
  max_agents: number;
  horizon_threshold: number;
  mcp_call_threshold: number;
  subtasks: SubtaskInput[];
}

export interface SubtaskScheduleNode extends SubtaskInput {
  assigned_agent_slot: string;
  depth_level: number;
  start_step: number;
  end_step: number;
  on_critical_path: boolean;
  flat_tokens: number;
  routed_tokens: number;
}

export interface SimulativeRoutingDecision {
  mode: RoutingMode;
  triggered_by: string[];
  horizon_threshold: number;
  mcp_call_threshold: number;
  critical_path_steps: number;
  total_steps: number;
  total_mcp_calls: number;
  shadow_pass_tokens: number;
  flat_tier3_tokens: number;
  selective_routed_tokens: number;
  token_savings: number;
  token_reduction_pct: number;
  estimated_routing_overhead_ms: number;
}

export interface TopologyMetrics {
  topology: SwarmTopology;
  max_agents: number;
  active_agents: number;
  communication_edges: number;
  coordination_latency_ms: number;
  parallel_speedup: number;
  parallel_efficiency_pct: number;
  role_distribution: Record<string, number>;
  bottleneck_warning: string | null;
}

export interface SwarmPlanRecord {
  id: string;
  name: string;
  objective: string;
  topology: SwarmTopology;
  max_agents: number;
  subtasks: SubtaskInput[];
  schedule: SubtaskScheduleNode[];
  routing: SimulativeRoutingDecision;
  topology_metrics: TopologyMetrics;
  created_at: string;
  updated_at: string;
}

export interface DashboardSummaryMetrics {
  total_plans: number;
  simulative_routed_count: number;
  reactive_direct_count: number;
  avg_token_reduction_pct: number;
  avg_parallel_efficiency_pct: number;
  total_tokens_saved: number;
}

export interface SwarmPlanListResponse {
  items: SwarmPlanRecord[];
  total: number;
  limit: number;
  offset: number;
  summary: DashboardSummaryMetrics;
}

export interface BenchmarkCaseResult {
  case_id: string;
  title: string;
  category: string;
  expected_mode: RoutingMode;
  predicted_mode: RoutingMode;
  matched_expectation: boolean;
  critical_path_steps: number;
  total_mcp_calls: number;
  baseline_flat_tokens: number;
  selective_routed_tokens: number;
  token_reduction_pct: number;
  routing_overhead_ms: number;
}

export interface BenchmarkRunRecord {
  id: string;
  suite_name: string;
  horizon_threshold: number;
  mcp_call_threshold: number;
  case_count: number;
  routing_accuracy_pct: number;
  baseline_total_tokens: number;
  routed_total_tokens: number;
  overall_token_reduction_pct: number;
  avg_overhead_ms: number;
  cases: BenchmarkCaseResult[];
  created_at: string;
}

export type VerificationState = "verified_clean" | "drift_detected" | "unverifiable_missing_build";

export interface ArtifactVerificationResult {
  artifact_path: string;
  expected_sha256: string;
  actual_sha256: string | null;
  exists: boolean;
  match: boolean | null;
}

export interface PlatformVerificationResult {
  platform: "macos" | "linux" | "windows";
  state: VerificationState;
  entries_total: number;
  entries_verified: number;
  entries_missing: number;
  entries_mismatch: number;
  results: ArtifactVerificationResult[];
  witness_stamp_valid: boolean | null;
  witness_stamp_detail: string | null;
}

export interface WitnessVerificationRequest {
  manifest_dir: string;
  require_dist_artifacts: boolean;
}

export interface WitnessVerificationResponse {
  overall_state: VerificationState;
  platforms: PlatformVerificationResult[];
  summary: string;
}

export interface WitnessStampVerificationRequest {
  manifest_path: string;
  session_commit: string;
}

export interface WitnessStampVerificationResponse {
  manifest_path: string;
  witness_stamp: string;
  computed_stamp: string;
  valid: boolean;
  session_commit: string;
  detail: string;
}

export interface VerificationStatesResponse {
  states: VerificationState[];
}

export interface SwarmPlanFilterParams {
  topology?: string;
  routing_mode?: string;
  search?: string;
}

export class ApiClient {
  private readonly baseUrl: string;

  constructor(baseUrl = "") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
    });
    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      try {
        const errBody = (await response.json()) as { detail?: unknown };
        if (typeof errBody.detail === "string") {
          detail = errBody.detail;
        } else if (errBody.detail) {
          detail = JSON.stringify(errBody.detail);
        }
      } catch {
        // Keep status fallback
      }
      throw new Error(detail);
    }
    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }

  async listSwarmPlans(params: SwarmPlanFilterParams = {}): Promise<SwarmPlanListResponse> {
    const query = new URLSearchParams();
    if (params.topology) query.set("topology", params.topology);
    if (params.routing_mode) query.set("routing_mode", params.routing_mode);
    if (params.search) query.set("search", params.search);
    const qs = query.toString();
    return this.request<SwarmPlanListResponse>(`/api/v1/swarms/plans${qs ? `?${qs}` : ""}`);
  }

  async createSwarmPlan(payload: SwarmPlanCreateRequest): Promise<SwarmPlanRecord> {
    return this.request<SwarmPlanRecord>("/api/v1/swarms/plans", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async getSwarmPlan(planId: string): Promise<SwarmPlanRecord> {
    return this.request<SwarmPlanRecord>(`/api/v1/swarms/plans/${encodeURIComponent(planId)}`);
  }

  async exportSwarmPlan(planId: string): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>(
      `/api/v1/swarms/plans/${encodeURIComponent(planId)}/export`
    );
  }

  async deleteSwarmPlan(planId: string): Promise<void> {
    await this.request<void>(`/api/v1/swarms/plans/${encodeURIComponent(planId)}`, {
      method: "DELETE",
    });
  }

  async getLatestBenchmark(): Promise<BenchmarkRunRecord> {
    return this.request<BenchmarkRunRecord>("/api/v1/benchmarks/latest");
  }

  async runBenchmark(
    horizonThreshold = 5,
    mcpCallThreshold = 2
  ): Promise<BenchmarkRunRecord> {
    return this.request<BenchmarkRunRecord>("/api/v1/benchmarks/run", {
      method: "POST",
      body: JSON.stringify({
        horizon_threshold: horizonThreshold,
        mcp_call_threshold: mcpCallThreshold,
      }),
    });
  }

  async verifyWitnessManifests(
    manifestDir = "verification",
    requireDistArtifacts = true
  ): Promise<WitnessVerificationResponse> {
    return this.request<WitnessVerificationResponse>("/api/v1/witness/verify", {
      method: "POST",
      body: JSON.stringify({
        manifest_dir: manifestDir,
        require_dist_artifacts: requireDistArtifacts,
      }),
    });
  }

  async verifyWitnessStamp(
    manifestPath: string,
    sessionCommit: string
  ): Promise<WitnessStampVerificationResponse> {
    return this.request<WitnessStampVerificationResponse>("/api/v1/witness/verify-stamp", {
      method: "POST",
      body: JSON.stringify({
        manifest_path: manifestPath,
        session_commit: sessionCommit,
      }),
    });
  }

  async getVerificationStates(): Promise<VerificationStatesResponse> {
    return this.request<VerificationStatesResponse>("/api/v1/witness/states");
  }
}

export const defaultApiClient = new ApiClient();
