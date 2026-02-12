from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import base64

from .creative_effectiveness import (
    validate_input, 
    run_creative_evaluation,
    EvaluationInput,
    ContextualBaseline
)
from .documents import extract_text_from_file

router = APIRouter(prefix="/api/creative", tags=["creative"])

class ValidateRequest(BaseModel):
    brand_name: Optional[str] = None
    category: Optional[str] = None
    campaign_objective: Optional[str] = None
    primary_channels: Optional[list[str]] = None
    target_audience: Optional[str] = None
    brand_status: Optional[str] = None
    market_context: Optional[dict] = None
    creative: Optional[dict] = None
    competitive_context: Optional[dict] = None
    local_factors: Optional[dict] = None

@router.get("/config")
async def get_config():
    """Get configuration for creative evaluation."""
    return {
        "roles": [
            "Creative Director",
            "Strategist",
            "Media Planner",
            "Brand Manager",
            "Data Analyst",
            "Consumer Psychologist",
            "Copywriter",
            "Art Director"
        ],
        "framework": "Creative Effectiveness Ladder (6 layers)",
        "models": {
            "evaluation": "openai/gpt-4o",
            "synthesis": "anthropic/claude-3-5-sonnet"
        }
    }

@router.post("/validate")
async def validate(data: Dict[str, Any]):
    """Validate input data before evaluation."""
    # If file content is provided in base64, extracting text for validation
    creative = data.get("creative", {})
    file_content_b64 = creative.get("file_content")
    filename = creative.get("file_path")
    
    if file_content_b64 and filename:
        try:
            # Decode base64
            content_bytes = base64.b64decode(file_content_b64)
            # Extract text using shared document logic
            extracted_text = extract_text_from_file(filename, content_bytes)
            # Inject extracted text into description for validation if description is empty
            if not creative.get("description"):
                creative["description"] = f"[Extracted from {filename}]:\n{extracted_text[:1000]}..." # Truncate for validation check
            
            # Also valid if we successfully extracted text
            creative["has_valid_content"] = True
            
        except Exception as e:
            creative["file_error"] = str(e)
            
    result = validate_input(data)
    result = validate_input(data)
    return result

class ExtractRequest(BaseModel):
    file_content: str  # Base64 encoded
    file_name: str

@router.post("/extract")
async def extract_from_document(request: ExtractRequest):
    """
    Auto-extract structured evaluation input from a document.
    """
    try:
        from .llm import query_llm
        
        # 1. Decode and extract text
        content_bytes = base64.b64decode(request.file_content)
        text = extract_text_from_file(request.file_name, content_bytes)
        
        # 2. Prepare LLM prompt
        prompt = f"""
        You are a smart assistant that extracts structured marketing brief data from documents.
        
        DOCUMENT TEXT:
        {text[:15000]}  # Truncate to avoid context window issues
        
        The document is a marketing brief or creative asset.
        Extract the following fields into a JSON object:
        
        - brand_name (String)
        - category (String, e.g. "Automotive", "CPG")
        - campaign_objective (One of: "Long-term brand growth", "Short-term activation", "Mixed")
        - target_audience (String, detailed description)
        - brand_status (One of: "Market Leader", "Strong Challenger", "Emerging / Growth Brand", "New or Low-Awareness Brand")
        - market_context (Object with fields):
            - market_maturity (One of: "Mature", "Growing", "Emerging")
            - category_clutter (One of: "Low", "Medium", "High")
            - purchase_frequency (One of: "High", "Medium", "Low")
            - decision_involvement (One of: "Low", "Medium", "High")
        - creative_description (String, concise summary of the creative idea/execution if mentioned)
        
        If a field is not explicitly stated, infer it from context.
        If you absolutely cannot infer it, leave it as null.
        
        Respond ONLY with valid JSON.
        """
        
        # 3. Call LLM
        response = await query_llm([
            {"role": "system", "content": "You are a data extraction specialist. Output only valid JSON."},
            {"role": "user", "content": prompt}
        ])
        
        if not response:
            raise HTTPException(status_code=500, detail="LLM extraction failed")
            
        content = response["content"]
        
        # 4. Clean and parse JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        return json.loads(content.strip())
        
    except Exception as e:
        # Fallback partial structure on error
        print(f"Extraction error: {e}")
        return {"error": str(e)}

@router.post("/evaluate")
async def evaluate(data: EvaluationInput):
    """Run full creative effectiveness evaluation."""
    try:
        result = await run_creative_evaluation(data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluate/stream")
async def evaluate_stream(data: EvaluationInput):
    """Stream evaluation progress."""
    async def event_generator():
        try:
            # This is a placeholder for actual streaming logic
            # implementing a simple version that waits for result
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            
            result = await run_creative_evaluation(data)
            
            yield f"data: {json.dumps({'type': 'complete', 'data': result.dict()})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
