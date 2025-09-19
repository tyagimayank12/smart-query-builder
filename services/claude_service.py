"""
Claude API service for intelligent query generation
Industry-agnostic with robust error handling and dynamic fallbacks
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
        Industry analysis with improved prompt engineering and robust error handling
        """
        prompt = f"""Analyze the "{industry}" industry. You are an expert business analyst.

TASK: Identify specific business types, roles, and terms in the {industry} industry.

RULES:
1. Focus on REAL business types that actually exist
2. Avoid generic terms like "{industry.lower()} business" or "{industry.lower()} company"  
3. Think about what customers search for when looking for these services
4. Consider different specializations within this industry
5. Use terms that real businesses use on their websites and marketing

EXAMPLES of specificity:
- Instead of "healthcare business" → "hospital", "dental clinic", "urgent care center"
- Instead of "real estate company" → "real estate brokerage", "property management company"
- Instead of "technology business" → "software development company", "IT consulting firm"

OUTPUT FORMAT: Return valid JSON with exactly these fields:

{{
    "core_terms": [
        "List 10-15 specific business types that actually exist in {industry}",
        "Use terms that real businesses use to describe themselves",
        "Focus on searchable, specific business categories"
    ],
    "technical_terms": [
        "Industry-specific technology, equipment, software",
        "Certification names, standards, regulatory terms",
        "Technical processes and methodologies"
    ],
    "role_titles": [
        "CEO", "President", "Director", "Manager",
        "Industry-specific job titles and decision-maker positions"
    ],
    "business_types": [
        "LLC", "Corporation", "Partnership", "Franchise",
        "Organizational structures and business models"
    ],
    "related_industries": [
        "Industries that work with {industry}",
        "Supplier industries and adjacent markets",
        "Supporting services and complementary businesses"
    ],
    "regional_variations": {{}}
}}

Industry to analyze: {industry}
Region: {region}

Return only the JSON object. No explanations, markdown, or additional text."""

        try:
            response = await asyncio.to_thread(
                lambda: self.client.messages.create(
                    model=settings.CLAUDE_MODEL,
                    max_tokens=1500,  # Reduced for more concise output
                    temperature=0.3,   # Lower temperature for consistency
                    messages=[{"role": "user", "content": prompt}]
                )
            )

            content = response.content[0].text.strip()
            logger.info(f"Claude industry analysis response: {len(content)} characters")

            # Extract and validate JSON
            json_content = self._extract_json_safely(content)
            logger.debug(f"Extracted JSON preview: {json_content[:200]}...")

            try:
                analysis_data = json.loads(json_content)
                logger.info(f"Successfully parsed JSON with keys: {list(analysis_data.keys())}")

                # Validate and clean the data structure
                validated_data = self._validate_analysis_structure(analysis_data, industry)

                return IndustryAnalysis(**validated_data)

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode failed for '{industry}': {e}")
                logger.error(f"Problematic JSON content: {json_content[:300]}...")
                return self._create_intelligent_fallback(industry, region)

        except Exception as e:
            logger.error(f"Claude industry analysis failed for '{industry}': {str(e)}")
            return self._create_intelligent_fallback(industry, region)

    def _extract_json_safely(self, content: str) -> str:
        """Extract JSON from Claude response safely"""
        # Remove markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # Find JSON object boundaries
        start = content.find("{")
        end = content.rfind("}") + 1

        if start != -1 and end != 0:
            return content[start:end]
        else:
            # If no clear JSON boundaries, try the whole content
            return content

    def _validate_analysis_structure(self, data: dict, industry: str) -> dict:
        """Ensure the data matches our expected structure"""

        # Required fields with defaults
        validated = {
            "core_terms": [],
            "technical_terms": [],
            "role_titles": [],
            "business_types": [],
            "related_industries": [],
            "regional_variations": {}
        }

        # Copy valid data, ensuring correct types
        for field in validated.keys():
            if field in data:
                if field == "regional_variations":
                    validated[field] = data[field] if isinstance(data[field], dict) else {}
                else:
                    if isinstance(data[field], list):
                        validated[field] = data[field]
                    elif isinstance(data[field], str):
                        validated[field] = [data[field]]  # Convert single string to list
                    else:
                        logger.warning(f"Field {field} has unexpected type: {type(data[field])}")

        # Filter out generic terms from core_terms
        if validated["core_terms"]:
            filtered_terms = [
                term for term in validated["core_terms"]
                if not any(generic in term.lower() for generic in [
                    f"{industry.lower()} business",
                    f"{industry.lower()} company",
                    f"{industry.lower()} service",
                    f"{industry.lower()} firm"
                ])
            ]

            # Use filtered terms if we have enough, otherwise keep original
            if len(filtered_terms) >= 5:
                validated["core_terms"] = filtered_terms[:15]
            else:
                logger.warning(f"Industry analysis for {industry} returned mostly generic terms")
                validated["core_terms"] = validated["core_terms"][:15]

        # Ensure minimum viable data
        if not validated["core_terms"]:
            validated["core_terms"] = [f"{industry} provider", f"{industry} service", f"{industry} specialist"]

        if not validated["role_titles"]:
            validated["role_titles"] = ["CEO", "President", "Director", "Manager", "Owner"]

        return validated

    def _create_intelligent_fallback(self, industry: str, region: str) -> IndustryAnalysis:
        """Create a truly dynamic fallback using word analysis - NO HARDCODING"""
        logger.info(f"Creating intelligent fallback for industry: {industry}")

        # Extract meaningful words from the industry term
        stop_words = {'the', 'and', 'or', 'of', 'in', 'for', 'to', 'a', 'an', 'with', 'by'}
        industry_words = [word for word in industry.lower().split()
                         if word not in stop_words and len(word) > 2]

        # Generate core terms dynamically
        core_terms = []

        # Base patterns that work for any industry
        base_patterns = [
            "{} company",
            "{} firm",
            "{} service",
            "{} provider",
            "{} specialist",
            "{} consultant",
            "{} agency",
            "{} business",
            "{} organization"
        ]

        # Use the original industry phrase and individual words
        for pattern in base_patterns[:6]:  # Limit patterns to avoid too many terms
            # Use full industry term
            core_terms.append(pattern.format(industry.lower()))

            # Use key words from industry (take first 2 meaningful words)
            for word in industry_words[:2]:
                if len(word) > 3:  # Skip very short words
                    core_terms.append(pattern.format(word))

        # Add some variations without patterns
        core_terms.extend([
            industry.lower(),
            f"{industry.lower()} solutions",
            f"professional {industry.lower()}",
        ])

        # Remove duplicates while preserving order
        seen = set()
        unique_core_terms = []
        for term in core_terms:
            if term not in seen:
                seen.add(term)
                unique_core_terms.append(term)

        return IndustryAnalysis(
            core_terms=unique_core_terms[:15],
            technical_terms=self._generate_universal_tech_terms(),
            role_titles=self._generate_universal_roles(),
            business_types=self._generate_universal_business_types(),
            related_industries=self._generate_related_from_words(industry_words),
            regional_variations={}
        )

    def _generate_universal_tech_terms(self):
        """Universal technical terms that apply to most industries"""
        return [
            "software", "platform", "technology", "system", "solution",
            "automation", "digital", "online", "cloud", "data",
            "analytics", "tools", "equipment"
        ]

    def _generate_universal_roles(self):
        """Universal executive roles that exist in most industries"""
        return [
            "CEO", "President", "Director", "Manager", "Owner", "Founder",
            "Vice President", "Head", "Lead", "Principal", "Partner",
            "Executive", "Administrator", "Supervisor"
        ]

    def _generate_universal_business_types(self):
        """Universal business structures"""
        return [
            "company", "corporation", "LLC", "partnership", "firm",
            "enterprise", "organization", "business", "agency",
            "startup", "SME", "franchise"
        ]

    def _generate_related_from_words(self, industry_words):
        """Generate related industries based on the words in the original industry"""
        related = ["consulting", "technology", "finance", "marketing", "legal services"]

        # Add the industry words themselves as related areas
        for word in industry_words:
            if len(word) > 3:
                related.append(f"{word} services")
                related.append(f"{word} consulting")

        return list(set(related))[:8]  # Remove duplicates and limit

    async def generate_email_optimized_queries(self, industry_data, geo_data, request):
        """Generate optimized queries with robust error handling"""
        prompt = f"""You are a search optimization expert. Generate and rank the MOST EFFECTIVE search queries.

Available elements:
Business types: {industry_data.core_terms[:20]}
Locations: {[geo_data.primary_city] + geo_data.neighborhoods[:10] + geo_data.metro_areas[:5]}
Email providers: gmail.com, yahoo.com, outlook.com, hotmail.com, aol.com, live.com
TLD options: .com, .org, .net

Your task: Generate {request.top_k * 2} potential queries, then select the BEST {request.top_k} based on these criteria:

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

Return ONLY a JSON array: ["query1", "query2", "query3", ...]"""

        try:
            response = await asyncio.to_thread(
                lambda: self.client.messages.create(
                    model=settings.CLAUDE_MODEL,
                    max_tokens=2000,
                    temperature=0.4,
                    messages=[{"role": "user", "content": prompt}]
                )
            )

            content = response.content[0].text.strip()
            logger.info(f"Claude query generation response: {len(content)} characters")

            # Extract JSON array
            json_content = self._extract_json_array_safely(content)

            try:
                queries = json.loads(json_content)

                if isinstance(queries, list) and len(queries) > 0:
                    logger.info(f"Claude generated {len(queries)} queries successfully")
                    return queries
                else:
                    raise ValueError("Invalid response format - not a list or empty")

            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed for query generation: {e}")
                logger.error(f"Problematic content: {json_content[:200]}...")
                return self._generate_fallback_queries_array(industry_data, geo_data, request)

        except Exception as e:
            logger.error(f"Claude query generation failed: {e}, using fallback")
            return self._generate_fallback_queries_array(industry_data, geo_data, request)

    def _extract_json_array_safely(self, content: str) -> str:
        """Extract JSON array from Claude response safely"""
        # Remove markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # Find JSON array boundaries
        start = content.find("[")
        end = content.rfind("]") + 1
        if start != -1 and end != 0:
            return content[start:end]
        else:
            return content

    def _generate_fallback_queries_array(self, industry_data, geo_data, request):
        """Generate fallback queries as array (not concatenated string)"""
        logger.info("Creating fallback queries as array")

        queries = []
        email_providers = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "aol.com", "live.com"]
        tlds = [".com", ".org", ".net"]

        # Use the core terms we know exist
        terms = industry_data.core_terms[:15] if industry_data.core_terms else ["business", "company", "service"]
        locations = [geo_data.primary_city] + geo_data.neighborhoods[:10]

        # Generate diverse query patterns
        patterns = [
            'site:{tld} "{term}" "{location}" "@{email}"',
            '"{term}" "{location}" "@{email}"',
            'site:{tld} "{term}" "{location}" contact @{email}',
            '"{term} company" "{location}" "@{email}"'
        ]

        for i in range(request.top_k):
            pattern = patterns[i % len(patterns)]
            term = terms[i % len(terms)]
            location = locations[i % len(locations)]
            email = email_providers[i % len(email_providers)]
            tld = tlds[i % len(tlds)]

            query = pattern.format(term=term, location=location, email=email, tld=tld)
            queries.append(query)

        return queries