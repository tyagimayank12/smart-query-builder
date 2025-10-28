"""
Claude Service - AI-powered query generation with SERP intelligence
"""
import os
import logging
from typing import List, Dict, Optional
from anthropic import Anthropic
from models import IndustryAnalysis, GeographicData, QueryRequest
from services.Serp_service import SerpService


logger = logging.getLogger(__name__)


class ClaudeService:
    """
    Claude service that uses SERP intelligence for smart query generation
    """

    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.client = Anthropic(api_key=api_key)
        self.model = os.getenv('CLAUDE_MODEL', 'claude-3-haiku-20240307')
        self.serp_service = SerpService()

        logger.info(f"Claude service initialized with model: {self.model}")

    async def generate_intelligent_queries(self, request: QueryRequest) -> List[str]:
        """
        Generate queries using SERP intelligence - no hardcoding, pure intelligence
        """

        # Get intelligent context from SERP (1 API call)
        logger.info(f"Fetching intelligent context for {request.industry} in {request.region}")
        context = await self.serp_service.get_intelligent_context(
            request.industry,
            request.region
        )

        # Build the intelligent prompt with SERP insights
        prompt = f"""
        Generate EXACTLY {request.top_k} Google search queries to find email contacts.
        
        Target: {request.industry} businesses in {request.region}
        
        INTELLIGENT CONTEXT FROM MARKET DATA:
        - Business types that ARE this industry: {context['primary_business_types']}
        - Related terms used in market: {context['keyword_variations']}
        - Geographic areas to target: {context['location_areas']}
        - Successful patterns: {context['search_patterns']}
        - Business type: {'B2B' if context['is_b2b'] else 'B2C/Mixed'}
        
        GENERATION RULES:
        1. Focus on businesses that ARE "{request.industry}" not those that serve it
        2. Use the discovered business types and variations from market data
        3. Include location variants: {request.region} and discovered areas
        4. Email providers MUST be in quotes: "@gmail.com", "@yahoo.com", "@outlook.com"
        5. Mix search operators: site:, intitle:, inurl:, "exact phrases"
        
        CRITICAL FORMAT: All parameters must be within quotes:
        - Business type: "Real Estate Agency"
        - Location: "Manhattan"
        - Email: "@gmail.com"
        Example: site:.com "Real Estate Agency" "Manhattan" "@gmail.com"
        
        {"MUST INCLUDE: " + str(request.includes) if request.includes else ""}
        {"MUST EXCLUDE: " + str(request.excludes) if request.excludes else ""}
        
        Create diverse, non-repetitive queries that would actually find {request.industry} email contacts.
        
        OUTPUT: Return EXACTLY {request.top_k} queries, one per line, no numbering, no explanations.
        """

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse response
            content = response.content[0].text if response.content else ""
            queries = [q.strip() for q in content.strip().split('\n') if q.strip()]

            # Remove any numbering if present
            cleaned_queries = []
            for query in queries:
                # Remove leading numbers like "1. " or "1) "
                import re
                cleaned = re.sub(r'^\d+[\.\)]\s*', '', query)
                if cleaned and not cleaned.startswith('#'):  # Skip comments
                    cleaned_queries.append(cleaned)

            # Apply includes/excludes if specified
            final_queries = self._apply_filters(cleaned_queries, request)

            # Ensure exactly top_k queries
            if len(final_queries) < request.top_k:
                logger.warning(f"Generated only {len(final_queries)} queries, requested {request.top_k}")
                # Generate a few more if needed
                final_queries = self._generate_fallback_queries(
                    final_queries,
                    request,
                    context
                )

            return final_queries[:request.top_k]

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            # Fallback to basic queries using context
            return self._create_fallback_queries(request, context)

    async def analyze_industry(self, industry: str, region: str) -> IndustryAnalysis:
        """
        Analyze industry using SERP context
        """
        # Get context from SERP
        context = await self.serp_service.get_intelligent_context(industry, region)

        # Build analysis from SERP data
        return IndustryAnalysis(
            core_terms=context.get('keyword_variations', [industry]),
            technical_terms=[],  # Could enhance with another API call if needed
            role_titles=self._generate_role_titles(industry, context),
            business_types=context.get('primary_business_types', []),
            is_b2b=context.get('is_b2b', False)
        )

    def _generate_role_titles(self, industry: str, context: Dict) -> List[str]:
        """
        Generate role titles based on industry and context
        """
        base_titles = ['owner', 'manager', 'director', 'CEO', 'founder']

        # Add industry-specific titles
        if context.get('is_b2b'):
            base_titles.extend(['sales director', 'business development', 'account manager'])

        # Combine with industry
        role_titles = []
        for title in base_titles[:5]:
            role_titles.append(f"{industry} {title}")

        return role_titles

    def _apply_filters(self, queries: List[str], request: QueryRequest) -> List[str]:
        """
        Apply include/exclude filters to queries
        """
        filtered = []

        for query in queries:
            # Check excludes
            if request.excludes:
                if any(exclude.lower() in query.lower() for exclude in request.excludes):
                    continue

            # Check includes (if specified, at least one must be present)
            if request.includes:
                if not any(include.lower() in query.lower() for include in request.includes):
                    # Add the include term if not present
                    query = f'{query} "{request.includes[0]}"'

            filtered.append(query)

        return filtered

    def _generate_fallback_queries(self,
                                   existing_queries: List[str],
                                   request: QueryRequest,
                                   context: Dict) -> List[str]:
        """
        Generate additional queries if we don't have enough
        """
        queries = existing_queries.copy()

        # Use context to generate more variations
        email_domains = context['suggested_email_domains']
        business_types = context['primary_business_types']
        areas = context['location_areas']
        variations = context['keyword_variations']

        while len(queries) < request.top_k:
            # Rotate through patterns
            idx = len(queries) % len(email_domains)
            email = email_domains[idx]

            business_type = business_types[idx % len(business_types)] if business_types else "company"
            area = areas[idx % len(areas)] if areas else request.region
            variation = variations[idx % len(variations)] if variations else request.industry

            # Generate different patterns - ALL with quoted emails
            patterns = [
                f'"{variation} {business_type}" "{area}" "{email}"',
                f'site:.com "{variation}" "{area}" "{email}"',
                f'intitle:"{variation}" "{area}" email "{email}"',
                f'"{business_type}" "{variation}" "{area}" contact "{email}"'
            ]

            # Use a pattern we haven't used yet
            query = patterns[len(queries) % len(patterns)]

            if query not in queries:
                queries.append(query)

        return queries

    def _create_fallback_queries(self, request: QueryRequest, context: Dict) -> List[str]:
        """
        Create basic fallback queries when Claude API fails
        """
        queries = []

        # Use the SERP context even in fallback
        email_domains = context.get('suggested_email_domains', ['@gmail.com', '@yahoo.com'])
        areas = context.get('location_areas', [request.region])
        business_types = context.get('primary_business_types', ['company', 'services'])
        variations = context.get('keyword_variations', [request.industry])

        for i in range(request.top_k):
            email = email_domains[i % len(email_domains)]
            area = areas[i % len(areas)]
            business_type = business_types[i % len(business_types)]
            keyword = variations[i % len(variations)]

            # Mix different patterns - ALL with quoted emails
            if i % 4 == 0:
                query = f'site:.com "{keyword} {business_type}" "{area}" "{email}"'
            elif i % 4 == 1:
                query = f'"{keyword}" "{area}" "{email}" contact'
            elif i % 4 == 2:
                query = f'intitle:"{keyword}" "{area}" email "{email}"'
            else:
                query = f'"{business_type}" "{keyword}" "{area}" "{email}"'

            queries.append(query)

        return queries[:request.top_k]

    async def generate_email_optimized_queries(self,
                                              industry_analysis: IndustryAnalysis,
                                              geographic_data: GeographicData,
                                              request: QueryRequest) -> List[str]:
        """
        Legacy method - redirects to new intelligent method
        """
        return await self.generate_intelligent_queries(request)