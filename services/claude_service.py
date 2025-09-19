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
        """
        Deep industry analysis that generates specific business types, not generic terms
        """
        prompt = f"""You are a business intelligence expert analyzing the {industry} industry to identify REAL business types.

    Your goal: Break down {industry} into specific business categories that actually exist and operate.

    Think like a business directory expert:
    1. What specific types of businesses operate within {industry}?
    2. How do companies in this space differentiate their services?
    3. What specializations or niches exist?
    4. What would customers search for when looking for these services?
    5. What terms do these businesses use to describe themselves?

    CRITICAL: Avoid generic terms like "{industry.lower()} business", "{industry.lower()} company", "{industry.lower()} service"

    Instead, provide SPECIFIC business categories that real companies use:

    Examples of specificity:
    - Instead of "healthcare business" → "hospital", "dental clinic", "urgent care center"
    - Instead of "real estate company" → "real estate brokerage", "property management company", "commercial real estate firm"
    - Instead of "technology business" → "software development company", "IT consulting firm", "cybersecurity company"

    Analyze {industry} in {region} and provide:

    {{
        "core_terms": [
            "15-20 specific business types that actually exist in {industry}",
            "use real business categories that appear in directories",
            "terms that businesses use to describe themselves",
            "specific service types within this industry"
        ],
        "technical_terms": [
            "industry-specific technology terms",
            "specialized equipment or software",
            "regulatory compliance terms",
            "certifications and standards",
            "technical processes used in this industry"
        ],
        "role_titles": [
            "C-level executives (CEO, CTO, CFO)",
            "department heads and managers", 
            "specialized professional roles",
            "decision maker positions",
            "industry-specific job titles"
        ],
        "business_types": [
            "organizational structures (LLC, corporation, partnership)",
            "business models (B2B, B2C, franchise)",
            "company sizes (startup, SME, enterprise)",
            "ownership types (private, public, family-owned)"
        ],
        "related_industries": [
            "supplier industries",
            "partner sectors",
            "adjacent markets",
            "supporting services",
            "complementary businesses"
        ],
        "regional_variations": {{}}
    }}

    Focus on terms that real businesses use on their websites and in their marketing.
    Return ONLY valid JSON with no additional text."""

        try:
            response = await asyncio.to_thread(
                lambda: self.client.messages.create(
                    model=settings.CLAUDE_MODEL,
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}]
                )
            )

            content = response.content[0].text.strip()
            logger.info(f"Claude industry analysis response: {len(content)} characters")

            # Clean JSON extraction
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Find JSON object in response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end != 0:
                json_content = content[start:end]
            else:
                json_content = content

            analysis_data = json.loads(json_content)

            # Validate that we have specific terms, not generic ones
            core_terms = analysis_data.get("core_terms", [])
            filtered_terms = [
                term for term in core_terms
                if not any(generic in term.lower() for generic in [
                    f"{industry.lower()} business",
                    f"{industry.lower()} company",
                    f"{industry.lower()} service",
                    f"{industry.lower()} firm"
                ])
            ]

            # If we filtered out too many generic terms, keep some but log warning
            if len(filtered_terms) < 5:
                logger.warning(f"Industry analysis for {industry} returned mostly generic terms")
                analysis_data["core_terms"] = core_terms[:15]  # Keep original
            else:
                analysis_data["core_terms"] = filtered_terms[:15]  # Use filtered

            return IndustryAnalysis(**analysis_data)

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed for industry analysis: {e}")
            logger.error(f"Raw Claude response: {content[:500]}...")
            return self._fallback_industry_analysis(industry)

        except Exception as e:
            logger.error(f"Claude industry analysis failed: {e}")
            return self._fallback_industry_analysis(industry)

    def _fallback_industry_analysis(self, industry: str) -> IndustryAnalysis:
        """Fallback with some intelligence based on common industry patterns"""

        # Basic industry-specific fallbacks
        industry_fallbacks = {
            "healthcare": ["hospital", "medical clinic", "dental practice", "urgent care center",
                           "physical therapy clinic"],
            "fintech": ["digital bank", "payment processor", "crypto exchange", "lending platform", "robo advisor"],
            "real estate": ["real estate brokerage", "property management company", "commercial real estate firm",
                            "residential real estate agency"],
            "education": ["private school", "tutoring center", "online learning platform",
                          "vocational training institute"],
            "retail": ["clothing store", "electronics retailer", "grocery store", "specialty retail shop"],
            "food": ["restaurant", "catering company", "food truck", "bakery", "cafe"],
            "technology": ["software development company", "IT consulting firm", "cybersecurity company",
                           "web design agency"]
        }

        # Get specific terms for the industry or use generic pattern
        core_terms = industry_fallbacks.get(
            industry.lower(),
            [f"{industry} specialist", f"{industry} consultant", f"{industry} provider"]
        )

        return IndustryAnalysis(
            core_terms=core_terms + [f"{industry.lower()} company", f"{industry.lower()} business"],
            technical_terms=["technology", "software", "digital platform", "automation"],
            role_titles=["CEO", "founder", "president", "director", "manager", "owner"],
            business_types=["company", "corporation", "LLC", "partnership", "startup"],
            related_industries=["consulting", "technology", "marketing", "finance"],
            regional_variations={}
        )

    # In your claude_service.py, find this method and replace the return statement:

    async def generate_email_optimized_queries(self, industry_data, geo_data, request):
        prompt = f"""You are a search optimization expert. Generate and rank the MOST EFFECTIVE search queries.

        Available elements:
        Business types: {industry_data.core_terms[:20]}
        Locations: {[geo_data.primary_city] + geo_data.neighborhoods[:10] + geo_data.metro_areas[:5]}
        Email providers: gmail.com, yahoo.com, outlook.com, hotmail.com, aol.com, live.com
        TLD options: .com, .org, .net

        Your task: Generate {request.top_k * 3} potential queries, then select the BEST {request.top_k} based on these criteria:

        RANKING FACTORS:
        1. Business term specificity (specific > generic)
        2. Location coverage (major city + neighborhoods)
        3. Email provider diversity
        4. Query uniqueness (avoid similar patterns)
        5. Search volume potential (popular terms > obscure terms)

        PATTERNS TO USE:
        - site:.com "business_type" "location" "@email_provider"
        - site:.org "business_type" "location" "@email_provider"  
        - "business_type" "major_city" "@email_provider"
        - "business_type" "neighborhood" "@email_provider"

        OPTIMIZATION STRATEGY:
        - Prioritize specific business types that actually exist
        - Balance major cities with neighborhoods for coverage
        - Distribute email providers evenly
        - Avoid redundant location-business combinations
        - Select queries with highest discovery potential

        Generate and internally rank queries, then return the TOP {request.top_k} most effective ones.

        Return JSON array: ["top_ranked_query1", "top_ranked_query2", ...]"""

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
                # ✅ FIXED: Return the array directly, don't concatenate
                return queries  # This was the issue!
            else:
                raise ValueError("Invalid response format")

        except Exception as e:
            logger.error(f"Claude query generation failed: {e}, using fallback")
            # ✅ FIXED: Fallback should also return array
            return self._generate_fallback_queries_array(industry_data, geo_data, request)

    # ✅ NEW: Add this method to your ClaudeService class
    def _generate_fallback_queries_array(self, industry_data, geo_data, request):
        """Generate fallback queries as array (not concatenated string)"""
        logger.info("Creating fallback queries as array")

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

        # ✅ Return array, not concatenated string
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


        return queries


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