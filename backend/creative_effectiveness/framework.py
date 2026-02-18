"""6-Layer Evaluation Framework for Creative Effectiveness.

Implements the mandatory evaluation layers A-F with sub-criteria,
scoring mechanics, and fail conditions.
"""

from typing import Dict, List, Any, Literal
from dataclasses import dataclass, field


@dataclass
class SubCriterion:
    """Definition of a sub-criterion within a layer."""
    id: str
    name: str
    question: str
    score_type: str  # "1-5", "weak/moderate/strong", "low/medium/high", etc.
    fail_condition: str
    evaluation_mechanic: str


@dataclass
class Layer:
    """Definition of an evaluation layer."""
    id: str  # A, B, C, D, E, F
    name: str
    sub_criteria: List[SubCriterion]


# ============================================================================
# Layer Definitions from Planning Document
# ============================================================================

LAYER_A = Layer(
    id="A",
    name="Emotional Prediction",
    sub_criteria=[
        SubCriterion(
            id="A1",
            name="Emotional Response Strength",
            question="Does the creative generate clear, positive emotion within the first 2–3 seconds? Is the emotion felt, not explained?",
            score_type="1-5",
            fail_condition="Flat, neutral, or confusion-led response",
            evaluation_mechanic="""1) Isolate only the first exposure viewing.
2) Examine the first 2–3 seconds independently of narrative context.
3) Identify whether a recognisable emotion is immediately present without verbal or cognitive explanation.
4) Apply the following test: if the emotion cannot be named without explaining the story, cap score at 2.
5) Assign score based on immediacy and clarity of affective signal.
6) Lock score before proceeding."""
        ),
        SubCriterion(
            id="A2",
            name="Type of Emotion Quality",
            question="Is the emotion conducive to memory formation and future choice (e.g. warmth, amusement, pride), not just surprise or shock? Does it align with brand personality?",
            score_type="weak/moderate/strong",
            fail_condition="Emotion entertains but does not attach to the brand",
            evaluation_mechanic="""1) Identify the single dominant emotion from a fixed set (warmth, joy, amusement, reassurance, excitement, surprise, tension, other).
2) Exclude mixed or sequential emotions; select the strongest.
3) Test brand linkage: ask whether this emotion could credibly belong to multiple competing brands.
4) If yes, cap at Moderate.
5) Cross-check alignment with brand personality and category norms.
6) Assign final rating and lock."""
        ),
        SubCriterion(
            id="A3",
            name="Emotional Sustainability",
            question="Would the emotion remain effective after multiple exposures? Is it irritation-resistant?",
            score_type="low/medium/high",
            fail_condition="Joke-dependent or novelty-dependent creative",
            evaluation_mechanic="""1) Identify the emotional trigger mechanism (story, character, relationship, gag, reveal).
2) Simulate second and third exposure without surprise.
3) If emotional payoff depends on a twist, punchline, or reveal, score Low.
4) If emotion is character- or relationship-led, score Medium or High.
5) Assign score based on durability, not intensity.
6) Lock result."""
        ),
    ]
)

LAYER_B = Layer(
    id="B",
    name="Brand Linkage & Distinctiveness",
    sub_criteria=[
        SubCriterion(
            id="B1",
            name="Brand Attribution Speed (Fluency)",
            question="Can the brand be recognised instantly and confidently? Are distinctive brand assets clearly and early embedded?",
            score_type="poor/adequate/strong",
            fail_condition='"Great ad, wrong brand" risk',
            evaluation_mechanic="""1) Remove brand identifiers mentally.
2) Ask unaided: "Which brand is this for?" within first moments.
3) Assess timing and integration of distinctive assets.
4) If branding appears only at end or as overlay, cap at Adequate.
5) If misattribution is plausible, score Poor.
6) Lock score."""
        ),
        SubCriterion(
            id="B2",
            name="Memory Structure Contribution (Ehrenberg-Bass)",
            question="Does this creative reinforce category entry cues or distinctive brand assets? Will it increase mental availability beyond this campaign?",
            score_type="no/partial/yes",
            fail_condition="One-off idea with no memory continuity",
            evaluation_mechanic="""1) List known category entry cues and brand assets.
2) Map creative elements to those cues.
3) If no clear linkage exists, score No.
4) If linkage is present but inconsistent, score Partial.
5) If creative strengthens existing memory structures, score Yes.
6) Lock result."""
        ),
    ]
)

