import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import "./EvaluationForm.css";

// Options for select fields
const BRAND_STATUS_OPTIONS = [
  { value: "Market Leader", label: "Market Leader" },
  { value: "Strong Challenger", label: "Strong Challenger" },
  { value: "Emerging / Growth Brand", label: "Emerging / Growth Brand" },
  { value: "New or Low-Awareness Brand", label: "New or Low-Awareness Brand" },
];

const MARKET_MATURITY_OPTIONS = [
  { value: "Mature", label: "Mature" },
  { value: "Growing", label: "Growing" },
  { value: "Emerging", label: "Emerging" },
];

const CLUTTER_OPTIONS = [
  { value: "Low", label: "Low" },
  { value: "Medium", label: "Medium" },
  { value: "High", label: "High" },
];

const FREQUENCY_OPTIONS = [
  { value: "High", label: "High" },
  { value: "Medium", label: "Medium" },
  { value: "Low", label: "Low" },
];

const INVOLVEMENT_OPTIONS = [
  { value: "Low", label: "Low" },
  { value: "Medium", label: "Medium" },
  { value: "High", label: "High" },
];

const OBJECTIVE_OPTIONS = [
  { value: "Long-term brand growth", label: "Long-term brand growth" },
  { value: "Short-term activation", label: "Short-term activation" },
  { value: "Mixed", label: "Mixed" },
];

const CHANNEL_OPTIONS = [
  "TV",
  "YouTube",
  "Social Media (Paid)",
  "Social Media (Organic)",
  "Display",
  "OOH/DOOH",
  "Radio",
  "Print",
  "Cinema",
  "Podcast",
];

