"""Pydantic models for Creative Effectiveness Evaluation."""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================================
# Enums for structured choices
# ============================================================================

class BrandStatus(str, Enum):
    MARKET_LEADER = "Market Leader"
    STRONG_CHALLENGER = "Strong Challenger"
    EMERGING_GROWTH = "Emerging / Growth Brand"
    NEW_LOW_AWARENESS = "New or Low-Awareness Brand"


class MarketMaturity(str, Enum):
    MATURE = "Mature"
    GROWING = "Growing"
    EMERGING = "Emerging"


class ClutterLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class PurchaseFrequency(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class DecisionInvolvement(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class CampaignObjective(str, Enum):
    LONG_TERM_BRAND = "Long-term brand growth"
    SHORT_TERM_ACTIVATION = "Short-term activation"
    MIXED = "Mixed"


class CompetitiveNoise(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


# ============================================================================
# Input Models
# ============================================================================

class CreativeAsset(BaseModel):
    """Creative asset being evaluated."""
    description: str = Field(default="", description="Text description of the creative")
    file_path: Optional[str] = Field(default=None, description="Path to uploaded file")
    file_type: Optional[str] = Field(default=None, description="MIME type of file")


class MarketContext(BaseModel):
    """Market and category context."""
    market_maturity: MarketMaturity
    category_clutter: ClutterLevel
    purchase_frequency: PurchaseFrequency
    decision_involvement: DecisionInvolvement


class LocalFactors(BaseModel):
    """Local market factors."""
    cultural_notes: str = Field(default="", description="Cultural norms or sensitivities")
    media_behaviours: str = Field(default="", description="Market-specific media consumption")
    regulatory_constraints: str = Field(default="", description="Regulatory or category constraints")


class CompetitiveContext(BaseModel):
    """Competitive activity context."""
    competitor_themes: str = Field(default="", description="Dominant competitor messaging themes")
    competitor_assets: str = Field(default="", description="Distinctive assets owned by competitors")
    competitive_noise: CompetitiveNoise = Field(default=CompetitiveNoise.MEDIUM)


class EvaluationInput(BaseModel):
    """Complete input for creative effectiveness evaluation."""
    # Required fields
    creative: CreativeAsset
    brand_name: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    campaign_objective: CampaignObjective
    primary_channels: List[str] = Field(..., min_items=1)
    target_audience: str = Field(..., min_length=50)
    
    # Contextual classification
    brand_status: BrandStatus
    market_context: MarketContext
    
    # Optional context
    local_factors: Optional[LocalFactors] = None
    competitive_context: Optional[CompetitiveContext] = None
    existing_research: Optional[str] = Field(default=None, description="Any existing research or benchmarks")


class ContextualBaseline(BaseModel):
    """Locked contextual baseline - immutable once set."""
    brand_status: str
    market_maturity: str
    category_clutter: str
    purchase_frequency: str
    decision_involvement: str
    competitive_noise: str
    summary_bullets: List[str] = Field(..., max_items=5)


# ============================================================================
# Scoring Models
# ============================================================================

class LayerScore(BaseModel):
    """Score for a single evaluation layer."""
    layer_id: str  # A, B, C, D, E, F
    layer_name: str
    sub_scores: Dict[str, Any]  # Sub-criterion ID -> score
    fail_conditions: List[str] = Field(default_factory=list)
    evidence_notes: List[str] = Field(default_factory=list)
    verdict: Literal["Pass", "Weak Pass", "Fail"]


class RoleEvaluation(BaseModel):
    """Evaluation result from a single specialist role."""
    role_id: int
    role_name: str
    is_hard_gate: bool
    result: Literal["PASS", "FAIL"]
    score: Optional[float] = Field(default=None, ge=0, le=10)  # 0-10, only if PASS
    confidence: float = Field(..., ge=0, le=1)  # 0.0-1.0
    justification: str
    layer_scores: List[LayerScore] = Field(default_factory=list)


# ============================================================================
# Output Models
# ============================================================================

class FinalReport(BaseModel):
    """Executive-facing final report."""
    verdict: Literal["RECOMMEND", "REVISE BEFORE RECOMMENDATION", "DO NOT RECOMMEND"]
    top_strengths: List[str] = Field(..., max_items=3)
    top_risks: List[str] = Field(..., max_items=3)
    predicted_commercial_role: Literal["Brand growth", "Activation", "Both", "Neither"]
    revision_guidance: Optional[str] = None
    confidence_level: Literal["Low", "Medium", "High"]


class AnalysisAppendix(BaseModel):
    """Detailed diagnostic appendix for expert review."""
    contextual_baseline: ContextualBaseline
    layer_matrices: Dict[str, LayerScore]  # Layer ID -> Scoring matrix
    fail_register: List[str]
    risk_register: List[str]
    raw_score_summary: Dict[str, float]
    confidence_dampeners: List[str]
    verdict_traceability: Dict[str, List[str]]  # Report element -> supporting layers
    revision_sensitivity: Optional[Dict[str, str]] = None  # Layer -> potential impact


class EvaluationResult(BaseModel):
    """Complete evaluation result."""
    evaluation_id: str
    created_at: str
    input_summary: Dict[str, Any]
    role_evaluations: List[RoleEvaluation]
    final_effectiveness_index: float
    final_report: FinalReport
    analysis_appendix: AnalysisAppendix
    hard_gate_failed: bool = False
    failed_hard_gate_role: Optional[str] = None
