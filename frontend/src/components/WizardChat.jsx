import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "../api";
import "./WizardChat.css";
import FinalReport from "./FinalReport";
import RoleResults from "./RoleResults";

export default function WizardChat({
  onEvaluationsComplete,
  onSaveEvaluation,
}) {
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: "bot",
      content:
        "Hi! I'm your Creative Effectiveness AI. To get started, please upload the creative asset(s) or brief you'd like to analyze.",
      type: "upload_initial",
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const messagesEndRef = useRef(null);

  // State machine variables
  const [step, setStep] = useState("INITIAL_UPLOAD"); // INITIAL_UPLOAD, CLARIFY_GAPS, UPLOAD_PLATFORMS, EVALUATING, COMPARE, RECOMMEND
  const [extractedContext, setExtractedContext] = useState(null);
  const [clarifyingQuestions, setClarifyingQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [qaPairs, setQaPairs] = useState([]);
  const [finalContext, setFinalContext] = useState(null);

  // File collection
  const [initialFiles, setInitialFiles] = useState([]);

  // Evaluations state
  const [evaluations, setEvaluations] = useState([]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const addBotMessage = (content, type = "text", extra = null) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now() + Math.random().toString(36).substr(2, 9),
        role: "bot",
        content,
        type,
        extra,
      },
    ]);
  };

  const addUserMessage = (content, type = "text", extra = null) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now() + Math.random().toString(36).substr(2, 9),
        role: "user",
        content,
        type,
        extra,
      },
    ]);
  };

  // ----- Step 1: Initial Upload -----
  const handleInitialUpload = async (e) => {
    const files = e.target.files
      ? Array.from(e.target.files)
      : Array.from(e.dataTransfer.files);
    if (!files || !files.length) return;

    setInitialFiles(files);
    addUserMessage(`Uploaded ${files.length} asset(s)`, "text");
    setIsLoading(true);
    setIsDragging(false);

    try {
      addBotMessage(
        "Analyzing your asset(s) to establish the Contextual Baseline...",
        "loading",
      );
      const result = await api.analyzeContext(files);

      // Remove loading message
      setMessages((prev) => prev.filter((m) => m.type !== "loading"));

      if (result.error) throw new Error(result.error);

      setExtractedContext(result.extracted_context);

      if (
        result.clarifying_questions &&
        result.clarifying_questions.length > 0
      ) {
        setClarifyingQuestions(result.clarifying_questions);
        setStep("CLARIFY_GAPS");
        addBotMessage(
          "I extracted some initial context, but there are a few gaps I need to fill before we can confidently evaluate the creative. " +
            result.clarifying_questions[0],
        );
      } else {
        // No gaps
        proceedToPlatformInput(result.extracted_context);
      }
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.type !== "loading"));
      addBotMessage(`Error analyzing upload: ${err.message}`, "error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (step === "INITIAL_UPLOAD" && !isLoading) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (step === "INITIAL_UPLOAD" && !isLoading) {
      handleInitialUpload(e);
    }
  };

  // ----- Step 2: Clarifying Gaps -----
  const handleClarifyAnswer = async (answer) => {
    addUserMessage(answer);

    const question = clarifyingQuestions[currentQuestionIndex];
    const newQaPairs = [...qaPairs, { question, answer }];
    setQaPairs(newQaPairs);

    if (currentQuestionIndex + 1 < clarifyingQuestions.length) {
      const nextIndex = currentQuestionIndex + 1;
      setCurrentQuestionIndex(nextIndex);
      setTimeout(() => addBotMessage(clarifyingQuestions[nextIndex]), 500);
    } else {
      // Done asking questions, synthesize the final baseline
      setIsLoading(true);
      setStep("SYNTHESIZING");
      addBotMessage(
        "Thank you! Compiling the final Evaluation Baseline...",
        "loading",
      );

      try {
        const finalCtx = await api.clarifyBrief(extractedContext, newQaPairs);
        setMessages((prev) => prev.filter((m) => m.type !== "loading"));

        if (finalCtx.error) throw new Error(finalCtx.error);
        proceedToPlatformInput(finalCtx);
      } catch (err) {
        setMessages((prev) => prev.filter((m) => m.type !== "loading"));
        addBotMessage(`Error synthesizing brief: ${err.message}`, "error");
      } finally {
        setIsLoading(false);
      }
    }
  };

  const proceedToPlatformInput = (fullContext) => {
    setFinalContext(fullContext);
    setStep("GET_PLATFORM");
    addBotMessage(
      "Awesome. Our Contextual Baseline is locked. What platform(s) is this creative intended to run on? (e.g. Meta, TikTok, YouTube)",
    );
  };

  // ----- Step 3: Extract Platforms -----
  const handlePlatformSubmit = async (text) => {
    addUserMessage(text);
    const platform = text || "Generic Platform";

    // Begin evaluation using the files uploaded in step 1
    startEvaluations({ [platform]: initialFiles });
  };

  // ----- Step 4: Run Evaluations -----
  const startEvaluations = async (allCreatives) => {
    setStep("EVALUATING");
    addBotMessage(
      "All creatives received! The LLM Council is deliberating in parallel. This will take 1-2 minutes...",
      "loading",
    );
    setIsLoading(true);

    try {
      const results = [];
      const platforms = Object.keys(allCreatives);

      for (const platform of platforms) {
        // Evaluate each platform sequentially for simplicity here,
        // passing files as base64 or upload to Vercel string in real app
        // Here we simulate concurrent evaluations if backend supported it,
        // but backend expects 'creative.file_path' and 'creative.file_content' as b64 currently.
        // For a true implementation, we read file to b64.
        const file = allCreatives[platform][0]; // Take first file
        const fileB64 = await toBase64(file);

        const evalInput = {
          brand_name: finalContext.brand_name || "Unknown Brand",
          category: finalContext.category || "Unknown Category",
          campaign_objective: finalContext.campaign_objective || "Mixed",
          primary_channels: [platform],
          target_audience:
            finalContext.target_audience ||
            "General Audience, reaching out to everyday people looking for a better solution in their daily lives to ensure wide market reach and adoption over time.",
          brand_status: finalContext.brand_status || "Emerging / Growth Brand",
          market_context: finalContext.market_context || {
            market_maturity: "Mature",
            category_clutter: "Medium",
            purchase_frequency: "Medium",
            decision_involvement: "Medium",
          },
          creative: {
            description: `Visual reference creative ad for ${platform}. Please execute full multimodal evaluation.`,
            file_path: file.name,
            file_name: file.name,
            file_content: fileB64.split(",")[1],
            file_type: file.type,
          },
        };

        const result = await api.runEvaluation(evalInput);
        results.push({ platform, result });

        // Save the generated evaluation to the sidebar
        if (onSaveEvaluation) {
          // MINIMIZE STORAGE: Strip the heavy base64 file content from the saved data
          // so we don't hit the 5MB localStorage quota
          const savedInput = {
            ...evalInput,
            creative: { ...evalInput.creative, file_content: "[STRIPPED]" },
          };
          onSaveEvaluation(savedInput, result);
        }
      }

      setMessages((prev) => prev.filter((m) => m.type !== "loading"));
      setEvaluations(results);

      // Add a message with the results
      addBotMessage("Evaluation complete!", "evaluation_results", { results });

      setStep("POST_EVAL");
      setTimeout(
        () =>
          addBotMessage(
            "Would you like me to generate a head-to-head comparison table across all criteria? (Yes/No)",
          ),
        1000,
      );
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.type !== "loading"));
      addBotMessage(`Evaluation Error: ${err.message}`, "error");
    } finally {
      setIsLoading(false);
    }
  };

  const toBase64 = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result);
      reader.onerror = (error) => reject(error);
    });

  // ----- Step 5 & 6: Compare & Recommend -----
  const handlePostEvalResponse = async (text) => {
    addUserMessage(text);
    const isYes =
      text.toLowerCase().includes("yes") || text.toLowerCase().includes("yep");

    if (step === "POST_EVAL") {
      if (isYes) {
        setIsLoading(true);
        addBotMessage("Generating head-to-head comparison...", "loading");
        try {
          // Pass the evaluations array
          const cleanEvals = evaluations.map((e) => ({
            platform: e.platform,
            final_effectiveness_index: e.result.final_effectiveness_index,
            final_report: e.result.final_report,
            role_evaluations: e.result.role_evaluations,
          }));
          const res = await api.compareCreatives(cleanEvals);
          setMessages((prev) => prev.filter((m) => m.type !== "loading"));
          addBotMessage(res.comparison_markdown, "markdown");

          setStep("ASK_RECOMMENDATIONS");
          setTimeout(
            () =>
              addBotMessage(
                "Would you like actionable recommendations to make these creatives stronger before launch?",
              ),
            1000,
          );
        } catch (err) {
          setMessages((prev) => prev.filter((m) => m.type !== "loading"));
          addBotMessage(`Error: ${err.message}`, "error");
        } finally {
          setIsLoading(false);
        }
      } else {
        setStep("ASK_RECOMMENDATIONS");
        setTimeout(
          () =>
            addBotMessage(
              "Alright! Would you like actionable recommendations to make these creatives stronger before launch?",
            ),
          1000,
        );
      }
    } else if (step === "ASK_RECOMMENDATIONS") {
      if (isYes) {
        setIsLoading(true);
        addBotMessage("Generating recommendations...", "loading");
        try {
          const cleanEvals = evaluations.map((e) => ({
            platform: e.platform,
            final_effectiveness_index: e.result.final_effectiveness_index,
            role_evaluations: e.result.role_evaluations,
          }));
          const res = await api.getRecommendations(cleanEvals);
          setMessages((prev) => prev.filter((m) => m.type !== "loading"));
          addBotMessage(res.recommendations_markdown, "markdown");

          setStep("DONE");
          setTimeout(
            () =>
              addBotMessage(
                "All done! If you have further assets or campaigns to evaluate, let me know or start a new session.",
              ),
            1000,
          );
        } catch (err) {
          setMessages((prev) => prev.filter((m) => m.type !== "loading"));
          addBotMessage(`Error: ${err.message}`, "error");
        } finally {
          setIsLoading(false);
        }
      } else {
        setStep("DONE");
        addBotMessage("All done! Let me know if you need anything else.");
      }
    }
  };

  const handleInputSubmit = (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const text = inputValue;
    setInputValue("");

    if (step === "CLARIFY_GAPS") {
      handleClarifyAnswer(text);
    } else if (step === "GET_PLATFORM") {
      handlePlatformSubmit(text);
    } else if (step === "POST_EVAL" || step === "ASK_RECOMMENDATIONS") {
      handlePostEvalResponse(text);
    } else {
      // Generic chat or DONE state
      addUserMessage(text);
      setTimeout(
        () =>
          addBotMessage(
            "The evaluation workflow is complete. Please start a new session for another campaign.",
          ),
        500,
      );
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleInputSubmit(e);
    }
  };

  return (
    <div className="wizard-chat-container">
      <div className="chat-messages">
        {step === "INITIAL_UPLOAD" ? (
          <div
            className={`initial-upload-hero ${isDragging ? "dragging" : ""}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="hero-content">
              <div className="hero-icon">📁</div>
              <h2>Welcome to Creative Effectiveness AI</h2>
              <p>
                Drag and drop your creative ad assets (video/image) or a brief
                anywhere here, or use the button below.
              </p>

              <label className="hero-upload-button">
                <input
                  type="file"
                  onChange={handleInitialUpload}
                  multiple
                  accept="video/*,image/*,.pdf,.doc,.docx"
                  disabled={isLoading}
                />
                {isLoading ? "Analyzing..." : "Get Started - Upload Assets"}
              </label>

              {isLoading && (
                <div className="hero-loading">
                  <div className="spinner-small"></div>
                  <span>Council is establishing Contextual Baseline...</span>
                </div>
              )}
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <div key={msg.id} className={`message-bubble ${msg.role}`}>
                <div className="message-content">
                  {msg.type === "text" && <p>{msg.content}</p>}

                  {msg.type === "markdown" && (
                    <div className="markdown-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  )}

                  {
                    msg.type === "upload_initial" &&
                      null /* Handled by hero now */
                  }

                  {msg.type === "upload_platform" && (
                    <div className="upload-prompt">
                      <p>{msg.content}</p>
                      <label className="upload-button blue-btn">
                        <input
                          type="file"
                          onChange={(e) =>
                            handlePlatformUpload(e, msg.extra.platform)
                          }
                          multiple
                          accept="video/*,image/*"
                          disabled={isLoading}
                        />
                        Upload for {msg.extra.platform}
                      </label>
                    </div>
                  )}

                  {msg.type === "loading" && (
                    <div className="loading-state">
                      <div className="spinner-small"></div>
                      <span>{msg.content}</span>
                    </div>
                  )}

                  {msg.type === "error" && (
                    <div className="error-state">
                      <p>{msg.content}</p>
                    </div>
                  )}

                  {msg.type === "evaluation_results" && msg.extra?.results && (
                    <div className="evaluation-results-stack">
                      {msg.extra.results.map((r, i) => (
                        <div key={i} className="eval-platform-detailed">
                          <h3 className="platform-title">
                            Platform: {r.platform}
                          </h3>

                          <FinalReport
                            report={r.result.final_report}
                            fei={r.result.final_effectiveness_index}
                            hardGateFailed={r.result.hard_gate_failed}
                            failedRole={r.result.failed_hard_gate_role}
                          />

                          <div className="role-results-wrapper">
                            <h4>LLM Council Deliberation</h4>
                            <p className="deliberation-subtext">
                              See the exact reasoning and layer scores from the
                              8 specialist AI models.
                            </p>
                            <RoleResults
                              roleEvaluations={r.result.role_evaluations}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input-area" onSubmit={handleInputSubmit}>
        <textarea
          placeholder="Type your answer here..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={
            isLoading ||
            step === "INITIAL_UPLOAD" ||
            step.includes("UPLOAD_CREATIVES")
          }
          rows={2}
        />
        <button
          type="submit"
          disabled={!inputValue.trim() || isLoading}
          className="send-btn"
        >
          Send
        </button>
      </form>
    </div>
  );
}
