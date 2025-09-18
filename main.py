"""
Smart Query Builder - FastAPI Application
"""
import logging
import time
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from models import QueryRequest, QueryResponse, QueryAnalytics
from services.claude_service import ClaudeService
from services.geo_service import GeographicService
from config import settings, validate_config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Smart Query Builder",
    description="AI-powered search query generation for contact discovery",
    version="1.0.0"
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
claude_service = ClaudeService()
geo_service = GeographicService()


@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Smart Query Builder API starting...")
    if not validate_config():
        raise Exception("Configuration validation failed")
    logger.info("✅ API ready!")


@app.get("/")
async def root():
    return {
        "service": "Smart Query Builder",
        "status": "operational",
        "version": "1.0.0",
        "endpoints": {
            "build_queries": "/queries/build",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": int(time.time()),
        "claude_model": settings.CLAUDE_MODEL
    }


@app.post("/queries/build")
async def build_queries(request: QueryRequest):
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]

    logger.info(f"[{request_id}] Building queries: {request.industry} in {request.region}")

    try:
        # Step 1: Analyze industry
        industry_analysis = await claude_service.analyze_industry(
            request.industry,
            request.region
        )
        logger.info(f"[{request_id}] Industry analysis complete: {len(industry_analysis.core_terms)} core terms")

        # Step 2: Resolve geography
        geo_data = await geo_service.resolve_geography(request.region)
        logger.info(f"[{request_id}] Geographic resolution complete: {geo_data.primary_city}")

        # Step 3: Generate queries
        queries = await claude_service.generate_email_optimized_queries(
            industry_analysis,
            geo_data,
            request
        )
        logger.info(f"[{request_id}] Query generation complete: {len(queries)} queries")

        # Step 4: Build response (simplified)
        execution_time = time.time() - start_time

        # In main.py, update the response building:
        response = {
            "queries": queries,  # This is now a single string
            "meta": {
                "industry_analysis": {
                    "core_terms": industry_analysis.core_terms[:10],  # Limit for response size
                    "technical_terms": industry_analysis.technical_terms[:10],
                    "role_titles": industry_analysis.role_titles[:10]
                },
                "geographic_data": {
                    "primary_city": geo_data.primary_city,
                    "neighborhoods": geo_data.neighborhoods[:5],
                    "metro_areas": geo_data.metro_areas[:5]
                },
                "execution_time": round(execution_time, 2),
                "model_used": settings.CLAUDE_MODEL
            },
            "analytics": {
                "total_generated": request.top_k,
                "query_length": len(queries),
                "estimated_coverage": "Query generation successful"
            },
            "request_id": request_id
        }

        logger.info(f"[{request_id}] Success! Generated {len(queries)} queries in {execution_time:.2f}s")
        return response

    except Exception as e:
        logger.error(f"[{request_id}] Failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/queries/feedback")
async def query_feedback(feedback: dict):
    """
    Learn from query performance to improve future rankings

    Expected input:
    {
        "query": "site:.com \"hospital\" \"NYC\" \"@gmail.com\"",
        "emails_found": 25,
        "quality_score": 8.5,
        "industry": "healthcare"
    }
    """


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)