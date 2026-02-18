import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import "./App.css";
import EvaluationForm from "./components/EvaluationForm";
import FinalReport from "./components/FinalReport";
import RoleResults from "./components/RoleResults";
import Sidebar from "./components/Sidebar";

function App() {
  // Evaluation history (persisted in localStorage)
  const [evaluations, setEvaluations] = useState([]);
  const [currentEvaluationId, setCurrentEvaluationId] = useState(null);
  const [currentEvaluation, setCurrentEvaluation] = useState(null);

  const [backendInfo, setBackendInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [progress, setProgress] = useState({ current: 0, total: 8 });
  const [currentRoles, setCurrentRoles] = useState([]);
  const [error, setError] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const timerRef = useRef(null);

  // Load evaluations from localStorage on mount
  useEffect(() => {
    checkBackend();
    loadEvaluations();
  }, []);

  // Load evaluation when selected
  useEffect(() => {
    if (currentEvaluationId) {
      const eval_ = evaluations.find((e) => e.id === currentEvaluationId);
      if (eval_) {
        setCurrentEvaluation(eval_);
        setEvaluationResult(eval_.result);
      }
    }
  }, [currentEvaluationId, evaluations]);

  const checkBackend = async () => {
    try {
      const info = await api.getHealth();
      setBackendInfo(info);
    } catch (err) {
      setError("Backend not available. Please start the server.");
    }
  };

  const loadEvaluations = () => {
    try {
      const stored = localStorage.getItem("creative_evaluations");
      if (stored) {
        setEvaluations(JSON.parse(stored));
      }
    } catch (e) {
      console.error("Failed to load evaluations:", e);
    }
  };

  const saveEvaluation = (formData, result) => {
    const evaluation = {
      id: Date.now().toString(),
      created_at: new Date().toISOString(),
      title: `${formData.brand_name} - ${formData.category}`,
      formData,
      result,
    };

    const updated = [evaluation, ...evaluations];
    setEvaluations(updated);
    localStorage.setItem("creative_evaluations", JSON.stringify(updated));
    setCurrentEvaluationId(evaluation.id);
    return evaluation;
  };

  const handleSubmit = async (formData) => {
    setIsLoading(true);
    setError(null);
    setEvaluationResult(null);
    setProgress({ current: 0, total: 8 });
    setCurrentRoles([]);
    setElapsedSeconds(0);

    // Start a local timer for immediate feedback
    if (timerRef.current) clearInterval(timerRef.current);
    const startTime = Date.now();
    timerRef.current = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
    }, 1000);

    try {
      await api.runEvaluationStream(formData, (eventType, event) => {
        switch (eventType) {
          case "start":
            setProgress({ current: 0, total: event.total_roles });
            break;

          case "role_update":
            setCurrentRoles((prev) => {
              const idx = prev.findIndex((r) => r.role_name === event.role.role_name);
              if (idx >= 0) {
                const updated = [...prev];
                updated[idx] = { ...updated[idx], ...event.role };
                return updated;
              }
              return [...prev, event.role];
            });
            break;

          case "role_complete":
            setProgress((prev) => ({ ...prev, current: event.progress }));
            setCurrentRoles((prev) => {
              const idx = prev.findIndex((r) => r.role_name === event.role.role_name);
              if (idx >= 0) {
                const updated = [...prev];
                updated[idx] = { ...updated[idx], ...event.role };
                return updated;
              }
              return [...prev, event.role];
            });
            break;

          case "hard_gate_failed":
            setError(`HARD GATE FAILED: ${event.role}`);
            break;

          case "heartbeat":
            // Connection is alive - server confirmed elapsed time
            break;

          case "complete":
            setEvaluationResult(event.result);
            saveEvaluation(formData, event.result);
            setIsLoading(false);
            if (timerRef.current) clearInterval(timerRef.current);
            break;

          case "error":
            setError(event.message);
            setIsLoading(false);
            if (timerRef.current) clearInterval(timerRef.current);
            break;

          default:
            console.log("Unknown event:", eventType, event);
        }
      });
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  };

  const handleNewEvaluation = () => {
    setCurrentEvaluationId(null);
    setCurrentEvaluation(null);
    setEvaluationResult(null);
    setError(null);
    setProgress({ current: 0, total: 8 });
  };

  const handleSelectEvaluation = (id) => {
    setCurrentEvaluationId(id);
  };

  const deleteEvaluation = (id) => {
    const updated = evaluations.filter((ev) => ev.id !== id);
    setEvaluations(updated);
    localStorage.setItem("creative_evaluations", JSON.stringify(updated));

    if (currentEvaluationId === id) {
      handleNewEvaluation();
    }
  };

  // Convert evaluations to sidebar format
  const sidebarItems = evaluations.map((e) => ({
    id: e.id,
    title: e.title,
    message_count: e.result?.role_evaluations?.length || 0,
  }));

  return (
    <div className="app">
      <Sidebar
        conversations={sidebarItems}
        currentConversationId={currentEvaluationId}
        onSelectConversation={handleSelectEvaluation}
        onNewConversation={handleNewEvaluation}
        onDeleteConversation={deleteEvaluation}
      />

      <div className="app-content">
        <header className="app-header">
          <h1>SLIK Creative Effectiveness</h1>
          {backendInfo && (
            <span className="backend-info">{backendInfo.llm_backend}</span>
          )}
        </header>

        <main className="app-main">
          {error && (
            <div className="error-banner">
              <strong>Error:</strong> {error}
              <button onClick={() => setError(null)}>×</button>
            </div>
          )}

          {!evaluationResult ? (
            <>
              {/* Evaluation Form */}
              <EvaluationForm onSubmit={handleSubmit} isLoading={isLoading} />

              {/* Loading Progress */}
              {isLoading && (
                <div className="loading-overlay">
                  <div className="loading-content expanded">
                    <div className="loading-header">
                      <div className="loading-spinner small"></div>
                      <div>
                        <h3>Council is Deliberating...</h3>
                        <p className="progress-text">
                          {progress.current} of {progress.total} specialists finalized
                          <span className="elapsed-timer"> · {Math.floor(elapsedSeconds / 60)}:{String(elapsedSeconds % 60).padStart(2, '0')} elapsed</span>
                        </p>
                      </div>
                    </div>

                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{
                          width: `${(progress.current / progress.total) * 100}%`,
                        }}
                      ></div>
                    </div>
                    
                    {currentRoles.length === 0 && (
                      <div className="waiting-for-roles">
                        <p>🔄 Initializing specialist roles and building evaluation framework...</p>
                      </div>
                    )}

                    <div className="specialist-grid">
                      {currentRoles.map((role, i) => (
                        <div key={i} className={`specialist-status-card ${role.status}`}>
                          <div className="card-header">
                            <span className="role-name">{role.role_name}</span>
                            <span className={`status-tag ${role.status}`}>
                              {role.status === 'processing' ? '⚡ Working' : 
                               role.status === 'complete' ? '✓ Done' : '⏳ Queued'}
                            </span>
                          </div>
                          {role.status === 'complete' ? (
                            <div className="card-result">
                              <span className={`verdict ${role.result.toLowerCase()}`}>{role.result}</span>
                              <span className="score">Score: {role.score}/10</span>
                              <span className="confidence">({Math.round(role.confidence * 100)}% conf.)</span>
                            </div>
                          ) : role.status === 'processing' ? (
                            <div className="thinking-indicator">
                              <div className="thinking-dots">
                                <span></span><span></span><span></span>
                              </div>
                            </div>
                          ) : null}
                          <p className="status-note">{role.justification}</p>
                        </div>
                      ))}
                    </div>

                    <p className="warning-text">
                      ⚡ Specialist roles evaluate in parallel. This typically takes 30-90 seconds depending on LLM response times.
                    </p>
                  </div>
                </div>
              )}
            </>
          ) : (
            <>
              {/* Results View */}
              <div className="results-header">
                <h2>Evaluation Complete</h2>
                <button
                  className="new-eval-button"
                  onClick={handleNewEvaluation}
                >
                  New Evaluation
                </button>
              </div>

              <FinalReport
                report={evaluationResult.final_report}
                fei={evaluationResult.final_effectiveness_index}
                hardGateFailed={evaluationResult.hard_gate_failed}
                failedRole={evaluationResult.failed_hard_gate_role}
              />

              <RoleResults
                roleEvaluations={evaluationResult.role_evaluations}
              />
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
