"""
Claude Service - Intelligent Query Generation
Completely rewritten to handle any industry input with semantic understanding
"""

import anthropic
import json
import logging
import re
import asyncio
from typing import List, Dict, Any, Optional
import os


class ClaudeService:
    """Service for generating intelligent search queries using Claude AI"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.logger = logging.getLogger(__name__)

    async def generate_queries(
        self,
        industry: str,
        region: str,
        top_k: int = 10,
        serp_context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generate intelligent search queries with full semantic understanding.

        Args:
            industry: Any business type/industry (can be short or long phrase)
            region: Geographic location
            top_k: Number of queries to generate
            serp_context: Optional context from SERP (used as hints, not rules)

        Returns:
            List of diverse, intelligent search queries
        """
        try:
            self.logger.info(f"Generating {top_k} queries for '{industry}' in '{region}'")

            # Build the intelligent prompt
            prompt = self._build_intelligent_prompt(industry, region, top_k, serp_context)

            # Call Claude
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                temperature=0.7,  # Higher temperature for more creative variations
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Extract and parse response
            response_text = message.content[0].text.strip()
            queries = self._parse_claude_response(response_text, top_k)

            # Validate queries
            validated_queries = self._validate_queries(queries, top_k)

            self.logger.info(f"Successfully generated {len(validated_queries)} queries")
            return validated_queries

        except Exception as e:
            self.logger.error(f"Error generating queries: {str(e)}")
            # Fallback to basic queries if Claude fails
            return self._generate_fallback_queries(industry, region, top_k)

    def _build_intelligent_prompt(
        self,
        industry: str,
        region: str,
        top_k: int,
        serp_context: Optional[Dict[str, Any]]
    ) -> str:
        """Build an intelligent prompt that handles any input type"""

        # Clean SERP context if provided
        context_hint = ""
        if serp_context:
            cleaned_context = self._clean_serp_context(serp_context)
            if cleaned_context.get('business_types'):
                context_hint = f"\n\nHINT from market research (use intelligently, ignore if irrelevant):\n- Related business types found: {', '.join(cleaned_context['business_types'][:5])}"

        prompt = f"""You are an expert at generating Google X-ray search queries for lead generation. Your goal is to find business contacts across various platforms.

INPUT:
- Industry/Business Type: "{industry}"
- Geographic Region: "{region}"
- Number of queries needed: {top_k}

YOUR TASK:
Generate {top_k} highly diverse and intelligent Google search queries to find contacts in this industry.

CRITICAL RULES FOR UNDERSTANDING THE INDUSTRY:

1. **Semantic Intelligence** (MOST IMPORTANT):
   - Understand what "{industry}" actually means
   - If it's a long phrase like "real estate brokerage firms", understand the core business (real estate companies)
   - If it's "Insurance broker agents and agencies", understand it means BOTH professionals AND companies
   - If it's generic like "Insurance", expand to specific types (health insurance, auto insurance, life insurance)
   - DO NOT just append words like "specialist", "consultant", "provider" to the input
   - CREATE variations based on understanding, not templates

2. **Generate Semantic Variations**:
   - Synonyms: Different ways to describe the same business
   - Related roles: Job titles in this industry  
   - Company types: Different business structures in this industry
   - Specializations: Specific niches within the industry
   - Service variations: Different services offered

3. **Query Patterns - B2C Business Website Searches ONLY**:
   
   You are searching for ACTUAL BUSINESS WEBSITES (B2C), NOT individual professionals or LinkedIn profiles.
   
   Pattern A - .com Domain Search with Email (50% of queries):
   site:.com "Business Type" "Location" "@email.com"
   Examples:
   - site:.com "Insurance Agency" "Manhattan" "@gmail.com"
   - site:.com "Real Estate Brokerage" "Brooklyn" "@yahoo.com"
   - site:.com "Coffee Shop" "Portland" "@outlook.com"
   
   Pattern B - Multiple TLD Search with Contact (30% of queries):
   site:.org OR site:.net "Business Type" "Location" contact OR email
   Examples:
   - site:.org "Insurance Broker" "New York" contact
   - site:.net "Real Estate Agency" "Queens" email
   - site:.com "Property Management" "Manhattan" contact
   
   Pattern C - Open Web Business Search (20% of queries):
   "Business Type" "Location" "@email.com" -linkedin -indeed -jobs -careers
   Examples:
   - "Insurance Agency" "New York" "@gmail.com" -linkedin -jobs
   - "Real Estate Brokerage" "Chicago" "@yahoo.com" -indeed -careers
   - "Coffee Roastery" "Portland" "@outlook.com" -linkedin

4. **Geographic Intelligence**:
   - If "{region}" is a CITY (like "New York", "Chicago", "Los Angeles"):
     * Include main city name
     * Include major neighborhoods/boroughs
     * Include metro area variations
   - If "{region}" is a STATE (like "California", "Texas"):
     * Include major cities in that state
     * Include state name and abbreviation
   - If "{region}" is SMALL/UNKNOWN:
     * Use the exact region name provided
     * Don't make up locations

5. **Email Domain Rotation** (for queries that need email):
   - Rotate through: @gmail.com, @yahoo.com, @outlook.com, @hotmail.com
   - Occasionally use: @aol.com, @live.com, @icloud.com, @protonmail.com
   - Don't repeat same email domain consecutively

6. **Business Types to Focus On** (B2C ONLY):
   - Local businesses: Coffee shops, restaurants, retail stores
   - Service companies: Insurance agencies, real estate brokerages, law firms
   - Professional firms: Accounting firms, consulting companies, marketing agencies
   - Healthcare providers: Medical clinics, dental offices, urgent care centers
   - Home services: Plumbing companies, HVAC contractors, cleaning services
   
   Focus on finding their WEBSITES (.com, .org, .net domains), NOT their LinkedIn profiles or employees.

7. **CRITICAL - B2C ONLY (Avoid B2B Platforms)**:
   ❌ NEVER use: site:linkedin.com
   ❌ NEVER use: site:zoominfo.com
   ❌ NEVER use: site:apollo.io
   ❌ NEVER use: site:rocketreach.com
   ❌ NEVER use: site:crunchbase.com
   
   ✅ ONLY use: site:.com, site:.org, site:.net, OR open web searches
   ✅ ALWAYS exclude: -linkedin -indeed -jobs -careers -hiring
   
   We're finding BUSINESS WEBSITES, not individual people or business directories.

8. **Other Mistakes to AVOID**:
   ❌ Don't append generic words: "Insurance Brokers specialist" 
   ❌ Don't use unsupported operators: intitle:, inurl:, -site:
   ❌ Don't repeat similar queries (change location AND title AND email)
   ❌ Don't search for just email domains without context
   ❌ Don't use broken syntax like site:.com without meaningful terms

9. **Proper Query Syntax**:
   ✅ All phrases must be in quotes: "Insurance Broker" not Insurance Broker
   ✅ Email patterns in quotes: "@gmail.com" not @gmail.com
   ✅ Site operator format: site:linkedin.com OR site:.com
   ✅ Exclusions: -jobs -careers -hiring (when needed)
   ✅ Multiple terms: Use OR for alternatives: contact OR email

EXAMPLES TO LEARN FROM:

Example 1 - Input: "Insurance Brokers", Region: "New York"
B2C Focus: Find insurance agency/brokerage WEBSITES, not individual professionals
Good queries:
✅ site:.com "Insurance Agency" "Manhattan" "@gmail.com"
✅ site:.com "Insurance Brokerage" "Brooklyn" "@yahoo.com"
✅ site:.org "Independent Insurance Agent" "Queens" contact
✅ "Insurance Services" "New York" "@outlook.com" -linkedin -jobs
✅ site:.net "Insurance Broker" "Bronx" email
✅ site:.com "Commercial Insurance Agency" "Staten Island" "@hotmail.com"
✅ "Property & Casualty Insurance" "NYC" "@gmail.com" -indeed -careers
✅ site:.org "Insurance Company" "Manhattan" contact
✅ site:.com "Employee Benefits Insurance" "Greater New York" "@yahoo.com"
✅ "Risk Management Insurance" "New York" "@outlook.com" -linkedin

Bad queries (DON'T DO THIS):
❌ site:linkedin.com "Insurance Broker" "New York" "@gmail.com"
❌ site:zoominfo.com "Insurance Agency" "Manhattan"
❌ site:apollo.io "Insurance Broker" "NYC"
❌ intitle:"Insurance" "New York"
❌ "4" "Brooklyn" "@gmail.com"
❌ site:.com "company_page" "Insurance"

Example 2 - Input: "real estate brokerage firms", Region: "Chicago"
B2C Focus: Find real estate company WEBSITES
Good understanding: This means real estate company websites, not LinkedIn profiles
✅ site:.com "Real Estate Agency" "Chicago" "@gmail.com"
✅ site:.org "Real Estate Brokerage" "Loop" contact
✅ "Commercial Real Estate Firm" "Chicago" "@yahoo.com" -linkedin -jobs
✅ site:.net "Property Management Company" "Lincoln Park" email
✅ site:.com "Residential Real Estate" "Wicker Park" "@outlook.com"
✅ "Real Estate Services" "Chicago" "@gmail.com" -indeed -careers
✅ site:.org "Realty Company" "Downtown Chicago" contact
✅ site:.com "Real Estate Firm" "Chicagoland" "@hotmail.com"
✅ "Property Sales Company" "Illinois" "@yahoo.com" -linkedin
✅ site:.net "Real Estate Investment Firm" "Chicago" email

Example 3 - Input: "Coffee Shops", Region: "Portland"
B2C Focus: Find actual coffee shop business websites
✅ site:.com "Coffee Shop" "Portland" "@gmail.com"
✅ site:.com "Coffee House" "Downtown Portland" contact
✅ "Specialty Coffee Roaster" "Portland" "@yahoo.com" -linkedin -jobs
✅ site:.org "Cafe" "Pearl District" email
✅ "Independent Coffee Shop" "Portland OR" "@outlook.com" -indeed
✅ site:.net "Artisan Coffee" "Portland" contact
✅ site:.com "Coffee Roastery" "Alberta Arts" "@gmail.com"
✅ "Local Coffee Business" "Portland Metro" "@hotmail.com" -careers -linkedin
✅ site:.com "Espresso Bar" "Portland" email
✅ "Coffee Shop" "Oregon" "@yahoo.com" -jobs -indeed
{context_hint}

OUTPUT FORMAT:
Return ONLY a JSON array of {top_k} query strings. No explanations, no markdown, no code blocks.
Just the raw JSON array.

Format: ["query1", "query2", ...]

Generate {top_k} diverse, intelligent queries now:"""

        return prompt

    def _clean_serp_context(self, serp_context: Dict[str, Any]) -> Dict[str, Any]:
        """Clean garbage from SERP context"""

        business_types = serp_context.get('primary_business_types', [])

        # Filter out garbage patterns
        garbage_patterns = [
            r'^\d+$',  # Just numbers like "4"
            r'^company_page$',  # Metadata
            r'^@[\w\.-]+$',  # Email domains
            r'^[A-Z]{2,}$',  # Random acronyms
            r'^(www|http|https)',  # URLs
            r'^\W+$',  # Only special characters
        ]

        cleaned_types = []
        for btype in business_types:
            if not btype or len(btype) < 3:
                continue

            is_garbage = any(re.match(pattern, str(btype), re.IGNORECASE)
                           for pattern in garbage_patterns)

            if not is_garbage:
                cleaned_types.append(btype)

        return {
            'business_types': cleaned_types[:10],  # Top 10 relevant types
            'is_b2b': serp_context.get('is_b2b', True)
        }

    def _parse_claude_response(self, response_text: str, expected_count: int) -> List[str]:
        """Parse Claude's response and extract queries"""

        try:
            # Remove markdown code blocks if present
            response_text = re.sub(r'```json\s*|\s*```', '', response_text)
            response_text = response_text.strip()

            # Try to find JSON array
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)

            # Parse JSON
            queries = json.loads(response_text)

            if isinstance(queries, list):
                # Clean each query
                cleaned_queries = []
                for q in queries:
                    if isinstance(q, str) and len(q.strip()) > 10:
                        cleaned_queries.append(q.strip())

                return cleaned_queries[:expected_count]

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")
            self.logger.debug(f"Response text: {response_text[:500]}")
        except Exception as e:
            self.logger.error(f"Unexpected error parsing response: {e}")

        return []

    def _validate_queries(self, queries: List[str], expected_count: int) -> List[str]:
        """Validate and clean queries"""

        valid_queries = []
        seen = set()

        for query in queries:
            # Skip duplicates
            normalized = query.lower().strip()
            if normalized in seen:
                continue

            # Basic validation
            if len(query) < 15:  # Too short
                continue

            # Check for proper quote usage
            if '"' not in query:  # No quotes at all
                continue

            # Check for garbage patterns
            if any(garbage in query for garbage in ['undefined', 'null', 'example', 'placeholder']):
                continue

            seen.add(normalized)
            valid_queries.append(query)

            if len(valid_queries) >= expected_count:
                break

        return valid_queries

    def _generate_fallback_queries(
        self,
        industry: str,
        region: str,
        top_k: int
    ) -> List[str]:
        """Generate basic B2C fallback queries if Claude fails"""

        self.logger.warning("Using fallback query generation")

        # Clean industry input
        industry_clean = industry.strip()

        # Try to extract meaningful variations
        # If input is "Insurance Brokers", variations could be "Insurance Agency", "Insurance Services"
        variations = [
            industry_clean,
            industry_clean.replace("Brokers", "Agency").replace("brokers", "agency"),
            industry_clean.replace("Brokers", "Services").replace("brokers", "services"),
            industry_clean.replace("Brokers", "Company").replace("brokers", "company"),
            industry_clean.replace("Brokers", "Firm").replace("brokers", "firm"),
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for v in variations:
            if v not in seen:
                seen.add(v)
                unique_variations.append(v)

        # Geographic variations
        locations = [region]
        if "New York" in region:
            locations.extend(["Manhattan", "Brooklyn", "Queens", "NYC"])
        elif "Los Angeles" in region or "LA" in region:
            locations.extend(["Downtown LA", "West LA", "Santa Monica"])
        elif "Chicago" in region:
            locations.extend(["Downtown Chicago", "Loop", "North Side"])
        elif "San Francisco" in region:
            locations.extend(["Downtown SF", "Mission District", "SOMA"])

        # Email domains to rotate
        email_domains = ["@gmail.com", "@yahoo.com", "@outlook.com", "@hotmail.com", "@aol.com"]

        # Domain patterns
        domains = [".com", ".org", ".net"]

        # Generate diverse B2C queries
        queries = []
        patterns = [
            'site:{domain} "{industry}" "{location}" "{email}"',
            'site:{domain} "{industry}" "{location}" contact',
            '"{industry}" "{location}" "{email}" -linkedin -jobs',
            'site:{domain} "{industry}" "{location}" email',
            '"{industry}" "{location}" "{email}" -indeed -careers',
        ]

        for i in range(top_k):
            pattern = patterns[i % len(patterns)]
            industry_var = unique_variations[i % len(unique_variations)]
            location = locations[i % len(locations)]
            email = email_domains[i % len(email_domains)]
            domain = domains[i % len(domains)]

            query = pattern.format(
                industry=industry_var,
                location=location,
                email=email,
                domain=domain
            )
            queries.append(query)

        return queries[:top_k]

    def generate_intelligent_queries(
        self,
        industry: str = None,
        region: str = None,
        top_k: int = 10,
        serp_context: Optional[Dict[str, Any]] = None,
        **kwargs  # Catch any extra arguments
    ) -> List[str]:
        """
        Synchronous wrapper for generate_queries.
        Bulletproof version that handles any calling pattern.

        Usage (all these work):
            service.generate_intelligent_queries("Insurance", "New York", 10)
            service.generate_intelligent_queries(industry="Insurance", region="New York", top_k=10)
            service.generate_intelligent_queries("Insurance", region="New York")
        """
        # Handle missing required parameters
        if industry is None:
            industry = kwargs.get('industry', 'General Business')
            self.logger.warning(f"Industry not provided, using default: {industry}")

        if region is None:
            region = kwargs.get('region', 'United States')
            self.logger.warning(f"Region not provided, using default: {region}")

        # Ensure strings
        industry = str(industry)
        region = str(region)
        top_k = int(top_k) if top_k else 10

        self.logger.info(f"Generating queries: industry='{industry}', region='{region}', top_k={top_k}")

        try:
            # Try to use existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new loop in a thread if current loop is running
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.generate_queries(industry, region, top_k, serp_context)
                    )
                    return future.result()
            else:
                # Use existing loop
                return loop.run_until_complete(
                    self.generate_queries(industry, region, top_k, serp_context)
                )
        except RuntimeError:
            # No event loop exists, create one
            return asyncio.run(
                self.generate_queries(industry, region, top_k, serp_context)
            )
        except Exception as e:
            self.logger.error(f"Error in generate_intelligent_queries: {e}", exc_info=True)
            # Fall back to sync generation
            return self._generate_fallback_queries(industry, region, top_k)