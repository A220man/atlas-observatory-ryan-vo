import React, { useState, useCallback } from "react";
import {
  ApiClient,
  GOAPAction,
  GOAPGoal,
  GOAPPlanCreateRequest,
  GOAPPlanRecord,
  GOAPPlanResponse,
  defaultApiClient,
} from "../api/client";

interface GoapPlannerPanelProps {
  client?: ApiClient;
  onPlanCreated?: (plan: GOAPPlanRecord) => void;
}

export const GoapPlannerPanel: React.FC<GoapPlannerPanelProps> = ({
  client = defaultApiClient,
  onPlanCreated,
}) => {
  const [planName, setPlanName] = useState("");
  const [initialState, setInitialState] = useState<Record<string, boolean | number | string>>({});
  const [actions, setActions] = useState<GOAPAction[]>([]);
  const [goals, setGoals] = useState<GOAPGoal[]>([]);
  const [maxSearchDepth, setMaxSearchDepth] = useState(50);
  const [maxIterations, setMaxIterations] = useState(10000);

  const [validating, setValidating] = useState(false);
  const [creating, setCreating] = useState(false);
  const [validationResult, setValidationResult] = useState<GOAPPlanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Action form state
  const [actionForm, setActionForm] = useState<Partial<GOAPAction>>({
    id: "",
    name: "",
    cost: 1.0,
    preconditions: {},
    effects: {},
  });

  // Goal form state
  const [goalForm, setGoalForm] = useState<Partial<GOAPGoal>>({
    id: "",
    name: "",
    target_state: {},
    priority: 1.0,
  });

  // Initial state form
  const [initialStateKey, setInitialStateKey] = useState("");
  const [initialStateValue, setInitialStateValue] = useState("");
  const [initialStateType, setInitialStateType] = useState<"bool" | "number" | "string">("bool");

  const parseValue = useCallback((value: string, type: "bool" | "number" | "string") => {
    switch (type) {
      case "bool":
        return value.toLowerCase() === "true";
      case "number":
        return parseFloat(value);
      default:
        return value;
    }
  }, []);

  const handleAddInitialState = useCallback(() => {
    if (!initialStateKey.trim()) return;
    const value = parseValue(initialStateValue, initialStateType);
    setInitialState((prev) => ({ ...prev, [initialStateKey.trim()]: value }));
    setInitialStateKey("");
    setInitialStateValue("");
  }, [initialStateKey, initialStateValue, initialStateType, parseValue]);

  const handleRemoveInitialState = useCallback((key: string) => {
    setInitialState((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }, []);

  const handleAddAction = useCallback(() => {
    if (!actionForm.id || !actionForm.name) {
      setError("Action ID and name are required");
      return;
    }
    if (actions.some((a) => a.id === actionForm.id)) {
      setError(`Action with ID '${actionForm.id}' already exists`);
      return;
    }
    setActions((prev) => [
      ...prev,
      {
        id: actionForm.id!,
        name: actionForm.name!,
        cost: actionForm.cost ?? 1.0,
        preconditions: actionForm.preconditions ?? {},
        effects: actionForm.effects ?? {},
      },
    ]);
    setActionForm({ id: "", name: "", cost: 1.0, preconditions: {}, effects: {} });
    setError(null);
  }, [actionForm, actions]);

  const handleRemoveAction = useCallback((id: string) => {
    setActions((prev) => prev.filter((a) => a.id !== id));
  }, []);

  const handleAddGoal = useCallback(() => {
    if (!goalForm.id || !goalForm.name) {
      setError("Goal ID and name are required");
      return;
    }
    if (goals.some((g) => g.id === goalForm.id)) {
      setError(`Goal with ID '${goalForm.id}' already exists`);
      return;
    }
    setGoals((prev) => [
      ...prev,
      {
        id: goalForm.id!,
        name: goalForm.name!,
        target_state: goalForm.target_state ?? {},
        priority: goalForm.priority ?? 1.0,
      },
    ]);
    setGoalForm({ id: "", name: "", target_state: {}, priority: 1.0 });
    setError(null);
  }, [goalForm, goals]);

  const handleRemoveGoal = useCallback((id: string) => {
    setGoals((prev) => prev.filter((g) => g.id !== id));
  }, []);

  const handleValidate = useCallback(async () => {
    if (!planName.trim()) {
      setError("Plan name is required");
      return;
    }
    if (actions.length === 0) {
      setError("At least one action is required");
      return;
    }
    if (goals.length === 0) {
      setError("At least one goal is required");
      return;
    }

    setValidating(true);
    setError(null);
    setValidationResult(null);

    try {
      const payload: GOAPPlanRequest = {
        initial_state: initialState,
        actions,
        goals,
        max_search_depth: maxSearchDepth,
        max_iterations: maxIterations,
      };
      const response = await client.validateGoapPlan(payload);
      setValidationResult(response);
      if (!response.success) {
        setError(response.error_message || "Planning failed");
      } else {
        setSuccessMessage(`Plan validated successfully! ${response.plan.length} steps, cost: ${response.total_cost.toFixed(2)}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Validation failed");
    } finally {
      setValidating(false);
    }
  }, [planName, initialState, actions, goals, maxSearchDepth, maxIterations, client]);

  const handleCreate = useCallback(async () => {
    if (!validationResult?.success) {
      setError("Please validate the plan first and ensure it succeeds");
      return;
    }

    setCreating(true);
    setError(null);

    try {
      const payload: GOAPPlanCreateRequest = {
        name: planName,
        initial_state: initialState,
        actions,
        goals,
        max_search_depth: maxSearchDepth,
        max_iterations: maxIterations,
      };
      const record = await client.createGoapPlan(payload);
      setSuccessMessage(`Plan created successfully! ID: ${record.id}`);
      onPlanCreated?.(record);
      // Reset form
      setPlanName("");
      setInitialState({});
      setActions([]);
      setGoals([]);
      setValidationResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Creation failed");
    } finally {
      setCreating(false);
    }
  }, [validationResult, planName, initialState, actions, goals, maxSearchDepth, maxIterations, client, onPlanCreated]);

  const renderWorldState = (state: Record<string, boolean | number | string>, title: string, onRemove?: (key: string) => void) => (
    <div className="world-state-section">
      <h5>{title} ({Object.keys(state).length})</h5>
      {Object.keys(state).length === 0 ? (
        <p className="empty-state">None</p>
      ) : (
        <ul>
          {Object.entries(state).map(([key, value]) => (
            <li key={key}>
              <code>{key}</code>: <strong>{String(value)}</strong>
              {onRemove && <button onClick={() => onRemove(key)} className="remove-btn">×</button>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );

  const renderAction = (action: GOAPAction) => (
    <div className="action-card">
      <div className="action-header">
        <strong>{action.name}</strong> (<code>{action.id}</code>)
        <span className="cost">cost: {action.cost}</span>
      </div>
      <div className="action-details">
        <div className="preconditions">
          <strong>Preconditions:</strong>
          {Object.keys(action.preconditions).length === 0 ? " (none)" : (
            <span>{JSON.stringify(action.preconditions)}</span>
          )}
        </div>
        <div className="effects">
          <strong>Effects:</strong>
          {Object.keys(action.effects).length === 0 ? " (none)" : (
            <span>{JSON.stringify(action.effects)}</span>
          )}
        </div>
      </div>
    </div>
  );

  const renderGoal = (goal: GOAPGoal) => (
    <div className="goal-card">
      <div className="goal-header">
        <strong>{goal.name}</strong> (<code>{goal.id}</code>)
        <span className="priority">priority: {goal.priority}</span>
      </div>
      <div className="goal-details">
        <strong>Target State:</strong>
        {Object.keys(goal.target_state).length === 0 ? " (none)" : (
          <span>{JSON.stringify(goal.target_state)}</span>
        )}
      </div>
    </div>
  );

  return (
    <div className="goap-planner-panel">
      <h2>GOAP Action Planner</h2>
      <p className="description">
        Goal-Oriented Action Planning using A* search. Define actions with preconditions/effects and goals to synthesize optimal action sequences.
      </p>

      <div className="form-section">
        <h3>Plan Configuration</h3>
        <div className="form-row">
          <label>
            Plan Name:
            <input
              type="text"
              value={planName}
              onChange={(e) => setPlanName(e.target.value)}
              placeholder="e.g., Build and Deploy Application"
            />
          </label>
        </div>
        <div className="form-row">
          <label>
            Max Search Depth:
            <input
              type="number"
              value={maxSearchDepth}
              onChange={(e) => setMaxSearchDepth(parseInt(e.target.value) || 50)}
              min={1}
              max={200}
            />
          </label>
          <label>
            Max Iterations:
            <input
              type="number"
              value={maxIterations}
              onChange={(e) => setMaxIterations(parseInt(e.target.value) || 10000)}
              min={1}
              max={100000}
            />
          </label>
        </div>
      </div>

      <div className="form-section">
        <h3>Initial World State</h3>
        <div className="form-row">
          <input
            type="text"
            value={initialStateKey}
            onChange={(e) => setInitialStateKey(e.target.value)}
            placeholder="State key (e.g., hasCode)"
          />
          <select value={initialStateType} onChange={(e) => setInitialStateType(e.target.value as "bool" | "number" | "string")}>
            <option value="bool">Boolean</option>
            <option value="number">Number</option>
            <option value="string">String</option>
          </select>
          <input
            type="text"
            value={initialStateValue}
            onChange={(e) => setInitialStateValue(e.target.value)}
            placeholder="Value (e.g., true, 5, 'hello')"
          />
          <button onClick={handleAddInitialState} disabled={!initialStateKey.trim()}>
            Add
          </button>
        </div>
        {renderWorldState(initialState, "Current Initial State", handleRemoveInitialState)}
      </div>

      <div className="form-section">
        <h3>Actions</h3>
        <div className="form-row">
          <input
            type="text"
            value={actionForm.id}
            onChange={(e) => setActionForm({ ...actionForm, id: e.target.value })}
            placeholder="Action ID (e.g., writeCode)"
          />
          <input
            type="text"
            value={actionForm.name}
            onChange={(e) => setActionForm({ ...actionForm, name: e.target.value })}
            placeholder="Action Name (e.g., Write Code)"
          />
          <input
            type="number"
            step="0.1"
            value={actionForm.cost ?? 1.0}
            onChange={(e) => setActionForm({ ...actionForm, cost: parseFloat(e.target.value) })}
            placeholder="Cost"
            min="0.01"
          />
        </div>
        <div className="form-row">
          <label>
            Preconditions (JSON):
            <textarea
              value={JSON.stringify(actionForm.preconditions, null, 2)}
              onChange={(e) => {
                try {
                  setActionForm({ ...actionForm, preconditions: JSON.parse(e.target.value) });
                } catch {
                  // Ignore invalid JSON while typing
                }
              }}
              rows={2}
              placeholder='{"hasCode": false}'
            />
          </label>
          <label>
            Effects (JSON):
            <textarea
              value={JSON.stringify(actionForm.effects, null, 2)}
              onChange={(e) => {
                try {
                  setActionForm({ ...actionForm, effects: JSON.parse(e.target.value) });
                } catch {
                  // Ignore invalid JSON while typing
                }
              }}
              rows={2}
              placeholder='{"hasCode": true}'
            />
          </label>
        </div>
        <button onClick={handleAddAction} disabled={!actionForm.id || !actionForm.name}>
          Add Action
        </button>
        <div className="items-list">
          {actions.map(renderAction)}
        </div>
      </div>

      <div className="form-section">
        <h3>Goals</h3>
        <div className="form-row">
          <input
            type="text"
            value={goalForm.id}
            onChange={(e) => setGoalForm({ ...goalForm, id: e.target.value })}
            placeholder="Goal ID (e.g., codeWritten)"
          />
          <input
            type="text"
            value={goalForm.name}
            onChange={(e) => setGoalForm({ ...goalForm, name: e.target.value })}
            placeholder="Goal Name (e.g., Code Written)"
          />
          <input
            type="number"
            step="0.1"
            value={goalForm.priority ?? 1.0}
            onChange={(e) => setGoalForm({ ...goalForm, priority: parseFloat(e.target.value) })}
            placeholder="Priority"
            min="0.01"
          />
        </div>
        <div className="form-row">
          <label>
            Target State (JSON):
            <textarea
              value={JSON.stringify(goalForm.target_state, null, 2)}
              onChange={(e) => {
                try {
                  setGoalForm({ ...goalForm, target_state: JSON.parse(e.target.value) });
                } catch {
                  // Ignore invalid JSON while typing
                }
              }}
              rows={2}
              placeholder='{"hasCode": true, "testsPass": true}'
            />
          </label>
        </div>
        <button onClick={handleAddGoal} disabled={!goalForm.id || !goalForm.name}>
          Add Goal
        </button>
        <div className="items-list">
          {goals.map(renderGoal)}
        </div>
      </div>

      <div className="actions-bar">
        <button onClick={handleValidate} disabled={validating || creating} className="primary">
          {validating ? "Validating..." : "Validate Plan"}
        </button>
        <button
          onClick={handleCreate}
          disabled={creating || !validationResult?.success}
          className="success"
        >
          {creating ? "Creating..." : "Create Plan"}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}
      {successMessage && <div className="success-message">{successMessage}</div>}

      {validationResult && (
        <div className="validation-result">
          <h4>Validation Result</h4>
          <div className="result-summary">
            <span className={validationResult.success ? "success" : "error"}>
              {validationResult.success ? "✓ Plan Found" : "✗ No Valid Plan"}
            </span>
            <span>Steps: {validationResult.plan.length}</span>
            <span>Total Cost: {validationResult.total_cost.toFixed(2)}</span>
            <span>Nodes Expanded: {validationResult.nodes_expanded}</span>
            <span>Search Time: {validationResult.search_time_ms.toFixed(2)}ms</span>
          </div>
          {validationResult.error_message && (
            <div className="error-detail">{validationResult.error_message}</div>
          )}
          {validationResult.plan.length > 0 && (
            <div className="plan-steps">
              <h5>Plan Steps:</h5>
              <ol>
                {validationResult.plan.map((step, index) => (
                  <li key={index}>
                    <strong>Step {index + 1}:</strong> {step.action_name} (cost: {step.cost.toFixed(2)})
                    <details>
                      <summary>Resulting State</summary>
                      <pre>{JSON.stringify(step.resulting_state, null, 2)}</pre>
                    </details>
                  </li>
                ))}
              </ol>
            </div>
          )}
          <div className="final-state">
            <strong>Final State:</strong>
            <pre>{JSON.stringify(validationResult.final_state, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default GoapPlannerPanel;
