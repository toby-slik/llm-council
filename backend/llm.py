"""Unified LLM query function supporting multiple backends.

Automatically selects between Google Gemini API (if configured) or
OpenRouter free models as fallback.
"""

from typing import List, Dict, Any, Optional
from .config import USE_GEMINI


async def query_llm(
    messages: List[Dict[str, str]],
    timeout: float = None,
) -> Optional[Dict[str, Any]]:
    """
    Query an LLM with automatic backend selection.
    
    Uses Google Gemini if GOOGLE_API_KEY is configured,
    otherwise falls back to OpenRouter free models.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        timeout: Optional request timeout
        
    Returns:
        Dict with 'content' key, or None on failure
    """
    if USE_GEMINI:
        from .gemini import query_gemini
        return await query_gemini(messages, timeout=timeout)
    else:
        from .openrouter import query_model
        from .config import OPENROUTER_MODELS
        # Use first available model
        return await query_model(OPENROUTER_MODELS[0], messages, timeout=timeout)


async def get_active_backend() -> str:
    """Get the name of the currently active LLM backend."""
    if USE_GEMINI:
        from .config import GEMINI_MODEL
        return f"Google Gemini ({GEMINI_MODEL})"
    else:
        from .config import OPENROUTER_MODELS
        return f"OpenRouter ({OPENROUTER_MODELS[0]})"
