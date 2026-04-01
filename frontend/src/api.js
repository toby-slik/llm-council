import { upload } from "@vercel/blob/client";

/**
 * API client for the Creative Effectiveness Evaluation backend.
 */

// Use current origin in production, or localhost:8001 in development
const API_BASE =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1"
    ? "http://localhost:8001"
    : "";

export const api = {
  /**
   * Health check and get backend info.
   */
  async getHealth() {
    const response = await fetch(`${API_BASE}/api/creative/config`);
    if (!response.ok) {
      throw new Error("Backend not available");
    }
    return response.json();
  },

  async getUserStatus(token) {
    const response = await fetch(`${API_BASE}/api/user/status`, {
      headers: { ...(token ? { "Authorization": `Bearer ${token}` } : {}) }
    });
    if (!response.ok) throw new Error("Failed to get user status");
    return response.json();
  },

  async createCheckout(token) {
    const response = await fetch(`${API_BASE}/api/stripe/checkout`, {
      method: "POST",
      headers: { ...(token ? { "Authorization": `Bearer ${token}` } : {}) }
    });
    if (!response.ok) throw new Error("Failed to create checkout");
    return response.json();
  },

  /**
   * Get evaluation configuration (roles, backend info).
   */
  async getConfig() {
    const response = await fetch(`${API_BASE}/api/creative/config`);
    if (!response.ok) {
      throw new Error("Failed to get config");
    }
    return response.json();
  },

  /**
   * Validate input before running evaluation.
   * @param {Object} data - Partial or complete evaluation input
   * @returns {Promise<{valid: boolean, missing_fields: string[], incomplete_fields: string[], warnings: string[], ready_to_evaluate: boolean, document_stats: Object}>}
   */
  async validateInput(data) {
    const response = await fetch(`${API_BASE}/api/creative/validate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error("Validation request failed");
    }
    return response.json();
  },

  /**
   * Upload file to Vercel Blob using client-side SDK.
   * @param {File} file
   */
  async uploadToStorage(file) {
    try {
      const newBlob = await upload(file.name, file, {
        access: "public",
        handleUploadUrl: "/api/creative/upload/token", // Route to our Node.js helper
      });
      return newBlob.url;
    } catch (error) {
      console.error("Blob upload failed:", error);
      throw new Error("Failed to upload file to storage.");
    }
  },

  /**
   * Auto-extract structured data from document.
   * @param {string|null} fileContent - Base64 encoded file content (optional if fileUrl provided)
   * @param {string} fileName - Name of file
   * @param {string|null} fileUrl - URL to file in storage (optional if fileContent provided)
   * @returns {Promise<Object>} - Extracted fields
   */
  async extractInput(fileContent, fileName, fileUrl = null) {
    const body = {
      file_name: fileName,
      file_url: fileUrl || null,
      file_content: fileContent || null,
    };

    const response = await fetch(`${API_BASE}/api/creative/extract`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const errorText = await response.text();
      try {
        const errorJson = JSON.parse(errorText);
        throw new Error(errorJson.detail || "Extraction failed");
      } catch (e) {
        throw new Error(
          `Extraction failed: ${response.status} ${response.statusText}`,
        );
      }
    }
    return response.json();
  },

  /**
   * Run full creative effectiveness evaluation.
   * @param {Object} data - Complete evaluation input
   * @returns {Promise<Object>} - Evaluation result
   */
  async runEvaluation(data) {
    const response = await fetch(`${API_BASE}/api/creative/evaluate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      let errMsg = errorData.detail?.message || "Evaluation failed";
      if (errorData.detail?.missing_fields?.length)
        errMsg += ` - Missing: ${errorData.detail.missing_fields.join(", ")}`;
      if (errorData.detail?.incomplete_fields?.length)
        errMsg += ` - Incomplete: ${errorData.detail.incomplete_fields.join(", ")}`;

      // Also handle default pydantic validation errors (array of errors inside detail)
      if (Array.isArray(errorData.detail)) {
        errMsg = errorData.detail
          .map((e) => `${e.loc?.join(".")}: ${e.msg}`)
          .join(" | ");
      }

      throw new Error(errMsg);
    }
    return response.json();
  },

  /**
   * Run evaluation with streaming progress updates.
   * @param {Object} data - Complete evaluation input
   * @param {function} onEvent - Callback: (eventType, eventData) => void
   * @param {string} token - Auth Token
   * @returns {Promise<void>}
   */
  async runEvaluationStream(data, onEvent, token) {
    const response = await fetch(`${API_BASE}/api/creative/evaluate/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "Authorization": `Bearer ${token}` } : {})
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail?.message || "Evaluation failed");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by double newlines
      const parts = buffer.split("\n\n");
      // Keep the last part in the buffer (it might be incomplete)
      buffer = parts.pop();

      for (const part of parts) {
        if (!part.trim()) continue;

        // A single SSE message can have multiple data: lines
        const lines = part.split("\n");
        let eventData = "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            eventData += line.slice(6);
          }
        }

        if (eventData) {
          try {
            const event = JSON.parse(eventData);
            onEvent(event.type, event);
          } catch (e) {
            console.error("Failed to parse SSE event data:", eventData, e);
          }
        }
      }
    }
  },

  /**
   * Analyze uploaded creatives (video, image, document) to extract context baseline.
   * @param {File[]} files - Array of files to upload.
   * @returns {Promise<Object>} - Extracted context and missing gaps
   */
  async analyzeContext(files) {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    const response = await fetch(`${API_BASE}/api/creative/analyze-context`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.error || `Analysis failed: ${response.statusText}`,
      );
    }
    return response.json();
  },

  /**
   * Compiles gaps + user answers into structured brief.
   * @param {Object} extractedContext - The originally extracted context.
   * @param {Array<{question: string, answer: string}>} qaPairs - User's answers.
   */
  async clarifyBrief(extractedContext, qaPairs) {
    const response = await fetch(`${API_BASE}/api/creative/clarify-brief`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        extracted_context: extractedContext,
        qa_pairs: qaPairs,
      }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || "Clarification failed");
    }
    return response.json();
  },

  /**
   * Get head-to-head comparison
   * @param {Array<Object>} evaluations - Array of evaluation results
   */
  async compareCreatives(evaluations) {
    const response = await fetch(`${API_BASE}/api/creative/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ evaluations }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || "Comparison failed");
    }
    return response.json();
  },

  /**
   * Get recommendations
   * @param {Array<Object>} evaluations - Array of evaluation results
   */
  async getRecommendations(evaluations) {
    const response = await fetch(`${API_BASE}/api/creative/recommendations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ evaluations }),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || "Recommendations request failed");
    }
    return response.json();
  },

  /**
   * Generic chat with the AI about evaluations.
   * @param {Object} data - { messages: [{role, content}], evaluations: [...] }
   * @returns {Promise<Object>} - { reply: "..." }
   */
  async chat(data) {
    const response = await fetch(`${API_BASE}/api/creative/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || "Chat request failed");
    }
    return response.json();
  },
};
