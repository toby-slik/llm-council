/**
 * API client for the Creative Effectiveness Evaluation backend.
 */

const API_BASE = "http://localhost:8001";

export const api = {
  /**
   * Health check and get backend info.
   */
  async getHealth() {
    const response = await fetch(`${API_BASE}/`);
    if (!response.ok) {
      throw new Error("Backend not available");
    }
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
   * @returns {Promise<{valid: boolean, missing_fields: string[], incomplete_fields: string[], warnings: string[], ready_to_evaluate: boolean}>}
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
      throw new Error(errorData.detail?.message || "Evaluation failed");
    }
    return response.json();
  },

  /**
   * Run evaluation with streaming progress updates.
   * @param {Object} data - Complete evaluation input
   * @param {function} onEvent - Callback: (eventType, eventData) => void
   * @returns {Promise<void>}
   */
  async runEvaluationStream(data, onEvent) {
    const response = await fetch(`${API_BASE}/api/creative/evaluate/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail?.message || "Evaluation failed");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split("\n");

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error("Failed to parse SSE event:", e);
          }
        }
      }
    }
  },
};
