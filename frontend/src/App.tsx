import React, { useCallback, useEffect, useState } from "react";
import {
  ApiClient,
  BenchmarkRunRecord,
  DashboardSummaryMetrics,
  SwarmPlanCreateRequest,
  SwarmPlanRecord,
  defaultApiClient,
} from "./api/client";
import { SwarmPlanForm } from "./components/SwarmPlanForm";
import { SwarmPlanDetail } from "./components/SwarmPlanDetail";
import { BenchmarkPanel } from "./components/BenchmarkPanel";
import { WitnessVerifierPanel } from "./components/WitnessVerifierPanel";

interface AppProps {
  client?: ApiClient;
}

export const App: React.FC<AppProps> = ({ client = defaultApiClient }) => {
  const [plans, setPlans] = useState<SwarmPlanRecord[]>([]);
  const [summary, setSummary] = useState<DashboardSummaryMetrics | null>(null);
  const [selectedPlan, setSelectedPlan] = useState<SwarmPlanRecord | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkRunRecord | null>(null);
  const [exportedJson, setExportedJson] = useState<string | null>(null);

  const [topologyFilter, setTopologyFilter] = useState("");
  const [routingFilter, setRoutingFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [runningBenchmark, setRunningBenchmark] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [planRes, benchRes] = await Promise.all([
        client.listSwarmPlans({
          topology: topologyFilter || undefined,
          routing_mode: routingFilter || undefined,
          search: searchQuery || undefined,
        }),
        client.getLatestBenchmark(),
      ]);
      setPlans(planRes.items);
      setSummary(planRes.summary);
      setBenchmark(benchRes);
      setSelectedPlan((current) => {
        if (current) {
          const updated = planRes.items.find((p) => p.id === current.id);
          if (updated) return updated;
        }
        return planRes.items[0] ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load observatory data.");
    } finally {
      setLoading(false);
    }
  }, [client, topologyFilter, routingFilter, searchQuery]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleCreatePlan = async (payload: SwarmPlanCreateRequest) => {
    setSubmitting(true);
    setError(null);
    try {
      const created = await client.createSwarmPlan(payload);
      setExportedJson(null);
      await loadData();
      setSelectedPlan(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create swarm plan.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleExportPlan = async (planId: string) => {
    setError(null);
    try {
      const bundle = await client.exportSwarmPlan(planId);
      setExportedJson(JSON.stringify(bundle, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to export swarm plan.");
    }
  };

  const handleDeletePlan = async (planId: string) => {
    setError(null);
    try {
      await client.deleteSwarmPlan(planId);
      setExportedJson(null);
      if (selectedPlan?.id === planId) {
        setSelectedPlan(null);
      }
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete swarm plan.");
    }
  };

  const handleRunBenchmark = async (
    horizonThreshold: number,
    mcpCallThreshold: number
  ) => {
    setRunningBenchmark(true);
    setError(null);
    try {
      const res = await client.runBenchmark(horizonThreshold, mcpCallThreshold);
      setBenchmark(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to execute benchmark suite.");
    } finally {
      setRunningBenchmark(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Atlas Observatory — Swarm Topology &amp; Simulative Planning Router</h1>
          <p>
            Deterministic DAG critical-path horizon analyzer, selective SR²AM routing engine,
            and multi-agent topology evaluator.
          </p>
        </div>
        <span className="badge">Active Feature: simulative-swarm-planner</span>
      </header>

      {error && (
        <div className="error-banner" role="alert">
          <strong>Error:</strong> {error}
        </div>
      )}

      {summary && (
        <section className="metrics-grid" aria-label="Observatory Summary Metrics">
          <div className="metric-card">
            <div className="metric-label">Evaluated Swarm Plans</div>
            <div className="metric-value">{summary.total_plans}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Simulative Forward / Reactive</div>
            <div className="metric-value">
              {summary.simulative_routed_count} / {summary.reactive_direct_count}
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Mean Token Reduction</div>
            <div className="metric-value">{summary.avg_token_reduction_pct}%</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Cumulative Tokens Saved</div>
            <div className="metric-value">
              {summary.total_tokens_saved.toLocaleString()}
            </div>
          </div>
        </section>
      )}

      <div className="workspace-grid">
        <div>
          <SwarmPlanForm onSubmit={handleCreatePlan} submitting={submitting} />

          <section className="panel" aria-label="Saved Swarm Plans">
            <h2 style={{ fontSize: "1.15rem", marginBottom: "0.75rem" }}>
              Evaluated Swarm Plans
            </h2>
            <div className="form-row">
              <label>
                Filter Topology
                <select
                  aria-label="Filter Topology"
                  value={topologyFilter}
                  onChange={(e) => setTopologyFilter(e.target.value)}
                >
                  <option value="">All topologies</option>
                  <option value="hierarchical">hierarchical</option>
                  <option value="mesh">mesh</option>
                  <option value="ring">ring</option>
                  <option value="star">star</option>
                </select>
              </label>
              <label>
                Filter Routing Mode
                <select
                  aria-label="Filter Routing Mode"
                  value={routingFilter}
                  onChange={(e) => setRoutingFilter(e.target.value)}
                >
                  <option value="">All modes</option>
                  <option value="simulative_forward_pass">simulative_forward_pass</option>
                  <option value="reactive_direct">reactive_direct</option>
                </select>
              </label>
              <label>
                Search Plans
                <input
                  aria-label="Search Plans"
                  placeholder="Filter by name or objective..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </label>
            </div>

            {loading ? (
              <p>Loading swarm plans...</p>
            ) : plans.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>
                No swarm plans match the selected filters.
              </p>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Plan</th>
                    <th>Topology</th>
                    <th>Routing Mode</th>
                    <th>Horizon</th>
                    <th>Reduction</th>
                  </tr>
                </thead>
                <tbody>
                  {plans.map((p) => (
                    <tr
                      key={p.id}
                      className={selectedPlan?.id === p.id ? "selected-row" : ""}
                      onClick={() => {
                        setSelectedPlan(p);
                        setExportedJson(null);
                      }}
                      style={{ cursor: "pointer" }}
                    >
                      <td>
                        <strong>{p.name}</strong>
                      </td>
                      <td>{p.topology}</td>
                      <td>
                        <span
                          className={`badge ${
                            p.routing.mode === "simulative_forward_pass"
                              ? "badge-simulative"
                              : "badge-reactive"
                          }`}
                        >
                          {p.routing.mode}
                        </span>
                      </td>
                      <td>{p.routing.critical_path_steps} steps</td>
                      <td>{p.routing.token_reduction_pct}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </div>

        <div>
          <SwarmPlanDetail
            plan={selectedPlan}
            exportedJson={exportedJson}
            onExport={handleExportPlan}
            onDelete={handleDeletePlan}
          />
        </div>
      </div>

      <BenchmarkPanel
        benchmark={benchmark}
        onRunBenchmark={handleRunBenchmark}
        running={runningBenchmark}
      />

      <WitnessVerifierPanel client={client} />
    </div>
  );
};

export default App;
