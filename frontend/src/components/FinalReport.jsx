import "./FinalReport.css";

export default function FinalReport({
  report,
  fei,
  hardGateFailed,
  failedRole,
}) {
  if (!report) return null;

  const getVerdictClass = (verdict) => {
    if (verdict === "RECOMMEND") return "recommend";
    if (verdict === "REVISE BEFORE RECOMMENDATION") return "revise";
    return "not-recommend";
  };

  return (
    <div className={`final-report ${getVerdictClass(report.verdict)}`}>
      <div className="report-header">
        <h2>Final Report</h2>
        <div className="fei-score">
          <span className="fei-label">Effectiveness Index</span>
          <span className="fei-value">{fei.toFixed(1)}</span>
        </div>
      </div>

      {hardGateFailed && (
        <div className="hard-gate-failed">
          <strong>⛔ HARD GATE FAILED</strong>
          <p>Evaluation stopped early due to failure in: {failedRole}</p>
        </div>
      )}

      <div className="verdict-section">
        <div className={`verdict-badge ${getVerdictClass(report.verdict)}`}>
          {report.verdict}
        </div>
        <div className="confidence-badge">
          Confidence: {report.confidence_level}
        </div>
      </div>

      <div className="report-grid">
        <div className="report-column">
          <h3>✓ Top Strengths</h3>
          <ul className="strengths-list">
            {report.top_strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>

        <div className="report-column">
          <h3>⚠ Top Risks</h3>
          <ul className="risks-list">
            {report.top_risks.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="report-footer">
        <div className="commercial-role">
          <strong>Predicted Commercial Role:</strong>{" "}
          {report.predicted_commercial_role}
        </div>

        {report.revision_guidance && (
          <div className="revision-guidance">
            <strong>Revision Guidance:</strong>
            <p>{report.revision_guidance}</p>
          </div>
        )}
      </div>
    </div>
  );
}
