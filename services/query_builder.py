"""
Main query builder service that coordinates all components
"""
import uuid
import time
import logging
from typing import Dict, Any
from models import QueryRequest, QueryResponse, QueryAnalytics
from services.claude_service import ClaudeService
from services.geo_service import GeographicService
from config import settings

logger = logging.getLogger(__name__)


class QueryBuilderService:
    """Main service that coordinates query building process"""

    def __init__(self):
        self.claude_service = ClaudeService()
        self.geo_service = GeographicService()

    async def build_queries(self, request: QueryRequest) -> QueryResponse:
        """
        Main method to build optimized search queries
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]

        logger.info(f"[{request_id}] Building queries for {request.industry} in {request.region}")

        try:
            # Step 1: Analyze industry for semantic expansion
            logger.info(f"[{request_id}] Analyzing industry: {request.industry}")
            industry_analysis = await self.claude_service.analyze_industry(
                request.industry,
                request.region
            )

            # Step 2: Resolve geographic intelligence
            logger.info(f"[{request_id}] Resolving geography: {request.region}")
            geographic_data = await self.geo_service.resolve_geography(request.region)

            # Step 3: Generate optimized queries using Claude
            logger.info(f"[{request_id}] Generating {request.top_k} optimized queries")
            queries = await self.claude_service.generate_email_optimized_queries(
                industry_analysis,
                geographic_data,
                request
            )

            # Step 4: Analyze and enhance generated queries
            final_queries = self._post_process_queries(queries, request)

            # Step 5: Generate analytics and metadata
            analytics = self._generate_analytics(
                final_queries,
                industry_analysis,
                geographic_data,
                request
            )

            execution_time = time.time() - start_time

            # Build response
            response = QueryResponse(
                queries=final_queries,
                meta={
                    "industry_analysis": industry_analysis.dict(),
                    "geographic_data": geographic_data.dict(),
                    "execution_time_seconds": round(execution_time, 2),
                    "query_count": len(final_queries),
                    "model_used": settings.CLAUDE_MODEL,
                    "timestamp": int(time.time())
                },
                analytics=analytics.dict(),
                request_id=request_id
            )

            logger.info(f"[{request_id}] Successfully generated {len(final_queries)} queries in {execution_time:.2f}s")
            return response

        except Exception as e:
            logger.error(f"[{request_id}] Query building failed: {e}")
            # Return fallback response
            return self._create_fallback_response(request, request_id, str(e))

    def _post_process_queries(self, queries: list, request: QueryRequest) -> list:
        """
        Post-process and enhance generated queries
        """
        processed_queries = []
        seen_patterns = set()

        for query in queries:
            # Clean and validate
            cleaned_query = query.strip()
            if len(cleaned_query) < 10:
                continue

            # Remove duplicates (by pattern similarity)
            query_pattern = self._extract_pattern(cleaned_query)
            if query_pattern in seen_patterns:
                continue
            seen_patterns.add(query_pattern)

            # Apply user-specified includes/excludes
            if request.includes:
                # Check if any include terms are present
                if not any(term.lower() in cleaned_query.lower() for term in request.includes):
                    continue

            # Add excludes to query if specified
            if request.excludes:
                exclude_terms = " ".join([f'-site:{term}' for term in request.excludes if term])
                if exclude_terms and exclude_terms not in cleaned_query:
                    cleaned_query += f" {exclude_terms}"

            processed_queries.append(cleaned_query)

        # Ensure we have the requested number of queries
        while len(processed_queries) < request.top_k and len(processed_queries) < len(queries):
            # Add back some queries if we filtered too many
            break

        return processed_queries[:request.top_k]

    def _extract_pattern(self, query: str) -> str:
        """
        Extract pattern from query for deduplication
        """
        # Remove specific terms to identify pattern similarity
        pattern = query.lower()

        # Remove email providers
        for provider in settings.EMAIL_PROVIDERS:
            pattern = pattern.replace(provider, "EMAIL")

        # Remove quotes and specific terms
        pattern = pattern.replace('"', '').replace("'", '')

        # Extract base structure
        words = pattern.split()
        structure_words = [w for w in words if w in ['site:', 'intitle:', 'inurl:', 'filetype:', 'intext:']]

        return " ".join(structure_words)

    def _generate_analytics(self,
                            queries: list,
                            industry_analysis,
                            geographic_data,
                            request: QueryRequest) -> QueryAnalytics:
        """
        Generate analytics about the query generation process
        """
        # Count unique terms used
        all_terms = set()
        for query in queries:
            words = query.lower().replace('"', '').split()
            all_terms.update(words)

        # Email provider distribution
        email_distribution = {}
        for provider in settings.EMAIL_PROVIDERS:
            count = sum(1 for query in queries if provider in query)
            if count > 0:
                email_distribution[provider] = count

        # Pattern distribution
        pattern_distribution = {}
        for query in queries:
            if 'site:' in query:
                pattern_distribution['site_targeted'] = pattern_distribution.get('site_targeted', 0) + 1
            if 'filetype:' in query:
                pattern_distribution['document_search'] = pattern_distribution.get('document_search', 0) + 1
            if 'intitle:' in query:
                pattern_distribution['title_search'] = pattern_distribution.get('title_search', 0) + 1
            if 'inurl:' in query:
                pattern_distribution['url_search'] = pattern_distribution.get('url_search', 0) + 1

        # Geographic coverage
        geo_terms_used = len([
            term for term in all_terms
            if term in [geographic_data.primary_city.lower()] +
               [area.lower() for area in geographic_data.neighborhoods + geographic_data.metro_areas]
        ])

        return QueryAnalytics(
            total_generated=len(queries),
            unique_terms_used=len(all_terms),
            geographic_coverage=geo_terms_used,
            email_provider_distribution=email_distribution,
            pattern_distribution=pattern_distribution,
            estimated_coverage=self._estimate_coverage(queries, industry_analysis, geographic_data)
        )

    def _estimate_coverage(self, queries: list, industry_analysis, geographic_data) -> str:
        """
        Estimate the search coverage based on query diversity
        """
        diversity_score = 0

        # Industry term diversity
        industry_terms_covered = len(industry_analysis.core_terms) + len(industry_analysis.technical_terms)
        diversity_score += min(industry_terms_covered / 10, 1.0) * 30

        # Geographic diversity
        geo_terms_covered = len(geographic_data.neighborhoods) + len(geographic_data.metro_areas)
        diversity_score += min(geo_terms_covered / 5, 1.0) * 25

        # Query pattern diversity
        unique_patterns = len(set(self._extract_pattern(q) for q in queries))
        diversity_score += min(unique_patterns / 5, 1.0) * 25

        # Email provider distribution
        providers_used = len([p for p in settings.EMAIL_PROVIDERS if any(p in q for q in queries)])
        diversity_score += min(providers_used / len(settings.EMAIL_PROVIDERS), 1.0) * 20

        if diversity_score >= 80:
            return "Excellent (80%+ coverage)"
        elif diversity_score >= 60:
            return "Good (60-80% coverage)"
        elif diversity_score >= 40:
            return "Fair (40-60% coverage)"
        else:
            return "Limited (<40% coverage)"

    def _create_fallback_response(self, request: QueryRequest, request_id: str, error: str) -> QueryResponse:
        """
        Create a fallback response when main processing fails
        """
        # Generate basic fallback queries
        fallback_queries = []

        for i, provider in enumerate(settings.EMAIL_PROVIDERS[:request.top_k]):
            query = f'site:.com "{request.industry}" "{request.region}" "@{provider}"'
            fallback_queries.append(query)

        # Pad with additional basic queries if needed
        while len(fallback_queries) < request.top_k:
            provider = settings.EMAIL_PROVIDERS[len(fallback_queries) % len(settings.EMAIL_PROVIDERS)]
            query = f'"{request.industry}" "{request.region}" "@{provider}"'
            fallback_queries.append(query)

        fallback_analytics = QueryAnalytics(
            total_generated=len(fallback_queries),
            unique_terms_used=3,  # Basic estimate
            geographic_coverage=1,
            email_provider_distribution={provider: 1 for provider in settings.EMAIL_PROVIDERS[:request.top_k]},
            pattern_distribution={"basic": len(fallback_queries)},
            estimated_coverage="Limited (fallback mode)"
        )

        return QueryResponse(
            queries=fallback_queries,
            meta={
                "error": error,
                "fallback_mode": True,
                "industry": request.industry,
                "region": request.region,
                "query_count": len(fallback_queries),
                "timestamp": int(time.time())
            },
            analytics=fallback_analytics.dict(),
            request_id=request_id
        )