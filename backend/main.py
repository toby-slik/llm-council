"""FastAPI backend for Creative Effectiveness Evaluation System."""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from .creative_effectiveness.models import EvaluationInput, EvaluationResult
from .creative_effectiveness.validation import validate_input, ValidationResult
from .creative_effectiveness.evaluation import run_creative_evaluation
from .llm import query_llm, get_active_backend
from .config import USE_GEMINI

app = FastAPI(title="Creative Effectiveness Evaluation API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
        try:
            yield f"data: {json.dumps({'type': 'start', 'total_roles': 8})}\\n\\n"
            
            def on_role_complete(role_name, result):
                role_results.append({
                    "role_name": role_name,
                    "result": result.result,
                    "score": result.score,
                    "confidence": result.confidence,
                    "is_hard_gate": result.is_hard_gate,
                })
            
            # Run evaluation with progress callback
            result = await run_creative_evaluation(
                eval_input, 
                query_llm,
                on_role_complete=on_role_complete
            )
            
            # Send role completion events
            for i, role_result in enumerate(role_results):
                yield f"data: {json.dumps({'type': 'role_complete', 'role': role_result, 'progress': i + 1})}\\n\\n"
            
            # Check for hard gate failure
            if result.hard_gate_failed:
                yield f"data: {json.dumps({'type': 'hard_gate_failed', 'role': result.failed_hard_gate_role})}\\n\\n"
            
            # Send final result
            yield f"data: {json.dumps({'type': 'complete', 'result': result.model_dump()})}\\n\\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\\n\\n"
    
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
