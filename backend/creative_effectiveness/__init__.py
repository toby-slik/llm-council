"""Creative Effectiveness Evaluation System.

An agentic AI system for evaluating creative work using 8 specialist roles
and a 6-layer evaluation framework.
"""

from .models import EvaluationInput, EvaluationResult, ContextualBaseline
from .validation import validate_input
from .evaluation import run_creative_evaluation

__all__ = [
    "EvaluationInput",
    "EvaluationResult", 
    "ContextualBaseline",
    "validate_input",
    "run_creative_evaluation",
]
