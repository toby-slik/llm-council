"""Pre-submission input validation for Creative Effectiveness Evaluation.

Validates that all required inputs are present and sufficient before
running expensive LLM evaluation prompts.
"""

from typing import List, Dict, Any
from pydantic import BaseModel, Field

from .models import EvaluationInput, CreativeAsset


class ValidationResult(BaseModel):
    """Result of input validation check."""
    valid: bool
    missing_fields: List[str] = Field(default_factory=list)
    incomplete_fields: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    ready_to_evaluate: bool = False


# Minimum character thresholds for quality evaluation
MIN_CREATIVE_DESCRIPTION = 100
MIN_TARGET_AUDIENCE = 50
MIN_CULTURAL_NOTES = 20


def validate_creative_asset(creative: CreativeAsset) -> tuple[bool, List[str]]:
    """Validate that creative asset has sufficient content."""
    errors = []
    warnings = []
    
    has_file = creative.file_path is not None
    has_description = len(creative.description.strip()) >= MIN_CREATIVE_DESCRIPTION
    
    if not has_file and not has_description:
        errors.append("creative_asset")
        return False, errors
    
    if has_description and len(creative.description.strip()) < MIN_CREATIVE_DESCRIPTION:
        warnings.append(
            f"Creative description is short ({len(creative.description)} chars) - "
            f"minimum {MIN_CREATIVE_DESCRIPTION} recommended for accurate evaluation"
        )
    
    return True, warnings


def validate_input(data: Dict[str, Any]) -> ValidationResult:
    """
    Validate input data before running evaluation.
    
    This is a lightweight check that runs instantly to prevent
    wasting expensive LLM calls on incomplete submissions.
    
    Args:
        data: Raw input dictionary from API request
        
    Returns:
        ValidationResult with detailed feedback
    """
    missing = []
    incomplete = []
    warnings = []
    
    # Required top-level fields
    required_fields = [
        "brand_name",
        "category", 
        "campaign_objective",
        "primary_channels",
        "target_audience",
        "brand_status",
        "market_context",
    ]
    
    for field in required_fields:
        if field not in data or not data[field]:
            missing.append(field)
    
    # Check creative asset
    creative_data = data.get("creative", {})
    if not creative_data:
        missing.append("creative")
    else:
        has_file = creative_data.get("file_path") is not None
        description = creative_data.get("description", "")
        has_description = len(description.strip()) >= MIN_CREATIVE_DESCRIPTION
        
        if not has_file and not has_description:
            if description and len(description.strip()) < MIN_CREATIVE_DESCRIPTION:
                incomplete.append("creative")
                warnings.append(
                    f"Creative description too short ({len(description.strip())} chars). "
                    f"Need at least {MIN_CREATIVE_DESCRIPTION} characters or upload a file."
                )
            else:
                missing.append("creative")
    
    # Check target audience length
    audience = data.get("target_audience", "")
    if audience and len(audience.strip()) < MIN_TARGET_AUDIENCE:
        incomplete.append("target_audience")
        warnings.append(
            f"Target audience description is brief ({len(audience.strip())} chars). "
            f"Recommend at least {MIN_TARGET_AUDIENCE} characters for accurate evaluation."
        )
    
    # Check primary channels is non-empty list
    channels = data.get("primary_channels", [])
    if isinstance(channels, list) and len(channels) == 0:
        missing.append("primary_channels")
    
    # Check market context sub-fields
    market = data.get("market_context", {})
    if market:
        market_fields = ["market_maturity", "category_clutter", "purchase_frequency", "decision_involvement"]
        for field in market_fields:
            if field not in market or not market[field]:
                incomplete.append(f"market_context.{field}")
    
    # Optional but recommended fields
    if not data.get("competitive_context"):
        warnings.append(
            "No competitive context provided. Evaluation will assume medium competitive noise."
        )
    
    if not data.get("local_factors"):
        warnings.append(
            "No local market factors provided. Evaluation will use general market assumptions."
        )
    
    # Determine overall validity
    is_valid = len(missing) == 0 and len(incomplete) == 0
    ready = is_valid and len([w for w in warnings if "too short" in w.lower()]) == 0
    
    return ValidationResult(
        valid=is_valid,
        missing_fields=missing,
        incomplete_fields=incomplete,
        warnings=warnings,
        ready_to_evaluate=ready
    )


def format_validation_feedback(result: ValidationResult) -> str:
    """Format validation result as human-readable message."""
    if result.ready_to_evaluate:
        return "✓ All required inputs provided. Ready to evaluate."
    
    lines = []
    
    if result.missing_fields:
        lines.append("Missing required fields:")
        for field in result.missing_fields:
            lines.append(f"  • {field.replace('_', ' ').title()}")
    
    if result.incomplete_fields:
        lines.append("\nIncomplete fields:")
        for field in result.incomplete_fields:
            lines.append(f"  • {field.replace('_', ' ').title()}")
    
    if result.warnings:
        lines.append("\nWarnings:")
        for warning in result.warnings:
            lines.append(f"  ⚠ {warning}")
    
    return "\n".join(lines)
