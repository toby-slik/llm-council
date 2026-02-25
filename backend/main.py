"""FastAPI backend for Creative Effectiveness Evaluation System."""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio
import os

from .creative_effectiveness.models import EvaluationInput, EvaluationResult
from .creative_effectiveness.validation import validate_input, ValidationResult
from .creative_effectiveness.evaluation import run_creative_evaluation
from .llm import query_llm, get_active_backend
from .config import USE_GEMINI

app = FastAPI(title="Creative Effectiveness Evaluation API")

# Enable CORS
# In production on Vercel, we allow all for simplicity, or you can specify your domain
if os.getenv("VERCEL"):
    allow_origins = ["*"]
else:
    allow_origins = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class ValidateRequest(BaseModel):
    """Request to validate input before evaluation."""
    brand_name: Optional[str] = None
    category: Optional[str] = None
    campaign_objective: Optional[str] = None
    primary_channels: Optional[List[str]] = None
    target_audience: Optional[str] = None
    brand_status: Optional[str] = None
    market_context: Optional[Dict[str, str]] = None
    creative: Optional[Dict[str, Any]] = None
    competitive_context: Optional[Dict[str, Any]] = None
    local_factors: Optional[Dict[str, Any]] = None


class EvaluateRequest(BaseModel):
    """Full evaluation request."""
    brand_name: str
    category: str
    campaign_objective: str
    primary_channels: List[str]
    target_audience: str
    brand_status: str
    market_context: Dict[str, str]
    creative: Dict[str, Any]
    competitive_context: Optional[Dict[str, Any]] = None
    local_factors: Optional[Dict[str, Any]] = None
    existing_research: Optional[str] = None


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    backend = await get_active_backend()
    return {
        "status": "ok", 
        "service": "Creative Effectiveness Evaluation API",
        "llm_backend": backend,
    }


@app.post("/api/creative/validate", response_model=ValidationResult)
async def validate_creative_input(request: ValidateRequest):
    """
    Validate input before running evaluation.
    This is a lightweight, instant check to ensure all required fields are present.
    """
    # Convert request to dict for validation
    data = request.model_dump(exclude_none=True)
    
    # Check for file content in request and extract if present
    creative = data.get("creative", {})
    file_content_b64 = creative.get("file_content")
    file_path = creative.get("file_path")
    
    if file_content_b64 and file_path:
        try:
            from .documents import extract_text_from_file
            import base64
            
            # Decode base64 content
            content_bytes = base64.b64decode(file_content_b64)
            # Extract text
            extracted_text = extract_text_from_file(file_path, content_bytes)
            
            # Add to data for validation logic (validation.py uses this)
            data["creative"]["extracted_text"] = extracted_text
            
        except Exception as e:
            data["creative"]["file_content_error"] = str(e)
            
    result = validate_input(data)
    return result


