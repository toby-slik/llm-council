import { useState } from "react";
import "./RoleResults.css";

export default function RoleResults({ roleEvaluations, onSelectRole }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!roleEvaluations || roleEvaluations.length === 0) {
    return <div className="role-results-empty">No role evaluations yet</div>;
  }

  const activeRole = roleEvaluations[activeTab];

  return (
    <div className="role-results">
      <h3>Role Evaluations</h3>

      {/* Tab Navigation */}
      <div className="role-tabs">
        {roleEvaluations.map((role, index) => (
          <button
            key={role.role_id}
            className={`role-tab ${index === activeTab ? "active" : ""} ${
              role.is_hard_gate ? "hard-gate" : ""
            } ${role.result === "FAIL" ? "failed" : ""}`}
            onClick={() => setActiveTab(index)}
          >
            <span className="role-name">{role.role_name.split(" ")[0]}</span>
            <span className={`result-badge ${role.result.toLowerCase()}`}>
              {role.result}
            </span>
            {role.is_hard_gate && <span className="hard-gate-badge">GATE</span>}
          </button>
        ))}
      </div>

      {/* Active Role Details */}
      <div className="role-detail">
        <div className="role-header">
          <h4>{activeRole.role_name}</h4>
          <div className="role-meta">
            <span className={`result-large ${activeRole.result.toLowerCase()}`}>
              {activeRole.result}
            </span>
            {activeRole.score !== null && (
              <span className="score">
                Score: {activeRole.score.toFixed(1)}/10
              </span>
            )}
            <span className="confidence">
              Confidence: {(activeRole.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>

        {activeRole.is_hard_gate && (
          <div className="hard-gate-notice">
            ⚠️ HARD GATE: This role can stop the entire evaluation if it fails.
          </div>
        )}

        <div className="justification">
          <h5>Justification</h5>
          <p>{activeRole.justification}</p>
        </div>

        {activeRole.layer_scores && activeRole.layer_scores.length > 0 && (
          <div className="layer-scores">
            <h5>Layer Scores</h5>
            {activeRole.layer_scores.map((layer) => (
              <div key={layer.layer_id} className="layer-score-item">
                <div className="layer-header">
                  <span className="layer-id">Layer {layer.layer_id}</span>
                  <span className="layer-name">{layer.layer_name}</span>
                  <span
                    className={`layer-verdict ${layer.verdict.toLowerCase().replace(" ", "-")}`}
                  >
                    {layer.verdict}
                  </span>
                </div>
                {layer.fail_conditions.length > 0 && (
                  <div className="fail-conditions">
                    {layer.fail_conditions.map((fc, i) => (
                      <span key={i} className="fail-condition">
                        ⚠ {fc}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
