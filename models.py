"""
Data models for Smart Query Builder
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class QueryRequest(BaseModel):
    """What the user sends to our API"""
    industry: str = Field(..., description="Industry like 'FinTech' or 'Healthcare'")
    region: str = Field(..., description="Location like 'San Francisco' or 'New York'")
    top_k: Optional[int] = Field(default=15, description="Number of queries to generate")
    includes: Optional[List[str]] = Field(default=[], description="Must include these terms")
    excludes: Optional[List[str]] = Field(default=[], description="Must exclude these sites")
    personal_only: Optional[bool] = Field(default=False, description="Focus on personal emails")

class QueryResponse(BaseModel):
    """What we send back to the user"""
    queries: List[str] = Field(..., description="Generated search queries")
    meta: Dict[str, Any] = Field(..., description="Additional information")
    analytics: Dict[str, Any] = Field(..., description="Query statistics")
    request_id: str = Field(..., description="Unique request ID")

class IndustryAnalysis(BaseModel):
    """Claude's analysis of the industry"""
    core_terms: List[str] = Field(default=[], description="Main industry terms")
    technical_terms: List[str] = Field(default=[], description="Technical terms")
    role_titles: List[str] = Field(default=[], description="Job titles")
    business_types: List[str] = Field(default=[], description="Business types")
    related_industries: List[str] = Field(default=[], description="Related sectors")
    regional_variations: Dict[str, List[str]] = Field(default={}, description="Regional terms")

class GeographicData(BaseModel):
    """Geographic information about the location"""
    primary_city: str = Field(..., description="Main city name")
    neighborhoods: List[str] = Field(default=[], description="Local areas")
    metro_areas: List[str] = Field(default=[], description="Metro areas")
    local_names: List[str] = Field(default=[], description="Alternative names")
    country_code: str = Field(default="US", description="Country code")
    languages: List[str] = Field(default=["en"], description="Languages")
    business_tlds: List[str] = Field(default=[".com"], description="Common TLDs")

class QueryAnalytics(BaseModel):
    """Statistics about generated queries"""
    total_generated: int = Field(..., description="Number of queries generated")
    unique_terms_used: int = Field(..., description="Unique terms used")
    geographic_coverage: int = Field(..., description="Geographic variations")
    email_provider_distribution: Dict[str, int] = Field(..., description="Email provider spread")
    pattern_distribution: Dict[str, int] = Field(..., description="Query patterns used")
    estimated_coverage: str = Field(..., description="Coverage estimate")