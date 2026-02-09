import { useEffect, useState } from "react";
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
  const [error, setError] = useState(null);

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

    try {
      await api.runEvaluationStream(formData, (eventType, event) => {
        switch (eventType) {
          case "start":
            setProgress({ current: 0, total: event.total_roles });
            break;

          case "role_complete":
            setProgress((prev) => ({ ...prev, current: event.progress }));
            break;

          case "hard_gate_failed":
            setError(`HARD GATE FAILED: ${event.role}`);
            break;

          case "complete":
            setEvaluationResult(event.result);
            saveEvaluation(formData, event.result);
            setIsLoading(false);
            break;

          case "error":
            setError(event.message);
            setIsLoading(false);
            break;

          default:
            console.log("Unknown event:", eventType);
        }
      });
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
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
                  <div className="loading-content">
                    <div className="loading-spinner"></div>
                    <h3>Evaluating Creative...</h3>
                    <p>
                      Role {progress.current} of {progress.total} complete
                    </p>
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{
                          width: `${(progress.current / progress.total) * 100}%`,
                        }}
                      ></div>
                    </div>
                    <p className="warning-text">
                      ⚠️ This may take several minutes as 8 specialist AI roles
                      evaluate your creative.
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