@app.post("/api/creative/evaluate")
async def evaluate_creative(request: EvaluateRequest):
    """
    Run full creative effectiveness evaluation.
    This may take several minutes as 8 specialist roles evaluate in parallel.
    """
    # First validate input
    data = request.model_dump()
    validation = validate_input(data)
    
    if not validation.valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Input validation failed",
                "missing_fields": validation.missing_fields,
                "incomplete_fields": validation.incomplete_fields,
            }
        )
    
    # Convert to EvaluationInput model
    try:
        from .creative_effectiveness.models import (
            EvaluationInput, 
            CreativeAsset,
            MarketContext,
            BrandStatus,
            CampaignObjective,
            MarketMaturity,
            ClutterLevel,
            PurchaseFrequency,
            DecisionInvolvement,
            CompetitiveContext,
            CompetitiveNoise,
            LocalFactors,
        )
        
        creative = CreativeAsset(
            description=data["creative"].get("description", ""),
            file_path=data["creative"].get("file_path"),
            file_type=data["creative"].get("file_type"),
        )
        
        market = data["market_context"]
        market_context = MarketContext(
            market_maturity=MarketMaturity(market["market_maturity"]),
            category_clutter=ClutterLevel(market["category_clutter"]),
            purchase_frequency=PurchaseFrequency(market["purchase_frequency"]),
            decision_involvement=DecisionInvolvement(market["decision_involvement"]),
        )
        
        competitive = None
        if data.get("competitive_context"):
            cc = data["competitive_context"]
            competitive = CompetitiveContext(
                competitor_themes=cc.get("competitor_themes", ""),
                competitor_assets=cc.get("competitor_assets", ""),
                competitive_noise=CompetitiveNoise(cc.get("competitive_noise", "Medium")),
            )
        
        local = None
        if data.get("local_factors"):
            lf = data["local_factors"]
            local = LocalFactors(
                cultural_notes=lf.get("cultural_notes", ""),
                media_behaviours=lf.get("media_behaviours", ""),
                regulatory_constraints=lf.get("regulatory_constraints", ""),
            )
        
        eval_input = EvaluationInput(
            creative=creative,
            brand_name=data["brand_name"],
            category=data["category"],
            campaign_objective=CampaignObjective(data["campaign_objective"]),
            primary_channels=data["primary_channels"],
            target_audience=data["target_audience"],
            brand_status=BrandStatus(data["brand_status"]),
            market_context=market_context,
            competitive_context=competitive,
            local_factors=local,
            existing_research=data.get("existing_research"),
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input format: {str(e)}")
    
    # Run evaluation
    try:
        result = await run_creative_evaluation(eval_input, query_llm)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@app.post("/api/creative/evaluate/stream")
async def evaluate_creative_stream(request: EvaluateRequest):
    """
    Run creative effectiveness evaluation with SSE streaming.
    Streams progress updates as each role completes evaluation.
    """
    # Validate input first
    data = request.model_dump()
    validation = validate_input(data)
    
    if not validation.valid:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Input validation failed",
                "missing_fields": validation.missing_fields,
                "incomplete_fields": validation.incomplete_fields,
            }
        )
    
    # Convert to EvaluationInput
    try:
        from .creative_effectiveness.models import (
            EvaluationInput, 
            CreativeAsset,
            MarketContext,
            BrandStatus,
            CampaignObjective,
            MarketMaturity,
            ClutterLevel,
            PurchaseFrequency,
            DecisionInvolvement,
            CompetitiveContext,
            CompetitiveNoise,
            LocalFactors,
        )
        
        creative = CreativeAsset(
            description=data["creative"].get("description", ""),
            file_path=data["creative"].get("file_path"),
            file_type=data["creative"].get("file_type"),
        )
        
        market = data["market_context"]
        market_context = MarketContext(
            market_maturity=MarketMaturity(market["market_maturity"]),
            category_clutter=ClutterLevel(market["category_clutter"]),
            purchase_frequency=PurchaseFrequency(market["purchase_frequency"]),
            decision_involvement=DecisionInvolvement(market["decision_involvement"]),
        )
        
        competitive = None
        if data.get("competitive_context"):
            cc = data["competitive_context"]
            competitive = CompetitiveContext(
                competitor_themes=cc.get("competitor_themes", ""),
                competitor_assets=cc.get("competitor_assets", ""),
                competitive_noise=CompetitiveNoise(cc.get("competitive_noise", "Medium")),
            )
        
        local = None
        if data.get("local_factors"):
            lf = data["local_factors"]
            local = LocalFactors(
                cultural_notes=lf.get("cultural_notes", ""),
                media_behaviours=lf.get("media_behaviours", ""),
                regulatory_constraints=lf.get("regulatory_constraints", ""),
            )
        
        eval_input = EvaluationInput(
            creative=creative,
            brand_name=data["brand_name"],
            category=data["category"],
            campaign_objective=CampaignObjective(data["campaign_objective"]),
            primary_channels=data["primary_channels"],
            target_audience=data["target_audience"],
            brand_status=BrandStatus(data["brand_status"]),
            market_context=market_context,
            competitive_context=competitive,
            local_factors=local,
            existing_research=data.get("existing_research"),
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid input format: {str(e)}")
    
    # Progress tracking for SSE
    role_results = []
    
    async def event_generator():
        queue = asyncio.Queue()
        role_results = []
        
        def on_role_complete(role_name, result, status="complete", justification=None):
            if status == "complete":
                event = {
                    'type': 'role_complete',
                    'role': {
                        "role_name": role_name,
                        "result": result.result,
                        "score": result.score,
                        "confidence": result.confidence,
                        "is_hard_gate": result.is_hard_gate,
                        "justification": result.justification,
                        "status": "complete"
                    },
                    'progress': len([r for r in role_results if r.get('status') == 'complete']) + 1
                }
                role_results.append({"role_name": role_name, "status": "complete"})
            else:
                event = {
                    'type': 'role_update',
                    'role': {
                        "role_name": role_name,
                        "status": status,
                        "justification": justification or (f"Model is currently {status}..." if status == "processing" else "Waiting in queue...")
                    }
                }
            queue.put_nowait(event)

        # Start evaluation in a background task
        eval_task = asyncio.create_task(run_creative_evaluation(
            eval_input, 
            query_llm,
            on_role_complete=on_role_complete
        ))

        try:
            # Send start event
            yield f"data: {json.dumps({'type': 'start', 'total_roles': 8})}\n\n"
            
            import time
            start_time = time.time()
            last_heartbeat = start_time
            
            # While evaluation is running or we have events in queue
            while not eval_task.done() or not queue.empty():
                try:
                    # Wait for an event from the queue with a timeout to check task status
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat ping every 5 seconds so frontend knows we're alive
                    now = time.time()
                    if now - last_heartbeat >= 5:
                        last_heartbeat = now
                        elapsed = int(now - start_time)
                        complete_count = len([r for r in role_results if r.get('status') == 'complete'])
                        yield f"data: {json.dumps({'type': 'heartbeat', 'elapsed_seconds': elapsed, 'completed': complete_count, 'total': 8})}\n\n"
                    continue
            
            # Get the final result
            result = await eval_task
            
            # Check for hard gate failure
            if result.hard_gate_failed:
                yield f"data: {json.dumps({'type': 'hard_gate_failed', 'role': result.failed_hard_gate_role})}\n\n"
            
            # Send final result
            yield f"data: {json.dumps({'type': 'complete', 'result': result.model_dump()})}\n\n"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            if not eval_task.done():
                eval_task.cancel()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/creative/config")
async def get_config():
    """Get current evaluation configuration."""
    backend = await get_active_backend()
    
    from .creative_effectiveness.roles import get_all_roles
    roles = get_all_roles()
    
    return {
        "llm_backend": backend,
        "use_gemini": USE_GEMINI,
        "roles": [
            {
                "id": r.id,
                "name": r.name,
                "short_name": r.short_name,
                "is_hard_gate": r.is_hard_gate,
                "framework_layers": r.framework_layers,
            }
            for r in roles
        ]
    }


class ExtractRequest(BaseModel):
    file_content: Optional[str] = None  # Base64 encoded
    file_url: Optional[str] = None
    file_name: str


@app.post("/api/creative/extract")
async def extract_from_document(request: ExtractRequest):
    """
    Auto-extract structured evaluation input from a document.
    """
    try:
        from .documents import extract_text_from_file
        import base64
        import httpx
        
        # 1. Decode and extract text
        if request.file_url:
            async with httpx.AsyncClient() as client:
                resp = await client.get(request.file_url)
                if resp.status_code != 200:
                    return {"error": f"Failed to download file from URL: {resp.status_code}"}
                content_bytes = resp.content
        elif request.file_content:
            content_bytes = base64.b64decode(request.file_content)
        else:
            return {"error": "Either file_content or file_url must be provided"}
            
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
        For example, if the document mentions "Moms aged 25-40," the target_audience should be that. 
        If the document is a script for a "Nike" ad, the brand_name is "Nike."
        Search the ENTIRE document text for these details.
        
        If you absolutely cannot infer it, leave it as null.
        
        Respond ONLY with valid JSON.
        """
        
        # 3. Call LLM
        from .config import GOOGLE_API_KEY, OPENROUTER_API_KEY, GEMINI_FLASH_MODEL
        
        if not GOOGLE_API_KEY and not OPENROUTER_API_KEY:
            return {"error": "API Key Missing: Please add GOOGLE_API_KEY or OPENROUTER_API_KEY to your .env file."}
            
        response = await query_llm([
            {"role": "system", "content": "You are a data extraction specialist. Output only valid JSON."},
            {"role": "user", "content": prompt}
        ], model=GEMINI_FLASH_MODEL)
        
        if not response:
            return {"error": "LLM extraction failed: The model returned an empty response or the API request failed. Check your API keys and quota."}
            
        content = response["content"]
        
        # 4. Clean and parse JSON
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        return {
            "data": json.loads(content.strip()),
            "reasoning": response.get("reasoning_details") or response.get("reasoning")
        }
        
    except Exception as e:
        print(f"Extraction error: {e}")
        return {"error": f"Extraction failed: {str(e)}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
