"""Core Evaluation Orchestration for Creative Effectiveness.

Implements the strict evaluation flow:
1. Lock contextual baseline
2. Run 8 role evaluations in parallel  
3. Check HARD GATEs → STOP if any FAIL
4. Calculate Final Effectiveness Index
5. Generate Final Report + Analysis Appendix
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from .models import (
    EvaluationInput,
    EvaluationResult,
    ContextualBaseline,
    RoleEvaluation,
    LayerScore,
    FinalReport,
    AnalysisAppendix,
)
from .roles import get_all_roles, get_hard_gate_roles, RoleDefinition
from .framework import get_layers_for_role, build_framework_prompt, build_scoring_instructions


# ============================================================================
# Contextual Baseline
# ============================================================================

def build_contextual_baseline(input_data: EvaluationInput) -> ContextualBaseline:
    """
    Build and lock the contextual baseline from input data.
    This becomes immutable for all subsequent scoring decisions.
    """
    # Build summary bullets (max 5)
    bullets = [
        f"Brand Status: {input_data.brand_status.value}",
        f"Market: {input_data.market_context.market_maturity.value} maturity, {input_data.market_context.category_clutter.value} clutter",
        f"Purchase: {input_data.market_context.purchase_frequency.value} frequency, {input_data.market_context.decision_involvement.value} involvement",
    ]
    
    if input_data.competitive_context:
        bullets.append(f"Competitive noise: {input_data.competitive_context.competitive_noise.value}")
    else:
        bullets.append("Competitive noise: Medium (assumed)")
    
    bullets.append(f"Objective: {input_data.campaign_objective.value}")
    
    return ContextualBaseline(
        brand_status=input_data.brand_status.value,
        market_maturity=input_data.market_context.market_maturity.value,
        category_clutter=input_data.market_context.category_clutter.value,
        purchase_frequency=input_data.market_context.purchase_frequency.value,
        decision_involvement=input_data.market_context.decision_involvement.value,
        competitive_noise=(
            input_data.competitive_context.competitive_noise.value 
            if input_data.competitive_context else "Medium"
        ),
        summary_bullets=bullets[:5],
    )


# ============================================================================
# Prompt Building
# ============================================================================

def build_evaluation_prompt(
    role: RoleDefinition,
    input_data: EvaluationInput,
    contextual_baseline: ContextualBaseline
) -> str:
    """Build the complete evaluation prompt for a role."""
    
    # Get the framework layers this role should evaluate
    layers = get_layers_for_role(role.framework_layers)
    framework_section = build_framework_prompt(layers)
    scoring_instructions = build_scoring_instructions()
    
    # Build creative description
    creative_desc = input_data.creative.description
    if input_data.creative.file_path:
        creative_desc += f"\n[File attached: {input_data.creative.file_type}]"
    
    prompt = f"""# CREATIVE EFFECTIVENESS EVALUATION

## CONTEXTUAL BASELINE (LOCKED - DO NOT CONTRADICT)
{chr(10).join('• ' + b for b in contextual_baseline.summary_bullets)}

## CREATIVE BEING EVALUATED
**Brand**: {input_data.brand_name}
**Category**: {input_data.category}
**Objective**: {input_data.campaign_objective.value}
**Channels**: {', '.join(input_data.primary_channels)}
**Target Audience**: {input_data.target_audience}

**Creative Description**:
{creative_desc}

---

## YOUR EVALUATION FRAMEWORK
{framework_section}

---

{scoring_instructions}

---

## YOUR TASK
Evaluate this creative deeply.
1. Identify KEY DISCOVERIES in the creative execution.
2. Provide COMPREHENSIVE REASONING for your score in the 'justification' field.
3. Be analytical, critical, and specific. Explain what you found and why it matters.

