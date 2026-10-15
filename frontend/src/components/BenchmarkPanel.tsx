import React, { useState } from "react";
import { BenchmarkRunRecord } from "../api/client";

interface BenchmarkPanelProps {
  benchmark: BenchmarkRunRecord | null;
  onRunBenchmark: (horizonThreshold: number, mcpCallThreshold: number) => Promise<void>;
  running: boolean;
}

export const BenchmarkPanel: React.FC<BenchmarkPanelProps> = ({
  benchmark,
  onRunBenchmark,
  running,
}) => {
  const [horizonThreshold, setHorizonThreshold] = useState(
    benchmark?.horizon_threshold ?? 5
  );
  const [mcpCallThreshold, setMcpCallThreshold] = useState(
    benchmark?.mcp_call_threshold ?? 2
  );

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    await onRunBenchmark(horizonThreshold, mcpCallThreshold);
  };

  return (
    <section className="panel" aria-label="Benchmark Evaluation Suite">
      <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "1rem", marginBottom: "1rem" }}>
        <div>
          <h2 style={{ marginBottom: "0.25rem", fontSize: "1.15rem" }}>
            Reproducible SR²AM Routing Benchmark Suite
          </h2>
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.88rem" }}>
            Evaluates selective simulative forward planning against flat Tier-3 dispatch across 8 labeled agent workloads.
          </p>
        </div>
        <form onSubmit={handleRun} style={{ display: "flex", gap: "0.6rem", alignItems: "flex-end" }}>
          <label>
            Horizon Gate
            <input
              aria-label="Benchmark Horizon Gate"
              type="number"
              min={1}
              max={20}
              value={horizonThreshold}
              onChange={(e) => setHorizonThreshold(Number(e.target.value))}
              style={{ width: "80px" }}
            />
          </label>
          <label>
            MCP Gate
            <input
              aria-label="Benchmark MCP Gate"
              type="number"
              min={1}
              max={15}
              value={mcpCallThreshold}
              onChange={(e) => setMcpCallThreshold(Number(e.target.value))}
              style={{ width: "80px" }}
            />
          </label>
          <button type="submit" disabled={running}>
            {running ? "Running Suite..." : "Run Benchmark Suite"}
          </button>
        </form>
      </div>

      {benchmark && (
        <>
          <div className="metrics-grid" style={{ marginBottom: "1rem" }}>
            <div className="metric-card">
              <div className="metric-label">Routing Classification Accuracy</div>
              <div className="metric-value">{benchmark.routing_accuracy_pct}%</div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                {benchmark.case_count} labeled workloads
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Overall Token Reduction</div>
              <div className="metric-value">{benchmark.overall_token_reduction_pct}%</div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                {benchmark.routed_total_tokens.toLocaleString()} vs{" "}
                {benchmark.baseline_total_tokens.toLocaleString()} baseline tokens
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Mean Router Overhead</div>
              <div className="metric-value">{benchmark.avg_overhead_ms} ms</div>
              <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
                Target: &le; 30.0 ms pre-execution budget
              </div>
            </div>
          </div>

          <table className="data-table">
            <thead>
              <tr>
                <th>Workload Case</th>
                <th>Category</th>
                <th>Horizon / MCP</th>
                <th>Expected</th>
                <th>Predicted</th>
                <th>Token Reduction</th>
              </tr>
            </thead>
            <tbody>
              {benchmark.cases.map((c) => (
                <tr key={c.case_id}>
                  <td>
                    <strong>{c.title}</strong>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      <code>{c.case_id}</code>
                    </div>
                  </td>
                  <td>{c.category}</td>
                  <td>
                    {c.critical_path_steps} steps / {c.total_mcp_calls} MCP
                  </td>
                  <td><code>{c.expected_mode}</code></td>
                  <td>
                    <span
                      className={`badge ${
                        c.predicted_mode === "simulative_forward_pass"
                          ? "badge-simulative"
                          : "badge-reactive"
                      }`}
                    >
                      {c.predicted_mode}
                    </span>
                  </td>
                  <td>
                    {c.token_reduction_pct}% ({c.selective_routed_tokens.toLocaleString()} /{" "}
                    {c.baseline_flat_tokens.toLocaleString()})
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
};