export default function EvaluationForm({ onSubmit, isLoading }) {
  // File upload state
  const [uploadedFile, setUploadedFile] = useState(null);

  // Form state
  const [formData, setFormData] = useState({
    brand_name: "",
    category: "",
    campaign_objective: "",
    primary_channels: [],
    target_audience: "",
    brand_status: "",
    market_context: {
      market_maturity: "",
      category_clutter: "",
      purchase_frequency: "",
      decision_involvement: "",
    },
    creative: {
      description: "",
      file_path: null,
      file_type: null,
    },
    competitive_context: {
      competitor_themes: "",
      competitor_assets: "",
      competitive_noise: "Medium",
    },
  });

  // Validation state
  const [validation, setValidation] = useState(null);
  const [validating, setValidating] = useState(false);

  // Debounced validation
  const validateForm = useCallback(async () => {
    setValidating(true);
    try {
      const result = await api.validateInput(formData);
      setValidation(result);
    } catch (error) {
      console.error("Validation error:", error);
    }
    setValidating(false);
  }, [formData]);

  // Validate on form changes (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      validateForm();
    }, 500);
    return () => clearTimeout(timer);
  }, [formData, validateForm]);

  // Handle input changes
  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleNestedChange = (parent, field, value) => {
    setFormData((prev) => ({
      ...prev,
      [parent]: { ...prev[parent], [field]: value },
    }));
  };

  const handleChannelToggle = (channel) => {
    setFormData((prev) => {
      const channels = prev.primary_channels.includes(channel)
        ? prev.primary_channels.filter((c) => c !== channel)
        : [...prev.primary_channels, channel];
      return { ...prev, primary_channels: channels };
    });
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      setUploadedFile(file);
      // Update form data with file info
      setFormData((prev) => ({
        ...prev,
        creative: {
          ...prev.creative,
          file_path: file.name,
          file_type: file.type || "unknown",
        },
      }));
    }
  };

  const handleRemoveFile = () => {
    setUploadedFile(null);
    setFormData((prev) => ({
      ...prev,
      creative: {
        ...prev.creative,
        file_path: null,
        file_type: null,
      },
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (validation?.ready_to_evaluate) {
      onSubmit(formData, uploadedFile);
    }
  };

  // Field validation status helper
  const getFieldStatus = (field) => {
    if (!validation) return "neutral";
    if (validation.missing_fields.includes(field)) return "missing";
    if (validation.incomplete_fields.includes(field)) return "incomplete";
    return "valid";
  };

  const FieldIndicator = ({ field }) => {
    const status = getFieldStatus(field);
    return (
      <span className={`field-indicator ${status}`}>
        {status === "valid" && "✓"}
        {status === "missing" && "✗"}
        {status === "incomplete" && "⚠"}
      </span>
    );
  };

  return (
    <form className="evaluation-form" onSubmit={handleSubmit}>
      <h2>Creative Effectiveness Evaluation</h2>

      {/* Validation Summary */}
      {validation && !validation.ready_to_evaluate && (
        <div className="validation-summary">
          {validation.missing_fields.length > 0 && (
            <div className="validation-error">
              <strong>Missing:</strong> {validation.missing_fields.join(", ")}
            </div>
          )}
          {validation.warnings.length > 0 && (
            <div className="validation-warning">
              {validation.warnings.map((w, i) => (
                <p key={i}>⚠ {w}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Creative Asset Section */}
      <section className="form-section">
        <h3>
          Creative Asset <FieldIndicator field="creative" />
        </h3>

        {/* File Upload */}
        <div className="form-field">
          <label>
            Upload Creative File <span className="optional-tag">Optional</span>
          </label>
          <div className="file-upload-area">
            {uploadedFile ? (
              <div className="file-preview">
                <span className="file-icon">📄</span>
                <span className="file-name">{uploadedFile.name}</span>
                <span className="file-size">
                  ({(uploadedFile.size / 1024).toFixed(1)} KB)
                </span>
                <button
                  type="button"
                  className="remove-file-btn"
                  onClick={handleRemoveFile}
                >
                  ×
                </button>
              </div>
            ) : (
              <label className="file-upload-label">
                <input
                  type="file"
                  accept="image/*,video/*,application/pdf"
                  onChange={handleFileUpload}
                />
                <span className="upload-icon">📁</span>
                <span>Click to upload image, video, or PDF</span>
              </label>
            )}
          </div>
        </div>

        <div className="form-field">
          <label>Creative Description *</label>
          <textarea
            value={formData.creative.description}
            onChange={(e) =>
              handleNestedChange("creative", "description", e.target.value)
            }
            placeholder="Describe the creative in detail (minimum 100 characters). Include visual elements, messaging, tone, characters, narrative, and any distinctive features..."
            rows={6}
          />
          <span className="char-count">
            {formData.creative.description.length} / 100 min
          </span>
        </div>
      </section>

      {/* Brand Context Section */}
      <section className="form-section">
        <h3>Brand Context</h3>
        <div className="form-row">
          <div className="form-field">
            <label>
              Brand Name * <FieldIndicator field="brand_name" />
            </label>
            <input
              type="text"
              value={formData.brand_name}
              onChange={(e) => handleChange("brand_name", e.target.value)}
              placeholder="e.g., Nike"
            />
          </div>
          <div className="form-field">
            <label>
              Category * <FieldIndicator field="category" />
            </label>
            <input
              type="text"
              value={formData.category}
              onChange={(e) => handleChange("category", e.target.value)}
              placeholder="e.g., Athletic Footwear"
            />
          </div>
        </div>
        <div className="form-field">
          <label>
            Brand Status * <FieldIndicator field="brand_status" />
          </label>
          <select
            value={formData.brand_status}
            onChange={(e) => handleChange("brand_status", e.target.value)}
          >
            <option value="">Select brand status...</option>
            {BRAND_STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </section>

      {/* Campaign Details Section */}
      <section className="form-section">
        <h3>Campaign Details</h3>
        <div className="form-field">
          <label>
            Campaign Objective * <FieldIndicator field="campaign_objective" />
          </label>
          <select
            value={formData.campaign_objective}
            onChange={(e) => handleChange("campaign_objective", e.target.value)}
          >
            <option value="">Select objective...</option>
            {OBJECTIVE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label>
            Primary Channels * <FieldIndicator field="primary_channels" />
          </label>
          <div className="channel-grid">
            {CHANNEL_OPTIONS.map((channel) => (
              <label key={channel} className="channel-option">
                <input
                  type="checkbox"
                  checked={formData.primary_channels.includes(channel)}
                  onChange={() => handleChannelToggle(channel)}
                />
                {channel}
              </label>
            ))}
          </div>
        </div>
        <div className="form-field">
          <label>
            Target Audience * <FieldIndicator field="target_audience" />
          </label>
          <textarea
            value={formData.target_audience}
            onChange={(e) => handleChange("target_audience", e.target.value)}
            placeholder="Describe the target audience in detail (minimum 50 characters). Include demographics, psychographics, behaviours, and purchase triggers..."
            rows={3}
          />
          <span className="char-count">
            {formData.target_audience.length} / 50 min
          </span>
        </div>
      </section>

      {/* Market Context Section */}
      <section className="form-section">
        <h3>
          Market Context <FieldIndicator field="market_context" />
        </h3>
        <div className="form-row four-col">
          <div className="form-field">
            <label>Market Maturity *</label>
            <select
              value={formData.market_context.market_maturity}
              onChange={(e) =>
                handleNestedChange(
                  "market_context",
                  "market_maturity",
                  e.target.value,
                )
              }
            >
              <option value="">Select...</option>
              {MARKET_MATURITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div className="form-field">
            <label>Category Clutter *</label>
            <select
              value={formData.market_context.category_clutter}
              onChange={(e) =>
                handleNestedChange(
                  "market_context",
                  "category_clutter",
                  e.target.value,
                )
              }
            >
              <option value="">Select...</option>
              {CLUTTER_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div className="form-field">
            <label>Purchase Frequency *</label>
            <select
              value={formData.market_context.purchase_frequency}
              onChange={(e) =>
                handleNestedChange(
                  "market_context",
                  "purchase_frequency",
                  e.target.value,
                )
              }
            >
              <option value="">Select...</option>
              {FREQUENCY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div className="form-field">
            <label>Decision Involvement *</label>
            <select
              value={formData.market_context.decision_involvement}
              onChange={(e) =>
                handleNestedChange(
                  "market_context",
                  "decision_involvement",
                  e.target.value,
                )
              }
            >
              <option value="">Select...</option>
              {INVOLVEMENT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Competitive Context (Optional) */}
      <section className="form-section optional">
        <h3>
          Competitive Context <span className="optional-tag">Optional</span>
        </h3>
        <div className="form-field">
          <label>Competitor Messaging Themes</label>
          <textarea
            value={formData.competitive_context.competitor_themes}
            onChange={(e) =>
              handleNestedChange(
                "competitive_context",
                "competitor_themes",
                e.target.value,
              )
            }
            placeholder="What messaging themes are competitors currently using?"
            rows={2}
          />
        </div>
        <div className="form-field">
          <label>Distinctive Assets Owned by Competitors</label>
          <textarea
            value={formData.competitive_context.competitor_assets}
            onChange={(e) =>
              handleNestedChange(
                "competitive_context",
                "competitor_assets",
                e.target.value,
              )
            }
            placeholder="What distinctive brand assets do competitors own?"
            rows={2}
          />
        </div>
        <div className="form-field">
          <label>Competitive Noise Level</label>
          <select
            value={formData.competitive_context.competitive_noise}
            onChange={(e) =>
              handleNestedChange(
                "competitive_context",
                "competitive_noise",
                e.target.value,
              )
            }
          >
            {CLUTTER_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </section>

      {/* Submit Button */}
      <div className="form-actions">
        <button
          type="submit"
          className="submit-button"
          disabled={!validation?.ready_to_evaluate || isLoading}
        >
          {isLoading ? "Evaluating..." : "Run Evaluation"}
        </button>
        {validating && <span className="validating">Validating...</span>}
        {validation?.ready_to_evaluate && (
          <span className="ready-indicator">✓ Ready to evaluate</span>
        )}
      </div>
    </form>
  );
}
