"""
Smart Query Builder - FastAPI Application with SERP Intelligence
"""
import logging
import time
import uuid
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import uvicorn

from services.claude_service import ClaudeService

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Request/Response Models
class QueryRequest(BaseModel):
    industry: str = Field(..., min_length=1, max_length=100, description="Industry or keyword to search")
    region: str = Field(..., min_length=1, max_length=100, description="Geographic region")
    top_k: int = Field(10, ge=1, le=50, description="Number of queries to generate")
    includes: Optional[List[str]] = Field(None, max_items=10, description="Terms to include")
    excludes: Optional[List[str]] = Field(None, max_items=10, description="Terms to exclude")

class QueryResponse(BaseModel):
    queries: List[str]
    meta: dict
    request_id: str

# Initialize FastAPI
app = FastAPI(
    title="Smart Query Builder",
    description="AI-powered search query generation with SERP intelligence",
    version="2.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
try:
    claude_service = ClaudeService()
    logger.info("Services initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize services: {e}")
    claude_service = None


@app.on_event("startup")
async def startup_event():
    """Validate configuration on startup"""
    logger.info("🚀 Smart Query Builder API starting...")

    # Check required environment variables
    required_vars = ['ANTHROPIC_API_KEY']
    optional_vars = ['SERP_API_KEY', 'CLAUDE_MODEL']

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        raise Exception(f"Missing required environment variables: {missing}")

    # Check optional variables
    for var in optional_vars:
        if not os.getenv(var):
            logger.warning(f"Optional variable {var} not set, using defaults")

    logger.info("✅ API ready with SERP intelligence!")


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "Smart Query Builder",
        "status": "operational",
        "version": "2.0.0",
        "features": {
            "serp_intelligence": bool(os.getenv('SERP_API_KEY')),
            "ai_model": os.getenv('CLAUDE_MODEL', 'claude-3-haiku-20240307')
        },
        "endpoints": {
            "build_queries": "/queries/build",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "services": {
            "claude": claude_service is not None,
            "serp": bool(os.getenv('SERP_API_KEY'))
        }
    }


@app.post("/queries/build", response_model=QueryResponse)
async def build_queries(request: QueryRequest):
    """
    Build intelligent search queries using SERP and AI

    Uses 1-2 SERP API calls to understand:
    - What businesses ARE the industry (not serve it)
    - Geographic intelligence about the location

    Returns queries in format: site:.com "business type" "location" "@email.com"
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]

    logger.info(f"[{request_id}] Building queries: {request.industry} in {request.region}")

    if not claude_service:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")

    try:
        # Generate intelligent queries with SERP context
        queries = await claude_service.generate_intelligent_queries(request)

        # Calculate execution time
        execution_time = time.time() - start_time

        # Build response
        response = QueryResponse(
            queries=queries,
            meta={
                "industry": request.industry,
                "region": request.region,
                "execution_time": round(execution_time, 2),
                "query_count": len(queries),
                "requested_count": request.top_k,
                "serp_enabled": bool(os.getenv('SERP_API_KEY')),
                "model_used": os.getenv('CLAUDE_MODEL', 'claude-3-haiku-20240307'),
                "timestamp": int(time.time())
            },
            request_id=request_id
        )

        logger.info(f"[{request_id}] Success! Generated {len(queries)} queries in {execution_time:.2f}s")

        return response

    except Exception as e:
        logger.error(f"[{request_id}] Failed: {e}")

        # Return a simple fallback response with proper format
        fallback_queries = []
        email_providers = ['@gmail.com', '@yahoo.com', '@outlook.com', '@hotmail.com']

        for i in range(min(request.top_k, 10)):
            provider = email_providers[i % len(email_providers)]
            # Use quoted format for fallback too
            query = f'"{request.industry}" "{request.region}" "{provider}"'
            fallback_queries.append(query)

        return QueryResponse(
            queries=fallback_queries,
            meta={
                "error": str(e),
                "fallback": True,
                "industry": request.industry,
                "region": request.region,
                "execution_time": round(time.time() - start_time, 2),
                "query_count": len(fallback_queries),
                "timestamp": int(time.time())
            },
            request_id=request_id
        )


@app.post("/queries/test")
async def test_serp_integration():
    """Test endpoint to verify SERP integration"""
    if not os.getenv('SERP_API_KEY'):
        return {
            "status": "SERP not configured",
            "message": "Add SERP_API_KEY to environment variables"
        }

    try:
        # Test with a simple query
        from services.Serp_service import SerpService
        serp = SerpService()
        context = await serp.get_intelligent_context("restaurant", "New York")

        return {
            "status": "SERP working",
            "sample_context": context
        }
    except Exception as e:
        return {
            "status": "SERP error",
            "error": str(e)
        }


@app.post("/queries/feedback")
async def query_feedback(feedback: dict):
    """
    Endpoint to receive feedback on query performance
    Can be used for future improvements

    Expected input:
    {
        "query": "site:.com \"restaurant\" \"NYC\" \"@gmail.com\"",
        "emails_found": 25,
        "quality_score": 8.5,
        "industry": "restaurant"
    }
    """
    # Log feedback for analysis
    logger.info(f"Feedback received: {feedback}")

    return {
        "status": "Feedback received",
        "message": "Thank you for the feedback"
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)