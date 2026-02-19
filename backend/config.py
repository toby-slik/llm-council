"""Configuration for the Creative Effectiveness Evaluation System."""

import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# API Keys
# ============================================================================

# OpenRouter API (for free-tier models)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Google API (for Gemini models - primary evaluation)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ============================================================================
# Model Configuration
# ============================================================================

# Primary evaluation model (used for all 8 roles when Google API available)
# Falls back to OpenRouter free models if Google API not configured
GEMINI_MODEL = "gemini-3-pro-preview"  # Fast and capable
GEMINI_FLASH_MODEL = "gemini-3-flash-preview"  # Higher quota, lower latency

# Fallback free models via OpenRouter
OPENROUTER_MODELS = [
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "tngtech/deepseek-r1t2-chimera:free",
    "z-ai/glm-4.5-air:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]

# ============================================================================
# Evaluation Settings
# ============================================================================

# Maximum time to wait for a single role evaluation (seconds)
EVALUATION_TIMEOUT = 120.0

# Whether to use Gemini (True) or OpenRouter free models (False)
USE_GEMINI = GOOGLE_API_KEY is not None

# ============================================================================
# Storage
# ============================================================================

# Data directory for evaluation storage
# On Vercel, only /tmp is writable. Locally, use the data/ directory.
import os as _os
DATA_DIR = "/tmp/evaluations" if _os.getenv("VERCEL") else "data/evaluations"