Return ONLY the JSON output. No preamble.
"""
    
    return prompt


# ============================================================================
# Role Evaluation
# ============================================================================

async def evaluate_with_role(
    role: RoleDefinition,
    input_data: EvaluationInput,
    contextual_baseline: ContextualBaseline,
    query_func,  # Async function to query the LLM
    on_role_complete=None  # Optional callback for progress updates
) -> RoleEvaluation:
    """
    Run evaluation for a single role.
    
    Args:
        role: The role definition
        input_data: The evaluation input
        contextual_baseline: Locked contextual baseline
        query_func: Async function (messages) -> response
        on_role_complete: Optional callback(role_name, result, status, justification)
        
    Returns:
        RoleEvaluation result
    """
    # Build the evaluation prompt
    if on_role_complete:
        on_role_complete(role.name, None, status="processing", justification="Building evaluation framework...")
    eval_prompt = build_evaluation_prompt(role, input_data, contextual_baseline)
    
    messages = [
        {"role": "system", "content": role.system_prompt},
        {"role": "user", "content": eval_prompt},
    ]
    
    try:
        # Query the LLM
        if on_role_complete:
            on_role_complete(role.name, None, status="processing", justification="Querying specialist LLM...")
        
        response = await query_func(messages)
        
        if response is None:
            # Model failed - treat as low-confidence PASS to not block
            return RoleEvaluation(
                role_id=role.id,
                role_name=role.name,
                is_hard_gate=role.is_hard_gate,
                result="PASS",
                score=5.0,
                confidence=0.3,
                justification=f"Model query failed. Defaulting to neutral score with low confidence.",
                layer_scores=[],
            )
        
        if on_role_complete:
            on_role_complete(role.name, None, status="processing", justification="Parsing specialist response...")
        
        # Parse the JSON response
        content = response.get("content", "")
        
        # Try to extract JSON from the response
        parsed = parse_evaluation_response(content)
        
        return RoleEvaluation(
            role_id=role.id,
            role_name=role.name,
            is_hard_gate=role.is_hard_gate,
            result=parsed.get("result", "PASS"),
            score=parsed.get("score"),
            confidence=parsed.get("confidence", 0.5),
            justification=parsed.get("justification", "No justification provided"),
            layer_scores=parse_layer_scores(parsed.get("layer_scores", {})),
        )
        
    except Exception as e:
        # Re-raise 429 specifically so it fails the entire evaluation as requested
        if "429" in str(e):
            raise e
            
        # Error during evaluation - return low-confidence result
        return RoleEvaluation(
            role_id=role.id,
            role_name=role.name,
            is_hard_gate=role.is_hard_gate,
            result="PASS",
            score=5.0,
            confidence=0.2,
            justification=f"Evaluation error: {str(e)}",
            layer_scores=[],
        )


def parse_evaluation_response(content: str) -> Dict[str, Any]:
    """Parse JSON from model response, handling markdown code blocks."""
    # Try to find JSON in code block
    if "```json" in content:
        start = content.find("```json") + 7
        end = content.find("```", start)
        if end > start:
            content = content[start:end].strip()
    elif "```" in content:
        start = content.find("```") + 3
        end = content.find("```", start)
        if end > start:
            content = content[start:end].strip()
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to find any JSON object in the content
        import re
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        
        return {"result": "PASS", "score": 5.0, "confidence": 0.3, "justification": "Failed to parse response"}


def parse_layer_scores(layer_data: Dict[str, Any]) -> List[LayerScore]:
    """Parse layer scores from response data."""
    scores = []
    for layer_id, data in layer_data.items():
        scores.append(LayerScore(
            layer_id=layer_id,
            layer_name=data.get("name", f"Layer {layer_id}"),
            sub_scores=data.get("sub_scores", {}),
            fail_conditions=data.get("fail_conditions", []),
            evidence_notes=data.get("evidence_notes", []),
            verdict=data.get("verdict", "Pass"),
        ))
    return scores


# ============================================================================
# Final Effectiveness Index Calculation
# ============================================================================

def calculate_fei(
    role_evaluations: List[RoleEvaluation],
    pattern_breaker_id: int = 6,
) -> float:
    """
    Calculate Final Effectiveness Index.
    
    FEI = Sum(Score × Confidence × Weight) − Pattern Breaker Penalty
    """
    from .roles import get_role_weights
    
    weights = get_role_weights()
    total = 0.0
    pattern_breaker_penalty = 0.0
    
    for eval in role_evaluations:
        if eval.result == "FAIL":
            continue  # Failed roles don't contribute
            
        if eval.role_id == pattern_breaker_id:
            # Pattern breaker score becomes penalty
            # Higher score = more risks identified = higher penalty
            pattern_breaker_penalty = (eval.score or 0) * eval.confidence * 0.5
        else:
            weight = weights.get(eval.role_id, 1.0)
            score = eval.score or 0
            total += score * eval.confidence * weight
    
    # Apply penalty and normalize to 0-100 scale
    fei = max(0, total - pattern_breaker_penalty)
    
    # Normalize: max possible is roughly 8 roles * 10 score * 1.0 confidence * 1.5 weight
    max_possible = 80  # Approximate
    normalized = (fei / max_possible) * 100
    
    return round(min(100, max(0, normalized)), 1)


# ============================================================================
# Final Report & Appendix Generation
# ============================================================================

def generate_final_report(
    role_evaluations: List[RoleEvaluation],
    fei: float,
    contextual_baseline: ContextualBaseline,
    campaign_objective: str,
) -> FinalReport:
    """Generate the executive-facing final report."""
    
    # Determine verdict based on FEI and fails
    has_fails = any(e.result == "FAIL" for e in role_evaluations)
    
    if has_fails:
        verdict = "DO NOT RECOMMEND"
    elif fei >= 70:
        verdict = "RECOMMEND"
    elif fei >= 40:
        verdict = "REVISE BEFORE RECOMMENDATION"
    else:
        verdict = "DO NOT RECOMMEND"
    
    # Extract strengths (highest confidence PASS evaluations)
    passing = [e for e in role_evaluations if e.result == "PASS" and e.score and e.score >= 7]
    passing.sort(key=lambda x: (x.score or 0) * x.confidence, reverse=True)
    strengths = [e.justification[:200] for e in passing[:3]]
    
    # Extract risks (from pattern breaker and any weak scores)
    risks = []
    for eval in role_evaluations:
        if eval.role_id == 6:  # Pattern breaker
            risks.append(eval.justification[:200])
        elif eval.score and eval.score < 5:
            risks.append(f"{eval.role_name}: {eval.justification[:150]}")
    risks = risks[:3]
    
    # Determine commercial role prediction
    if "long-term" in campaign_objective.lower():
        commercial_role = "Brand growth"
    elif "short-term" in campaign_objective.lower():
        commercial_role = "Activation"
    elif "mixed" in campaign_objective.lower():
        commercial_role = "Both"
    else:
        commercial_role = "Brand growth"  # Default
    
    # Revision guidance if needed
    revision = None
    if verdict == "REVISE BEFORE RECOMMENDATION":
        weak_areas = [e.role_name for e in role_evaluations if e.score and e.score < 6]
        if weak_areas:
            revision = f"Focus improvement on: {', '.join(weak_areas[:3])}"
    
    # Confidence level
    avg_confidence = sum(e.confidence for e in role_evaluations) / len(role_evaluations)
    if avg_confidence >= 0.8:
        confidence = "High"
    elif avg_confidence >= 0.5:
        confidence = "Medium"
    else:
        confidence = "Low"
    
    return FinalReport(
        verdict=verdict,
        top_strengths=strengths if strengths else ["Insufficient data for strength identification"],
        top_risks=risks if risks else ["No material risks identified"],
        predicted_commercial_role=commercial_role,
        revision_guidance=revision,
        confidence_level=confidence,
    )


def generate_analysis_appendix(
    role_evaluations: List[RoleEvaluation],
    contextual_baseline: ContextualBaseline,
    fei: float,
) -> AnalysisAppendix:
    """Generate the detailed analysis appendix."""
    
    # Collect all layer scores
    layer_matrices = {}
    for eval in role_evaluations:
        for ls in eval.layer_scores:
            layer_matrices[ls.layer_id] = ls
    
    # Collect fails and risks
    fail_register = [
        f"{e.role_name}: {e.justification[:100]}"
        for e in role_evaluations if e.result == "FAIL"
    ]
    
    risk_register = []
    for eval in role_evaluations:
        for ls in eval.layer_scores:
            risk_register.extend(ls.fail_conditions)
    
    # Raw score summary
    raw_scores = {
        e.role_name: e.score for e in role_evaluations if e.score
    }
    
    # Confidence dampeners
    dampeners = [
        f"{e.role_name}: confidence {e.confidence:.1%}"
        for e in role_evaluations if e.confidence < 0.7
    ]
    
    # Verdict traceability
    traceability = {
        "verdict": [e.role_name for e in role_evaluations],
        "strengths": [e.role_name for e in role_evaluations if e.score and e.score >= 7],
        "risks": [e.role_name for e in role_evaluations if e.score and e.score < 5],
    }
    
    return AnalysisAppendix(
        contextual_baseline=contextual_baseline,
        layer_matrices=layer_matrices,
        fail_register=fail_register,
        risk_register=list(set(risk_register)),
        raw_score_summary=raw_scores,
        confidence_dampeners=dampeners,
        verdict_traceability=traceability,
    )


# ============================================================================
# Main Evaluation Entry Point
# ============================================================================

async def run_creative_evaluation(
    input_data: EvaluationInput,
    query_func,  # Async function to query LLM
    on_role_complete=None,  # Optional callback for progress updates
) -> EvaluationResult:
    """
    Run the complete creative effectiveness evaluation.
    
    Args:
        input_data: Validated evaluation input
        query_func: Async function (messages) -> response dict
        on_role_complete: Optional callback(role_name, result) for progress
        
    Returns:
        Complete EvaluationResult
    """
    evaluation_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat() + "Z"
    
    # Step 1: Lock contextual baseline
    contextual_baseline = build_contextual_baseline(input_data)
    
    # Step 2: Run all role evaluations in parallel
    roles = get_all_roles()
    
    # Notify initial status for all roles
    if on_role_complete:
        for role in roles:
            # We use the same callback for status updates
            on_role_complete(role.name, None, status="queued")
    
    async def evaluate_role(role: RoleDefinition) -> RoleEvaluation:
        if on_role_complete:
            on_role_complete(role.name, None, status="processing")
        
        result = await evaluate_with_role(role, input_data, contextual_baseline, query_func, on_role_complete=on_role_complete)
        
        if on_role_complete:
            on_role_complete(role.name, result, status="complete")
        return result
    
    role_evaluations = await asyncio.gather(*[evaluate_role(r) for r in roles])
    role_evaluations = list(role_evaluations)
    
    # Step 3: Check HARD GATEs
    hard_gate_failed = False
    failed_hard_gate_role = None
    
    for eval in role_evaluations:
        if eval.is_hard_gate and eval.result == "FAIL":
            hard_gate_failed = True
            failed_hard_gate_role = eval.role_name
            break  # Stop on first hard gate failure
    
    # Step 4 & 5: Calculate FEI (skip if hard gate failed)
    if hard_gate_failed:
        fei = 0.0
    else:
        fei = calculate_fei(role_evaluations)
    
    # Step 6: Generate outputs
    final_report = generate_final_report(
        role_evaluations,
        fei,
        contextual_baseline,
        input_data.campaign_objective.value,
    )
    
    # Override verdict if hard gate failed
    if hard_gate_failed:
        final_report.verdict = "DO NOT RECOMMEND"
        final_report.top_risks.insert(0, f"HARD GATE FAILED: {failed_hard_gate_role}")
    
    analysis_appendix = generate_analysis_appendix(
        role_evaluations,
        contextual_baseline,
        fei,
    )
    
    return EvaluationResult(
        evaluation_id=evaluation_id,
        created_at=created_at,
        input_summary={
            "brand": input_data.brand_name,
            "category": input_data.category,
            "objective": input_data.campaign_objective.value,
        },
        role_evaluations=role_evaluations,
        final_effectiveness_index=fei,
        final_report=final_report,
        analysis_appendix=analysis_appendix,
        hard_gate_failed=hard_gate_failed,
        failed_hard_gate_role=failed_hard_gate_role,
    )