LAYER_C = Layer(
    id="C",
    name="Strategic Effectiveness Fit (Binet & Field)",
    sub_criteria=[
        SubCriterion(
            id="C1",
            name="Objective Alignment",
            question="Is the creative clearly optimised for Long-term brand building, Short-term activation, or is it confused?",
            score_type="clear/mixed/misaligned",
            fail_condition="Brand-style work forced into activation roles (or vice versa)",
            evaluation_mechanic="""1) Identify dominant mechanism: emotional priming or behavioural trigger.
2) Compare mechanism to stated objective.
3) If mechanisms conflict, score Misaligned.
4) If one dominates but secondary signals interfere, score Mixed.
5) Assign Clear only when all elements support the same objective.
6) Lock score."""
        ),
        SubCriterion(
            id="C2",
            name="Expected Effect Duration",
            question="Will impact persist beyond the media window?",
            score_type="short-lived/moderate/enduring",
            fail_condition="Campaign requires constant spend to function",
            evaluation_mechanic="""1) Assess whether creative builds memory or relies on reminders.
2) If offer-, price-, or urgency-led only, score Short-lived.
3) If some memory effects present, score Moderate.
4) If creative clearly builds long-term associations, score Enduring.
5) Lock result."""
        ),
    ]
)

LAYER_D = Layer(
    id="D",
    name="Attention & Delivery Realism",
    sub_criteria=[
        SubCriterion(
            id="D1",
            name="Attention Probability",
            question="In the actual media environment, will this creative likely be noticed? Does it earn attention rather than assume it?",
            score_type="low/medium/high",
            fail_condition="Relies on forced exposure assumptions",
            evaluation_mechanic="""1) Identify primary channel and viewing conditions.
2) Evaluate creative against scroll speed, clutter, sound defaults.
3) If attention relies on media weight alone, score Low.
4) If creative earns attention through pattern-break or relevance, score Medium or High.
5) Lock score."""
        ),
        SubCriterion(
            id="D2",
            name="Early Frame Performance",
            question="Are the opening frames strong enough for scroll environments?",
            score_type="weak/adequate/strong",
            fail_condition="Slow-burn concepts in fast-scroll contexts",
            evaluation_mechanic="""1) Isolate opening frames.
2) Check for immediate intrigue, brand cue, or disruption.
3) If none present, score Weak.
4) If present but delayed, score Adequate.
5) If immediate and compelling, score Strong.
6) Lock result."""
        ),
    ]
)

LAYER_E = Layer(
    id="E",
    name="Comprehension & Persuasion",
    sub_criteria=[
        SubCriterion(
            id="E1",
            name="Message Take-Out Accuracy",
            question="Would a typical viewer correctly articulate the intended benefit or idea?",
            score_type="clear/partial/unclear",
            fail_condition="Ambiguity about what the brand is offering",
            evaluation_mechanic="""1) Elicit unaided take-out.
2) List all plausible interpretations.
3) If more than one materially different interpretation exists, cap at Partial.
4) If take-out is incorrect or vague, score Unclear.
5) Lock score."""
        ),
        SubCriterion(
            id="E2",
            name="Barrier Resolution (JTBD Logic)",
            question="Does the creative resolve a real psychological or practical barrier?",
            score_type="no/somewhat/clearly",
            fail_condition="Emotional but non-persuasive work",
            evaluation_mechanic="""1) Identify the primary barrier (cost, effort, trust, relevance).
2) Assess whether creative materially reduces that barrier.
3) If not addressed, score No.
4) If partially reduced, score Somewhat.
5) If clearly resolved, score Clearly.
6) Lock result."""
        ),
    ]
)

