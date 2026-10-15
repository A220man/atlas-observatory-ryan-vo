import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import http from "node:http";
import { AddressInfo } from "node:net";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { App } from "./App";
import { ApiClient, SwarmPlanCreateRequest, SwarmPlanRecord } from "./api/client";

describe("Atlas Observatory UI & HTTP Boundary Integration", () => {
  let server: http.Server;
  let baseUrl = "";
  let storedPlans: SwarmPlanRecord[] = [];

  beforeAll(async () => {
    storedPlans = [
      {
        id: "plan-seed-1",
        name: "V3 Core Orchestrator & HNSW Memory Unification",
        objective: "Decompose monolithic orchestrator into bounded domain modules.",
        topology: "hierarchical",
        max_agents: 12,
        subtasks: [
          {
            id: "adr-contracts",
            title: "Specify DDD bounded context contracts",
            role: "architect",
            estimated_steps: 3,
            mcp_calls: 1,
            base_tokens: 2200,
            depends_on: [],
          },
          {
            id: "simulative-router",
            title: "Implement conditional SimulativePlanningRouter",
            role: "coder",
            estimated_steps: 4,
            mcp_calls: 2,
            base_tokens: 2900,
            depends_on: ["adr-contracts"],
          },
        ],
        schedule: [
          {
            id: "adr-contracts",
            title: "Specify DDD bounded context contracts",
            role: "architect",
            assigned_agent_slot: "architect-1",
            depth_level: 0,
            start_step: 0,
            end_step: 3,
            on_critical_path: true,
            estimated_steps: 3,
            mcp_calls: 1,
            base_tokens: 2200,
            flat_tokens: 3232,
            routed_tokens: 2581,
            depends_on: [],
          },
          {
            id: "simulative-router",
            title: "Implement conditional SimulativePlanningRouter",
            role: "coder",
            assigned_agent_slot: "coder-1",
            depth_level: 1,
            start_step: 3,
            end_step: 7,
            on_critical_path: true,
            estimated_steps: 4,
            mcp_calls: 2,
            base_tokens: 2900,
            flat_tokens: 5120,
            routed_tokens: 3729,
            depends_on: ["adr-contracts"],
          },
        ],
        routing: {
          mode: "simulative_forward_pass",
          triggered_by: ["critical_path_horizon (7 > 5 steps)", "mcp_call_density (3 >= 2 calls)"],
          horizon_threshold: 5,
          mcp_call_threshold: 2,
          critical_path_steps: 7,
          total_steps: 7,
          total_mcp_calls: 3,
          shadow_pass_tokens: 256,
          flat_tier3_tokens: 8352,
          selective_routed_tokens: 6566,
          token_savings: 1786,
          token_reduction_pct: 21.38,
          estimated_routing_overhead_ms: 28.4,
        },
        topology_metrics: {
          topology: "hierarchical",
          max_agents: 12,
          active_agents: 2,
          communication_edges: 1,
          coordination_latency_ms: 4.8,
          parallel_speedup: 1.0,
          parallel_efficiency_pct: 50.0,
          role_distribution: { architect: 1, coder: 1 },
          bottleneck_warning: "Subtasks form a purely sequential chain (speedup 1.0x); decouple independent steps.",
        },
        created_at: "2026-10-15T23:00:00Z",
        updated_at: "2026-10-15T23:00:00Z",
      },
    ];

    server = http.createServer((req, res) => {
      const url = new URL(req.url ?? "/", "http://127.0.0.1");
      res.setHeader("Content-Type", "application/json");

      if (req.method === "GET" && url.pathname === "/api/v1/swarms/plans") {
        const topology = url.searchParams.get("topology");
        const filtered = topology
          ? storedPlans.filter((p) => p.topology === topology)
          : storedPlans;
        res.writeHead(200);
        res.end(
          JSON.stringify({
            items: filtered,
            total: filtered.length,
            limit: 20,
            offset: 0,
            summary: {
              total_plans: storedPlans.length,
              simulative_routed_count: storedPlans.filter(
                (p) => p.routing.mode === "simulative_forward_pass"
              ).length,
              reactive_direct_count: storedPlans.filter(
                (p) => p.routing.mode === "reactive_direct"
              ).length,
              avg_token_reduction_pct: 21.38,
              avg_parallel_efficiency_pct: 64.0,
              total_tokens_saved: 1786,
            },
          })
        );
        return;
      }

      if (req.method === "POST" && url.pathname === "/api/v1/swarms/plans") {
        let body = "";
        req.on("data", (chunk) => {
          body += chunk;
        });
        req.on("end", () => {
          const payload = JSON.parse(body) as SwarmPlanCreateRequest;
          const totalSteps = payload.subtasks.reduce((acc, s) => acc + s.estimated_steps, 0);
          const totalMcp = payload.subtasks.reduce((acc, s) => acc + s.mcp_calls, 0);
          const isSim =
            totalSteps > payload.horizon_threshold || totalMcp >= payload.mcp_call_threshold;
          const created: SwarmPlanRecord = {
            id: `plan-${storedPlans.length + 1}`,
            name: payload.name,
            objective: payload.objective,
            topology: payload.topology,
            max_agents: payload.max_agents,
            subtasks: payload.subtasks,
            schedule: payload.subtasks.map((s, idx) => ({
              ...s,
              assigned_agent_slot: `${s.role}-1`,
              depth_level: idx,
              start_step: idx * 2,
              end_step: idx * 2 + s.estimated_steps,
              on_critical_path: true,
              flat_tokens: 2000,
              routed_tokens: 1500,
            })),
            routing: {
              mode: isSim ? "simulative_forward_pass" : "reactive_direct",
              triggered_by: isSim ? ["horizon_or_mcp_threshold"] : [],
              horizon_threshold: payload.horizon_threshold,
              mcp_call_threshold: payload.mcp_call_threshold,
              critical_path_steps: totalSteps,
              total_steps: totalSteps,
              total_mcp_calls: totalMcp,
              shadow_pass_tokens: isSim ? 256 : 0,
              flat_tier3_tokens: 6000,
              selective_routed_tokens: 4500,
              token_savings: 1500,
              token_reduction_pct: 25.0,
              estimated_routing_overhead_ms: 19.2,
            },
            topology_metrics: {
              topology: payload.topology,
              max_agents: payload.max_agents,
              active_agents: Math.min(payload.max_agents, payload.subtasks.length),
              communication_edges: 3,
              coordination_latency_ms: 8.4,
              parallel_speedup: 1.5,
              parallel_efficiency_pct: 75.0,
              role_distribution: { coder: 1 },
              bottleneck_warning: null,
            },
            created_at: "2026-10-15T23:05:00Z",
            updated_at: "2026-10-15T23:05:00Z",
          };
          storedPlans = [created, ...storedPlans];
          res.writeHead(201);
          res.end(JSON.stringify(created));
        });
        return;
      }

      if (req.method === "GET" && url.pathname.endsWith("/export")) {
        const planId = url.pathname.split("/")[4];
        const found = storedPlans.find((p) => p.id === planId);
        res.writeHead(200);
        res.end(
          JSON.stringify({
            schema_version: 1,
            tool: "atlas-observatory-ryan-vo",
            plan: found,
          })
        );
        return;
      }

      if (
        (req.method === "GET" || req.method === "POST") &&
        url.pathname.startsWith("/api/v1/benchmarks/")
      ) {
        res.writeHead(req.method === "POST" ? 201 : 200);
        res.end(
          JSON.stringify({
            id: "bench-test-1",
            suite_name: "SR2AM Selective Simulative Routing Benchmark v1",
            horizon_threshold: 5,
            mcp_call_threshold: 2,
            case_count: 2,
            routing_accuracy_pct: 100.0,
            baseline_total_tokens: 12400,
            routed_total_tokens: 9100,
            overall_token_reduction_pct: 26.61,
            avg_overhead_ms: 18.4,
            cases: [
              {
                case_id: "gaia-single-hop-status",
                title: "Single-Hop Config & Version Check",
                category: "reactive-lookup",
                expected_mode: "reactive_direct",
                predicted_mode: "reactive_direct",
                matched_expectation: true,
                critical_path_steps: 3,
                total_mcp_calls: 1,
                baseline_flat_tokens: 1300,
                selective_routed_tokens: 1120,
                token_reduction_pct: 13.85,
                routing_overhead_ms: 2.4,
              },
              {
                case_id: "sr2am-multi-hop-rag",
                title: "Multi-Hop Temporal Vector Memory Synthesis",
                category: "simulative-rag",
                expected_mode: "simulative_forward_pass",
                predicted_mode: "simulative_forward_pass",
                matched_expectation: true,
                critical_path_steps: 10,
                total_mcp_calls: 6,
                baseline_flat_tokens: 11100,
                selective_routed_tokens: 7980,
                token_reduction_pct: 28.11,
                routing_overhead_ms: 34.4,
              },
            ],
            created_at: "2026-10-15T23:00:00Z",
          })
        );
        return;
      }

      res.writeHead(404);
      res.end(JSON.stringify({ detail: "Not found" }));
    });

    await new Promise<void>((resolve) => {
      server.listen(0, "127.0.0.1", () => resolve());
    });
    const addr = server.address() as AddressInfo;
    baseUrl = `http://127.0.0.1:${addr.port}`;
  });

  afterAll(async () => {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  });

  it("loads seeded swarm plans and renders DAG critical-path and benchmark metrics", async () => {
    const client = new ApiClient(baseUrl);
    render(<App client={client} />);

    await waitFor(() => {
      expect(
        screen.getAllByText("V3 Core Orchestrator & HNSW Memory Unification").length
      ).toBeGreaterThan(0);
    });

    expect(screen.getAllByText("21.38%").length).toBeGreaterThan(0);
    expect(
      screen.getByText("Multi-Hop Temporal Vector Memory Synthesis")
    ).toBeInTheDocument();
  });

  it("creates a new swarm plan across the HTTP boundary and updates the inspector", async () => {
    const client = new ApiClient(baseUrl);
    render(<App client={client} />);

    await waitFor(() => {
      expect(screen.getByLabelText("Plan Name")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Plan Name"), {
      target: { value: "Federation Breaker Smoke Workflow" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Evaluate & Save Swarm Plan/i }));

    await waitFor(() => {
      expect(
        screen.getAllByText("Federation Breaker Smoke Workflow").length
      ).toBeGreaterThan(0);
    });
  });

  it("exports a selected swarm plan bundle as JSON and triggers benchmark evaluation", async () => {
    const client = new ApiClient(baseUrl);
    render(<App client={client} />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Export JSON/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Export JSON/i }));

    await waitFor(() => {
      expect(screen.getByLabelText("Exported Plan JSON")).toHaveTextContent(
        "atlas-observatory-ryan-vo"
      );
    });

    fireEvent.click(screen.getByRole("button", { name: /Run Benchmark Suite/i }));
    await waitFor(() => {
      expect(screen.getByText("26.61%")).toBeInTheDocument();
    });
  });
});
