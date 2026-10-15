import React from "react";
import { SwarmPlanRecord } from "../api/client";

interface SwarmPlanDetailProps {
  plan: SwarmPlanRecord | null;
  exportedJson: string | null;
  onExport: (planId: string) => Promise<void>;
  onDelete: (planId: string) => Promise<void>;
}

export const SwarmPlanDetail: React.FC<SwarmPlanDetailProps> = ({
  plan,
  exportedJson,
  onExport,
  onDelete,
}) => {
  if (!plan) {
    return (
      <div className="panel">
        <h2>Swarm Plan Inspector</h2>
        <p style={{ color: "var(--text-muted)" }}>
          Select a swarm plan from the table to inspect its critical-path DAG schedule,
          SR²AM routing decision, and topology communication metrics.
        </p>
      </div>
    );
  }

  const { routing, topology_metrics: topo, schedule } = plan;

  return (
    <div className="panel" aria-label="Swarm Plan Inspector">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
        <div>
          <h2 style={{ marginBottom: "0.25rem" }}>{plan.name}</h2>
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.9rem" }}>
            {plan.objective}
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <button
            type="button"
            className="secondary"
            onClick={() => onExport(plan.id)}
          >
            Export JSON
          </button>
          <button
            type="button"
            className="danger"
            onClick={() => onDelete(plan.id)}
          >
            Delete Plan
          </button>
        </div>
      </div>

      <div className="metrics-grid" style={{ marginTop: "1rem", marginBottom: "1rem" }}>
        <div className="metric-card">
          <div className="metric-label">Routing Decision</div>
          <div style={{ marginTop: "0.45rem" }}>
            <span
              className={`badge ${
                routing.mode === "simulative_forward_pass"
                  ? "badge-simulative"
                  : "badge-reactive"
              }`}
            >
              {routing.mode}
            </span>
          </div>
          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: "0.4rem" }}>
            {routing.triggered_by.length > 0
              ? routing.triggered_by.join(" • ")
              : "Below horizon & MCP thresholds"}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Critical Path / Total Steps</div>
          <div className="metric-value">
            {routing.critical_path_steps} / {routing.total_steps} steps
          </div>
          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            Total MCP calls: {routing.total_mcp_calls}
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Token Budget Savings</div>
          <div className="metric-value">{routing.token_reduction_pct}%</div>
          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            {routing.selective_routed_tokens.toLocaleString()} vs{" "}
            {routing.flat_tier3_tokens.toLocaleString()} flat tokens (shadow:{" "}
            {routing.shadow_pass_tokens})
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Topology Efficiency ({topo.topology})</div>
          <div className="metric-value">{topo.parallel_efficiency_pct}%</div>
          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)" }}>
            {topo.active_agents} active agents • {topo.communication_edges} edges •{" "}
            {topo.parallel_speedup}x speedup
          </div>
        </div>
      </div>

      {topo.bottleneck_warning && (
        <div className="warning-banner" role="status">
          <strong>Topology Advisory:</strong> {topo.bottleneck_warning}
        </div>
      )}

      <h3 style={{ marginTop: "1.1rem", marginBottom: "0.5rem", fontSize: "1rem" }}>
        Critical-Path Schedule & Subtask Token Allocation
      </h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Node</th>
            <th>Agent Slot</th>
            <th>Window</th>
            <th>Critical Path</th>
            <th>Flat Tokens</th>
            <th>Routed Tokens</th>
          </tr>
        </thead>
        <tbody>
          {schedule.map((node) => (
            <tr key={node.id}>
              <td>
                <strong>{node.title}</strong>
                <div style={{ fontSize: "0.76rem", color: "var(--text-muted)" }}>
                  <code>{node.id}</code> (depth {node.depth_level}, {node.mcp_calls} MCP)
                </div>
              </td>
              <td><code>{node.assigned_agent_slot}</code></td>
              <td>
                step {node.start_step} → {node.end_step}
              </td>
              <td>{node.on_critical_path ? "CRITICAL" : "parallel-slack"}</td>
              <td>{node.flat_tokens.toLocaleString()}</td>
              <td>{node.routed_tokens.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {exportedJson && (
        <div style={{ marginTop: "1rem" }}>
          <h3 style={{ fontSize: "0.95rem", marginBottom: "0.4rem" }}>
            Exported Plan Bundle (JSON)
          </h3>
          <pre
            aria-label="Exported Plan JSON"
            style={{
              background: "var(--bg-card)",
              padding: "0.75rem",
              borderRadius: "6px",
              overflowX: "auto",
              maxHeight: "220px",
              fontSize: "0.78rem",
            }}
          >
            {exportedJson}
          </pre>
        </div>
      )}
    </div>
  );
};
