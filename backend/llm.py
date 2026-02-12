"""Unified LLM query function supporting multiple backends.

Automatically selects between Google Gemini API (if configured) or
OpenRouter free models as fallback.
"""

from typing import List, Dict, Any, Optional
from .config import USE_GEMINI


async def query_llm(
    messages: List[Dict[str, str]],
    model: str = None,
    timeout: float = None,
) -> Optional[Dict[str, Any]]:
    """
    Query an LLM with automatic backend selection.
    
    Uses Google Gemini if GOOGLE_API_KEY is configured,
    otherwise falls back to OpenRouter free models.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Optional model name to override default
        timeout: Optional request timeout
        
    Returns:
        Dict with 'content' key, or None on failure
    """
    from .config import OPENROUTER_API_KEY
    
    if USE_GEMINI:
        from .gemini import query_gemini
        # Try Gemini first
        try:
            result = await query_gemini(messages, model=model, timeout=timeout)
            if result:
                return result
        except Exception as e:
            # If it's a 429, we might still want to try fallback if available
            if "429" in str(e) and OPENROUTER_API_KEY:
                print(f"Gemini rate limited (429), falling back to OpenRouter...")
            else:
                # Re-raise so it can fail the whole thing if no fallback
                raise e
            
        # If Gemini failed (e.g. 429) and we have OpenRouter key, fall back
        if OPENROUTER_API_KEY:
            from .openrouter import query_model
            from .config import OPENROUTER_MODELS
            return await query_model(OPENROUTER_MODELS[0], messages, timeout=timeout)
        return None
    else:
        from .openrouter import query_model
        from .config import OPENROUTER_MODELS
        # Use provided model or first fallback
        target_model = model or OPENROUTER_MODELS[0]
        try:
            return await query_model(target_model, messages, timeout=timeout)
        except Exception as e:
            if "429" in str(e):
                raise e
            print(f"OpenRouter query failed: {e}")
            return None


async def get_active_backend() -> str:
    """Get the name of the currently active LLM backend."""
    if USE_GEMINI:
        from .config import GEMINI_MODEL
        return f"Google Gemini ({GEMINI_MODEL})"
    else:
        from .config import OPENROUTER_MODELS
        return f"OpenRouter ({OPENROUTER_MODELS[0]})"
