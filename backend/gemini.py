"""Google Gemini API client for Creative Effectiveness Evaluation."""

import httpx
from typing import List, Dict, Any, Optional
from .config import GOOGLE_API_KEY, GEMINI_MODEL, EVALUATION_TIMEOUT


GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


async def query_gemini(
    messages: List[Dict[str, str]],
    model: str = None,
    timeout: float = None,
) -> Optional[Dict[str, Any]]:
    """
    Query Google Gemini API.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model to use (defaults to GEMINI_MODEL from config)
        timeout: Request timeout in seconds
        
    Returns:
        Dict with 'content' key, or None on failure
    """
    if not GOOGLE_API_KEY:
        return None
    
    model = model or GEMINI_MODEL
    timeout = timeout or EVALUATION_TIMEOUT
    
    # Convert messages to Gemini format
    # Gemini uses 'user' and 'model' roles, and a different structure
    contents = []
    system_instruction = None
    
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "system":
            # Gemini handles system prompts differently
            system_instruction = content
        elif role == "assistant":
            contents.append({
                "role": "model",
                "parts": [{"text": content}]
            })
        else:
            contents.append({
                "role": "user", 
                "parts": [{"text": content}]
            })
    
    # Build request
    url = f"{GEMINI_API_URL}/{model}:generateContent?key={GOOGLE_API_KEY}"
    
    request_body = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.95,
            "maxOutputTokens": 8192,
        }
    }
    
    # Add system instruction if present
    if system_instruction:
        request_body["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=request_body,
                timeout=timeout,
            )
            
            if response.status_code != 200:
                print(f"Gemini API error: {response.status_code} - {response.text[:200]}")
                return None
            
            data = response.json()
            
            # Extract text from response
            candidates = data.get("candidates", [])
            if not candidates:
                return None
            
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                return None
            
            text = parts[0].get("text", "")
            
            return {"content": text}
            
    except httpx.TimeoutException:
        print(f"Gemini API timeout after {timeout}s")
        return None
    except Exception as e:
        print(f"Gemini API error: {e}")
        return None


async def query_gemini_parallel(
    messages_list: List[List[Dict[str, str]]],
    model: str = None,
) -> List[Optional[Dict[str, Any]]]:
    """
    Query Gemini API with multiple message sets in parallel.
    
    Args:
        messages_list: List of message lists to process
        model: Model to use
        
    Returns:
        List of responses (None for failures)
    """
    import asyncio
    
    tasks = [query_gemini(msgs, model) for msgs in messages_list]
    return await asyncio.gather(*tasks)
