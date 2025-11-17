
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import time
import uuid

# Import your services
from services.claude_service import ClaudeService
from services.Serp_service import SerpService  # If you have it

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Smart Query Builder",
    description="Generate intelligent Google search queries for B2C lead generation",
    version="2.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class QueryRequest(BaseModel):
    industry: str
    region: str
    top_k: int = 10

# Initialize services
claude_service = ClaudeService()

# Try to initialize SERP service if available
try:
    serp_service = SerpService()
    SERP_ENABLED = True
    logger.info("✅ SERP service enabled")
except Exception as e:
    serp_service = None
    SERP_ENABLED = False
    logger.warning(f"⚠️  SERP service disabled: {e}")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Smart Query Builder API",
        "status": "running",
        "version": "2.0",
        "features": {
            "serp_intelligence": SERP_ENABLED,
            "b2c_focus": True,
            "claude_model": claude_service.model
        }
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "serp_enabled": SERP_ENABLED
    }


@app.post("/queries/build")
async def build_queries(request: QueryRequest):
    """
    Generate intelligent B2C search queries

    CORRECT implementation showing how to call ClaudeService
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]

    logger.info(f"[{request_id}] Building queries: {request.industry} in {request.region}")

    try:
        # Step 1: Get SERP context (optional but recommended)
        serp_context = None
        if SERP_ENABLED and serp_service:
            try:
                logger.info(f"[{request_id}] Fetching SERP context...")
                serp_context = await serp_service.get_intelligent_context(
                    request.industry,
                    request.region
                )
                logger.info(f"[{request_id}] SERP context fetched")
            except Exception as e:
                logger.warning(f"[{request_id}] SERP fetch failed: {e}")

        # Step 2: Generate queries with Claude
        # THIS IS THE CRITICAL PART - HOW TO CALL IT CORRECTLY
        logger.info(f"[{request_id}] Calling Claude service...")

        queries = claude_service.generate_intelligent_queries(
            industry=request.industry,    # REQUIRED
            region=request.region,        # REQUIRED
            top_k=request.top_k,          # Optional, defaults to 10
            serp_context=serp_context     # Optional
        )

        logger.info(f"[{request_id}] Generated {len(queries)} queries")

        # Step 3: Build response
        execution_time = time.time() - start_time

        response = {
            "queries": queries,
            "meta": {
                "industry": request.industry,
                "region": request.region,
                "execution_time": round(execution_time, 2),
                "query_count": len(queries),
                "requested_count": request.top_k,
                "serp_enabled": SERP_ENABLED,
                "model_used": claude_service.model,
                "timestamp": int(time.time())
            },
            "request_id": request_id
        }

        logger.info(f"[{request_id}] Success! Generated {len(queries)} queries in {execution_time:.2f}s")
        return response

    except Exception as e:
        logger.error(f"[{request_id}] Error: {str(e)}", exc_info=True)

        # Return error with fallback
        execution_time = time.time() - start_time

        return {
            "queries": [],
            "meta": {
                "error": str(e),
                "fallback": True,
                "industry": request.industry,
                "region": request.region,
                "execution_time": round(execution_time, 2),
                "query_count": 0,
                "timestamp": int(time.time())
            },
            "request_id": request_id
        }


# Run with: uvicorn main:app --host 0.0.0.0 --port 8000
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)