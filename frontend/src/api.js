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
        access: 'public',
        handleUploadUrl: '/api/creative/upload/token', // Route to our Node.js helper
        addRandomSuffix: true, // Prevent "blob already exists" errors
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
      file_content: fileContent || null
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
        throw new Error(`Extraction failed: ${response.status} ${response.statusText}`);
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
};
