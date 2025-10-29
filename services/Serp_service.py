"""
SERP Service for intelligent keyword and location understanding
"""
import os
import re

import httpx
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SerpService:
    """
    Intelligent SERP service that uses minimal API calls to understand:
    1. What businesses ARE the keyword (not serve it)
    2. Geographic intelligence about the location
    """

    def __init__(self):
        self.api_key = os.getenv('SERP_API_KEY')
        self.base_url = "https://serpapi.com/search.json"  # SerpAPI endpoint
        self.cache = {}
        self.cache_ttl = 86400  # 24 hours cache for keyword insights

        if not self.api_key:
            logger.warning("SERP_API_KEY not found in environment variables")

    async def get_intelligent_context(self, keyword: str, location: str) -> Dict:
        """
        Use 1-2 SERP calls to understand both keyword and location intelligently
        Returns enriched context for query generation
        """

        # Check cache first
        cache_key = f"{keyword.lower()}_{location.lower()}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                logger.info(f"Using cached context for {keyword} in {location}")
                return cached_data

        try:
            # Make ONE intelligent SERP call that gives us both business types AND location context
            context = await self._fetch_intelligent_context(keyword, location)

            # Cache the result
            self.cache[cache_key] = (context, datetime.now())

            return context

        except Exception as e:
            logger.error(f"SERP API error: {e}")
            # Return intelligent fallback without SERP
            return self._get_fallback_context(keyword, location)

    async def _fetch_intelligent_context(self, keyword: str, location: str) -> Dict:
        """
        Make ONE SERP call that tells us everything we need
        """

        # Smart query that reveals both business types AND geographic coverage
        search_query = f"{keyword} companies businesses {location}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={
                    "api_key": self.api_key,
                    "q": search_query,
                    "location": location,
                    "num": "10",  # Just 10 results is enough
                    "gl": "us"  # or detect from location
                }
            )

            if response.status_code != 200:
                raise Exception(f"SERP API returned {response.status_code}")

            data = response.json()

        # Extract intelligence from SERP results
        return self._extract_intelligence(data, keyword, location)

    def _extract_intelligence(self, serp_data: Dict, keyword: str, location: str) -> Dict:
        """
        Extract smart insights from SERP results without additional API calls
        """

        # Parse organic results
        organic_results = serp_data.get('organic_results', [])
        local_results = serp_data.get('local_results', {}).get('places', [])
        related_searches = serp_data.get('related_searches', [])

        # Extract business types that actually show up
        business_types = set()
        business_terms = set()
        location_variants = set()

        for result in organic_results[:10]:
            title = result.get('title', '').lower()
            snippet = result.get('snippet', '').lower()

            # Extract business descriptors (agency, firm, company, contractor, etc.)
            if keyword.lower() in title or keyword.lower() in snippet:
                # This is a PRIMARY business, not a service provider
                words = (title + ' ' + snippet).split()
                for word in words:
                    if word in ['agency', 'firm', 'company', 'contractor', 'studio',
                                'consultancy', 'partners', 'group', 'services', 'solutions',
                                'center', 'clinic', 'shop', 'store', 'restaurant', 'cafe']:
                        business_types.add(word)

                # Extract variations of the keyword
                # Look for related terms that appear with the keyword
                if keyword.lower() == 'real estate':
                    if 'realty' in title + snippet:
                        business_terms.add('realty')
                    if 'property' in title + snippet:
                        business_terms.add('property')
                    if 'realtor' in title + snippet:
                        business_terms.add('realtor')
                # For any keyword, find variations
                else:
                    # Extract words that appear near the keyword
                    text = title + ' ' + snippet
                    words = text.split()
                    keyword_pos = [i for i, w in enumerate(words) if keyword.lower() in w.lower()]
                    for pos in keyword_pos:
                        # Get surrounding words that might be variations
                        if pos > 0:
                            prev_word = words[pos - 1]
                            if len(prev_word) > 3 and prev_word not in ['the', 'and', 'for']:
                                business_terms.add(prev_word)

        # Extract location intelligence from local results
        for place in local_results:
            address = place.get('address', '')
            # Parse neighborhoods and areas from addresses
            if ',' in address:
                parts = address.split(',')
                if len(parts) > 1:
                    area = parts[-2].strip()  # Usually neighborhood or district
                    if area and area.lower() != location.lower():
                        location_variants.add(area)

        # Get related search terms for more variations
        keyword_variations = set()
        for related in related_searches:
            query = related.get('query', '').lower()
            if keyword.lower() in query:
                # Extract the variation
                variation = query.replace(keyword.lower(), '').strip()
                if variation and len(variation) > 2:
                    keyword_variations.add(variation)

        # Add the original keyword to variations
        business_terms.add(keyword)

        # Build intelligent context
        context = {
            "primary_business_types": list(business_types)[:5] if business_types else ["company", "business",
                                                                                       "services"],
            "keyword_variations": list(business_terms)[:5] if business_terms else [keyword],
            "location_areas": list(location_variants)[:8] if location_variants else [location],
            "search_patterns": self._identify_patterns(organic_results),
            "is_b2b": self._is_b2b_category(keyword, organic_results),
            "suggested_email_domains": self._suggest_email_domains(keyword)
        }

        logger.info(f"Extracted context for {keyword} in {location}: {json.dumps(context, indent=2)}")

        return context

    def _identify_patterns(self, results: List[Dict]) -> List[str]:
        """
        Identify successful search patterns from SERP results
        """
        patterns = []

        for result in results[:5]:
            url = result.get('link', '')
            title = result.get('title', '')

            # Identify patterns that work
            if 'directory' in url or 'yellowpages' in url:
                patterns.append('directory_listing')
            elif 'linkedin' in url:
                patterns.append('professional_profile')
            elif '.org' in url:
                patterns.append('organization')
            elif 'about' in url or 'contact' in url:
                patterns.append('company_page')

        return list(set(patterns))[:3] if patterns else ['company_page']

    def _is_b2b_category(self, keyword: str, results: List[Dict]) -> bool:
        """
        Determine if this is primarily a B2B category
        """
        b2b_indicators = ['wholesale', 'supplier', 'manufacturer', 'distributor',
                          'b2b', 'enterprise', 'solutions', 'consulting']

        text = ' '.join([r.get('snippet', '').lower() for r in results[:5]])

        return any(indicator in text for indicator in b2b_indicators)

    def _suggest_email_domains(self, keyword: str) -> List[str]:
        """
        Suggest email domains based on keyword category
        """
        # B2B categories might use more professional domains
        if any(term in keyword.lower() for term in ['consulting', 'enterprise', 'wholesale']):
            return ['@gmail.com', '@outlook.com', '@company.com', '@yahoo.com']
        else:
            return ['@gmail.com', '@yahoo.com', '@outlook.com', '@hotmail.com', '@aol.com']

    def _clean_serp_context(self, raw_context: dict) -> dict:
        """Filter out garbage from SERP results"""

        business_types = raw_context.get('primary_business_types', [])

        # Filter out garbage
        garbage_patterns = [
            r'^\d+$',  # Just numbers like "4"
            r'^company_page$',  # Metadata
            r'^@\w+\.com$',  # Email domains
            r'^[A-Z]{2,}$',  # Acronyms without context
        ]

        cleaned_types = []
        for btype in business_types:
            is_garbage = any(re.match(pattern, btype) for pattern in garbage_patterns)
            if not is_garbage and len(btype) > 3:  # Minimum length
                cleaned_types.append(btype)

        return {
            'business_types': cleaned_types[:5],  # Top 5 only
            'is_b2b': raw_context.get('is_b2b', True),
            'suggested_domains': ['@gmail.com', '@yahoo.com', '@outlook.com']
        }

    def _get_fallback_context(self, keyword: str, location: str) -> Dict:
        """
        Intelligent fallback when SERP is unavailable
        """
        return {
            "primary_business_types": ["company", "firm", "services", "agency"],
            "keyword_variations": [keyword],
            "location_areas": [location, f"Greater {location}", f"{location} Area"],
            "search_patterns": ["company_page", "directory_listing"],
            "is_b2b": False,
            "suggested_email_domains": ['@gmail.com', '@yahoo.com', '@outlook.com', '@hotmail.com']
        }