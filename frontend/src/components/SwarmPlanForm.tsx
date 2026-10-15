import React, { useState } from "react";
import {
  AgentRole,
  SubtaskInput,
  SwarmPlanCreateRequest,
  SwarmTopology,
} from "../api/client";

interface SwarmPlanFormProps {
  onSubmit: (payload: SwarmPlanCreateRequest) => Promise<void>;
  submitting: boolean;
}

const DEFAULT_SUBTASKS: SubtaskInput[] = [
  {
    id: "spec-boundaries",
    title: "Define module boundaries and memory schema",
    role: "architect",
    estimated_steps: 3,
    mcp_calls: 1,
    base_tokens: 1800,
    depends_on: [],
  },
  {
    id: "impl-router",
    title: "Implement conditional forward-simulation router",
    role: "coder",
    estimated_steps: 4,
    mcp_calls: 2,
    base_tokens: 2600,
    depends_on: ["spec-boundaries"],
  },
  {
    id: "verify-manifest",
    title: "Run cross-platform manifest integrity assertions",
    role: "validator",
    estimated_steps: 2,
    mcp_calls: 1,
    base_tokens: 1500,
    depends_on: ["impl-router"],
  },
];

export const SwarmPlanForm: React.FC<SwarmPlanFormProps> = ({
  onSubmit,
  submitting,
}) => {
  const [name, setName] = useState("Multi-Agent RAG & Router Verification");
  const [objective, setObjective] = useState(
    "Coordinate architecture, implementation, and manifest verification across a bounded swarm."
  );
  const [topology, setTopology] = useState<SwarmTopology>("hierarchical");
  const [maxAgents, setMaxAgents] = useState(6);
  const [horizonThreshold, setHorizonThreshold] = useState(5);
  const [mcpCallThreshold, setMcpCallThreshold] = useState(2);
  const [subtasks, setSubtasks] = useState<SubtaskInput[]>(DEFAULT_SUBTASKS);
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newTaskRole, setNewTaskRole] = useState<AgentRole>("coder");
  const [newTaskSteps, setNewTaskSteps] = useState(2);
  const [newTaskMcp, setNewTaskMcp] = useState(1);

  const handleAddSubtask = () => {
    const trimmed = newTaskTitle.trim();
    if (trimmed.length < 2) return;
    const id = `step-${subtasks.length + 1}`;
    const prevId = subtasks.length > 0 ? [subtasks[subtasks.length - 1].id] : [];
    setSubtasks([
      ...subtasks,
      {
        id,
        title: trimmed,
        role: newTaskRole,
        estimated_steps: newTaskSteps,
        mcp_calls: newTaskMcp,
        base_tokens: 1400,
        depends_on: prevId,
      },
    ]);
    setNewTaskTitle("");
  };

  const handleLoadReactivePreset = () => {
    setName("Quick Two-Step Lint & Version Probe");
    setObjective("Run shallow local verification without exceeding horizon or MCP thresholds.");
    setTopology("star");
    setMaxAgents(3);
    setSubtasks([
      {
        id: "probe-config",
        title: "Read local package and runtime metadata",
        role: "analyst",
        estimated_steps: 2,
        mcp_calls: 0,
        base_tokens: 600,
        depends_on: [],
      },
      {
        id: "emit-status",
        title: "Report lint and version check summary",
        role: "validator",
        estimated_steps: 1,
        mcp_calls: 1,
        base_tokens: 500,
        depends_on: ["probe-config"],
      },
    ]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit({
      name,
      objective,
      topology,
      max_agents: maxAgents,
      horizon_threshold: horizonThreshold,
      mcp_call_threshold: mcpCallThreshold,
      subtasks,
    });
  };

  return (
    <form className="panel" onSubmit={handleSubmit} aria-label="Create Swarm Plan Form">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <h2 style={{ margin: 0, fontSize: "1.15rem" }}>Create & Evaluate Swarm Plan</h2>
        <button
          type="button"
          className="secondary"
          onClick={handleLoadReactivePreset}
        >
          Load Shallow Preset
        </button>
      </div>

      <div className="form-row">
        <label>
          Plan Name
          <input
            aria-label="Plan Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </label>
        <label>
          Swarm Topology
          <select
            aria-label="Swarm Topology"
            value={topology}
            onChange={(e) => setTopology(e.target.value as SwarmTopology)}
          >
            <option value="hierarchical">hierarchical</option>
            <option value="mesh">mesh</option>
            <option value="ring">ring</option>
            <option value="star">star</option>
          </select>
        </label>
      </div>

      <label style={{ marginBottom: "0.75rem" }}>
        Workflow Objective
        <textarea
          aria-label="Workflow Objective"
          rows={2}
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
          required
        />
      </label>

      <div className="form-row">
        <label>
          Max Agents
          <input
            aria-label="Max Agents"
            type="number"
            min={2}
            max={64}
            value={maxAgents}
            onChange={(e) => setMaxAgents(Number(e.target.value))}
          />
        </label>
        <label>
          Horizon Threshold (Steps)
          <input
            aria-label="Horizon Threshold"
            type="number"
            min={1}
            max={30}
            value={horizonThreshold}
            onChange={(e) => setHorizonThreshold(Number(e.target.value))}
          />
        </label>
        <label>
          MCP Call Threshold
          <input
            aria-label="MCP Call Threshold"
            type="number"
            min={1}
            max={20}
            value={mcpCallThreshold}
            onChange={(e) => setMcpCallThreshold(Number(e.target.value))}
          />
        </label>
      </div>

      <div style={{ marginTop: "0.75rem", marginBottom: "0.75rem" }}>
        <div style={{ fontSize: "0.84rem", color: "var(--text-muted)", marginBottom: "0.4rem" }}>
          Subtask DAG ({subtasks.length} nodes)
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Role</th>
              <th>Steps</th>
              <th>MCP</th>
              <th>Depends On</th>
            </tr>
          </thead>
          <tbody>
            {subtasks.map((task) => (
              <tr key={task.id}>
                <td><code>{task.id}</code></td>
                <td>{task.title}</td>
                <td>{task.role}</td>
                <td>{task.estimated_steps}</td>
                <td>{task.mcp_calls}</td>
                <td>{task.depends_on.join(", ") || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="form-row" style={{ alignItems: "flex-end" }}>
        <label>
          Add Subtask Title
          <input
            aria-label="Add Subtask Title"
            placeholder="e.g. Run regression benchmark"
            value={newTaskTitle}
            onChange={(e) => setNewTaskTitle(e.target.value)}
          />
        </label>
        <label>
          Role
          <select
            aria-label="Add Subtask Role"
            value={newTaskRole}
            onChange={(e) => setNewTaskRole(e.target.value as AgentRole)}
          >
            <option value="coder">coder</option>
            <option value="architect">architect</option>
            <option value="analyst">analyst</option>
            <option value="researcher">researcher</option>
            <option value="validator">validator</option>
            <option value="coordinator">coordinator</option>
          </select>
        </label>
        <label>
          Steps
          <input
            type="number"
            min={1}
            max={20}
            value={newTaskSteps}
            onChange={(e) => setNewTaskSteps(Number(e.target.value))}
          />
        </label>
        <label>
          MCP Calls
          <input
            type="number"
            min={0}
            max={10}
            value={newTaskMcp}
            onChange={(e) => setNewTaskMcp(Number(e.target.value))}
          />
        </label>
        <button type="button" className="secondary" onClick={handleAddSubtask}>
          + Add Node
        </button>
      </div>

      <div style={{ marginTop: "1rem" }}>
        <button type="submit" disabled={submitting}>
          {submitting ? "Evaluating Plan..." : "Evaluate & Save Swarm Plan"}
        </button>
      </div>
    </form>
  );
};