LAYER_F = Layer(
    id="F",
    name="Commercial & Operational Risk",
    sub_criteria=[
        SubCriterion(
            id="F1",
            name="Wear-Out Risk",
            question="Will performance decay quickly due to repetition?",
            score_type="low/medium/high",  # Note: Higher = worse
            fail_condition="High wear-out with no variant strategy",
            evaluation_mechanic="""1) Identify dependence on novelty or single execution.
2) Assess modularity and variant potential.
3) If no variant path exists, score High risk.
4) Lock result."""
        ),
        SubCriterion(
            id="F2",
            name="Reputational / Regulatory Risk",
            question="Any plausible backlash, compliance, or trust risks?",
            score_type="none/manageable/material",  # Note: Higher = worse
            fail_condition="Material risk without mitigation",
            evaluation_mechanic="""1) Stress-test against regulatory codes and cultural sensitivity.
2) Identify plausible misinterpretation scenarios.
3) If mitigation is absent or unclear, score Material.
4) Lock result."""
        ),
    ]
)


# All layers for easy access
LAYERS: Dict[str, Layer] = {
    "A": LAYER_A,
    "B": LAYER_B,
    "C": LAYER_C,
    "D": LAYER_D,
    "E": LAYER_E,
    "F": LAYER_F,
}


def get_layer(layer_id: str) -> Layer:
    """Get layer definition by ID."""
    return LAYERS[layer_id]


def get_all_layers() -> List[Layer]:
    """Get all layer definitions."""
    return list(LAYERS.values())


def get_layers_for_role(layer_ids: List[str]) -> List[Layer]:
    """Get specific layers for a role's evaluation scope."""
    return [LAYERS[lid] for lid in layer_ids if lid in LAYERS]


def build_framework_prompt(layers: List[Layer]) -> str:
    """Build the evaluation framework prompt for specific layers."""
    sections = []
    
    for layer in layers:
        section = f"## LAYER {layer.id} — {layer.name.upper()}\n\n"
        
        for sc in layer.sub_criteria:
            section += f"### {sc.id}. {sc.name}\n"
            section += f"**Question**: {sc.question}\n"
            section += f"**Score Type**: {sc.score_type}\n"
            section += f"**Fail Condition**: {sc.fail_condition}\n\n"
            section += f"**Evaluation Mechanic**:\n{sc.evaluation_mechanic}\n\n"
        
        sections.append(section)
    
    return "\n---\n\n".join(sections)


def build_scoring_instructions() -> str:
    """Build the standardized scoring output instructions."""
    return """
## SCORING OUTPUT FORMAT (STRICT)

You must return your evaluation in the following JSON structure:

```json
{
  "result": "PASS" or "FAIL",
  "score": 0-10 (only if PASS, null if FAIL),
  "confidence": 0.0-1.0,
  "justification": "Comprehensive analysis including:\\n1. KEY DISCOVERIES: What specific details stand out?\\n2. STRATEGIC REASONING: Why does this succeed or fail?\\n3. EVIDENCE: Direct quotes or descriptions from the creative",
  "layer_scores": {
    "<layer_id>": {
      "verdict": "Pass" or "Weak Pass" or "Fail",
      "sub_scores": {
        "<criterion_id>": "<score_value>",
        ...
      },
      "fail_conditions": ["list any triggered fail conditions"],
      "evidence_notes": ["factual observations only"]
    },
    ...
  }
}
```

RULES:
- Score only the layers within your defined remit
- Lock each score before proceeding to the next
- PROVIDE DEEP ANALYSIS. Do not be superficial.
- Explain WHAT you discovered and WHY it matters.
- Justification must be detailed and referenced.
"""
