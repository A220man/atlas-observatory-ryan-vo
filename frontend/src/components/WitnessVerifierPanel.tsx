import React, { useEffect, useState } from "react";
import {
  ApiClient,
  WitnessVerificationResponse,
  PlatformVerificationResult,
  ArtifactVerificationResult,
  VerificationState,
  defaultApiClient,
} from "../api/client";

interface WitnessVerifierPanelProps {
  client?: ApiClient;
}

export const WitnessVerifierPanel: React.FC<WitnessVerifierPanelProps> = ({
  client = defaultApiClient,
}) => {
  const [result, setResult] = useState<WitnessVerificationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [manifestDir, setManifestDir] = useState("verification");
  const [requireDistArtifacts, setRequireDistArtifacts] = useState(true);

  const runVerification = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await client.verifyWitnessManifests(manifestDir, requireDistArtifacts);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runVerification();
  }, []);

  const getStateColor = (state: VerificationState) => {
    switch (state) {
      case "verified_clean":
        return "var(--color-success)";
      case "drift_detected":
        return "var(--color-error)";
      case "unverifiable_missing_build":
        return "var(--color-warning)";
      default:
        return "var(--color-text-muted)";
    }
  };

  const getStateLabel = (state: VerificationState) => {
    switch (state) {
      case "verified_clean":
        return "Verified Clean";
      case "drift_detected":
        return "Drift Detected";
      case "unverifiable_missing_build":
        return "Unverifiable (Missing Build)";
      default:
        return state;
    }
  };

  if (!result) {
    return (
      <div className="panel">
        <h3>Witness Manifest Verifier</h3>
        <div className="loading">Loading verification results...</div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Witness Manifest Verifier</h3>
        <div className="panel-controls">
          <label>
            <input
              type="checkbox"
              checked={requireDistArtifacts}
              onChange={(e) => setRequireDistArtifacts(e.target.checked)}
            />
            Require dist/ artifacts
          </label>
          <input
            type="text"
            value={manifestDir}
            onChange={(e) => setManifestDir(e.target.value)}
            placeholder="Manifest directory"
            style={{ width: "200px", marginLeft: "1rem" }}
          />
          <button onClick={runVerification} disabled={loading}>
            {loading ? "Verifying..." : "Run Verification"}
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      <div className="overall-state" style={{ borderColor: getStateColor(result.overall_state) }}>
        <span className="state-badge" style={{ backgroundColor: getStateColor(result.overall_state) }}>
          {getStateLabel(result.overall_state)}
        </span>
        <span className="summary">{result.summary}</span>
      </div>

      <div className="platforms-grid">
        {result.platforms.map((platform: PlatformVerificationResult) => (
          <div
            key={platform.platform}
            className="platform-card"
            style={{ borderColor: getStateColor(platform.state) }}
          >
            <div className="platform-header">
              <span className="platform-name">{platform.platform.toUpperCase()}</span>
              <span
                className="state-badge"
                style={{ backgroundColor: getStateColor(platform.state) }}
              >
                {getStateLabel(platform.state)}
              </span>
            </div>

            <div className="platform-metrics">
              <div className="metric">
                <span className="metric-label">Total Entries</span>
                <span className="metric-value">{platform.entries_total}</span>
              </div>
              <div className="metric">
                <span className="metric-label">Verified</span>
                <span className="metric-value" style={{ color: "var(--color-success)" }}>
                  {platform.entries_verified}
                </span>
              </div>
              <div className="metric">
                <span className="metric-label">Missing</span>
                <span className="metric-value" style={{ color: "var(--color-warning)" }}>
                  {platform.entries_missing}
                </span>
              </div>
              <div className="metric">
                <span className="metric-label">Mismatch</span>
                <span className="metric-value" style={{ color: "var(--color-error)" }}>
                  {platform.entries_mismatch}
                </span>
              </div>
            </div>

            {platform.witness_stamp_valid !== null && (
              <div className="witness-stamp">
                <span className="metric-label">Witness Stamp</span>
                <span
                  className="metric-value"
                  style={{
                    color: platform.witness_stamp_valid
                      ? "var(--color-success)"
                      : "var(--color-error)",
                  }}
                >
                  {platform.witness_stamp_valid ? "Valid" : "Invalid"}
                </span>
                {platform.witness_stamp_detail && (
                  <details className="witness-detail">
                    <summary>Detail</summary>
                    <pre>{platform.witness_stamp_detail}</pre>
                  </details>
                )}
              </div>
            )}

            <details className="artifacts-detail">
              <summary>Artifact Details ({platform.results.length})</summary>
              <table className="artifacts-table">
                <thead>
                  <tr>
                    <th>Artifact Path</th>
                    <th>Expected SHA256</th>
                    <th>Actual SHA256</th>
                    <th>Exists</th>
                    <th>Match</th>
                  </tr>
                </thead>
                <tbody>
                  {platform.results.map((artifact: ArtifactVerificationResult, idx: number) => (
                    <tr key={idx}>
                      <td>{artifact.artifact_path}</td>
                      <td>
                        <code>{artifact.expected_sha256.slice(0, 16)}…</code>
                      </td>
                      <td>
                        <code>
                          {artifact.actual_sha256
                            ? artifact.actual_sha256.slice(0, 16) + "…"
                            : "—"}
                        </code>
                      </td>
                      <td>{artifact.exists ? "✓" : "✗"}</td>
                      <td>
                        {artifact.match === true ? (
                          <span style={{ color: "var(--color-success)" }}>✓</span>
                        ) : artifact.match === false ? (
                          <span style={{ color: "var(--color-error)" }}>✗</span>
                        ) : (
                          <span style={{ color: "var(--color-text-muted)" }}>—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          </div>
        ))}
      </div>
    </div>
  );
};