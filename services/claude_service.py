"""
Claude API service for intelligent query generation
"""
import json
import asyncio
import logging
from typing import List
import anthropic
from models import IndustryAnalysis, QueryRequest
from config import settings

logger = logging.getLogger(__name__)

class ClaudeService:
    """Service for interacting with Claude API"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def analyze_industry(self, industry: str, region: str) -> IndustryAnalysis:
        prompt = f"""Break down the {industry} industry into specific business subtypes and variations.

    Think step by step:
    1. What specific types of businesses operate within {industry}?
    2. What services do these companies actually offer?
    3. How do these businesses describe themselves on their websites?
    4. What technical terms and roles are common in this industry?

    For {industry}, provide real business categories, not generic terms.

    Return this exact JSON format:
    {{
        "core_terms": ["15+ specific business subtypes like 'digital lending platform', 'crypto exchange'"],
        "technical_terms": ["10+ technology and specialized terms used in this industry"],
        "role_titles": ["10+ job titles and decision maker roles"],
        "business_types": ["company structures and business models"],
        "related_industries": ["adjacent sectors and suppliers"],
        "regional_variations": {{}}
    }}

    Focus on how real companies describe their services. Return ONLY the JSON, no other text."""

        try:
            response = await asyncio.to_thread(
                lambda: self.client.messages.create(
                    model=settings.CLAUDE_MODEL,
                    max_tokens=1500,
                    messages=[{"role": "user", "content": prompt}]
                )
            )

            content = response.content[0].text.strip()
            print(f"DEBUG - Claude response: {content}")  # Debug line

            analysis_data = json.loads(content)
            return IndustryAnalysis(**analysis_data)

        except json.JSONDecodeError as e:
            print(f"DEBUG - JSON parsing failed: {e}")
            print(f"DEBUG - Raw content: {content}")
            return self._fallback_analysis(industry)

        except Exception as e:
            print(f"DEBUG - Industry analysis failed: {e}")
            return self._fallback_analysis(industry)

    def _fallback_analysis(self, industry: str) -> IndustryAnalysis:
        """Reliable fallback that always returns a valid object"""
        return IndustryAnalysis(
            core_terms=[
                f"{industry.lower()} business",
                f"{industry.lower()} company",
                f"{industry.lower()} service",
                f"{industry.lower()} platform",
                f"{industry.lower()} startup"
            ],
            technical_terms=[],
            role_titles=["CEO", "founder", "manager", "director"],
            business_types=["company", "startup", "firm"],
            related_industries=[],
            regional_variations={}
        )

    async def generate_email_optimized_queries(self, industry_data, geo_data, request):
        prompt = f"""Generate {request.top_k} Google search queries that find business websites containing email addresses.

        Business types: {industry_data.core_terms[:15]}
        Locations: {[geo_data.primary_city] + geo_data.neighborhoods[:8]}

        Use this structure:
        site:.com "business_type" "location" "@gmail.com"
        site:.org "business_type" "location" "@yahoo.com"  
        site:.net "business_type" "location" "@outlook.com"

        Requirements:
        - Rotate between .com, .org, .net domains
        - Use different business types from core terms
        - Use different locations
        - Vary email providers: @gmail.com, @yahoo.com, @outlook.com, @hotmail.com
        - Each query must be unique

        Return the queries as a single concatenated string with no spaces between queries.
        Format: query1query2query3...

        Generate exactly {request.top_k} queries."""

        try:
            response = await asyncio.to_thread(
                lambda: self.client.messages.create(
                    model=settings.CLAUDE_MODEL,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
            )

            content = response.content[0].text.strip()

            # Clean up Claude's response - remove any markdown or extra text
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Find JSON array in the response
            start = content.find("[")
            end = content.rfind("]") + 1
            if start != -1 and end != 0:
                json_content = content[start:end]
            else:
                json_content = content

            queries = json.loads(json_content)

            if isinstance(queries, list) and len(queries) > 0:
                logger.info(f"Claude generated {len(queries)} queries successfully")
                concatenated_queries = "".join(queries)
                return concatenated_queries
            else:
                raise ValueError("Invalid response format")

        except Exception as e:
            logger.error(f"Claude query generation failed: {e}, using fallback")
            # Simple but diverse fallback using Claude's industry analysis
            queries = []
            email_providers = settings.EMAIL_PROVIDERS
            terms = industry_data.core_terms[:15]
            locations = [geo_data.primary_city] + geo_data.neighborhoods[:10]

            for i in range(request.top_k):
                term = terms[i % len(terms)]
                location = locations[i % len(locations)]
                email = email_providers[i % len(email_providers)]
                query = f'"{term}" "{location}" @{email}'
                queries.append(query)

            return queries

    def _generate_fallback_queries(self, industry_data, geo_data, request):
        """Generate fallback queries that always work"""
        logger.info("Creating fallback queries")

        queries = []
        email_providers = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com", "live.com"]
        tlds = [".com", ".org", ".net"]

        # Use the core terms we know exist
        terms = industry_data.core_terms[:15] if industry_data.core_terms else ["business", "company", "service"]
        locations = [geo_data.primary_city] + geo_data.neighborhoods[:10]

        for i in range(request.top_k):
            term = terms[i % len(terms)]
            location = locations[i % len(locations)]
            email = email_providers[i % len(email_providers)]
            tld = tlds[i % len(tlds)]

            query = f'site:{tld} "{term}" "{location}" "@{email}"'
            queries.append(query)

        # Return concatenated string directly
        concatenated_queries = "".join(queries)
        return concatenated_queries


    def _queries_too_similar(self, queries: list) -> bool:
        """Check if queries are too repetitive"""
        if len(queries) < 3:
            return False

        # Count how many queries use the same base pattern
        base_patterns = []
        for query in queries[:5]:  # Check first 5
            # Extract pattern (remove quotes and specific terms)
            pattern = query.lower().replace('"', '')
            for provider in settings.EMAIL_PROVIDERS:
                pattern = pattern.replace(provider, 'EMAIL')
            base_patterns.append(pattern)

        # If more than 60% are the same pattern, it's too repetitive
        most_common = max(set(base_patterns), key=base_patterns.count)
        repetition_rate = base_patterns.count(most_common) / len(base_patterns)

        return repetition_rate > 0.6

    def _generate_diverse_fallback(self, industry_data, geo_data, request):
        """Generate diverse queries algorithmically"""
        queries = []
        patterns = [
            '"{term}" "{location}" @{email}',
            'site:{tld} "{term}" "{location}" @{email}',
            'filetype:pdf "{term}" "{location}" @{email}',
            '"{term}" "{location}" contact @{email}',
            '"{term} company" "{location}" @{email}'
        ]

        terms = industry_data.core_terms[:20] if industry_data.core_terms else ["business"]
        locations = ([geo_data.primary_city] + geo_data.neighborhoods + geo_data.metro_areas)[:15]
        emails = settings.EMAIL_PROVIDERS
        tlds = geo_data.business_tlds

        for i in range(request.top_k):
            pattern = patterns[i % len(patterns)]
            term = terms[i % len(terms)]
            location = locations[i % len(locations)]
            email = emails[i % len(emails)]
            tld = tlds[i % len(tlds)]

            query = pattern.format(term=term, location=location, email=email, tld=tld)
            queries.append(query)

        return queries