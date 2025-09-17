"""
Simplified geographic service with reliable fallbacks
"""
import logging
from models import GeographicData

logger = logging.getLogger(__name__)

class GeographicService:
    """Simplified geographic service that always returns valid data"""

    def __init__(self):
        # Basic city data for common locations
        self.city_data = {
            'san francisco': {
                'neighborhoods': ['SOMA', 'Mission', 'Financial District', 'Castro', 'Mission Bay', 'Potrero Hill'],
                'metro_areas': ['Bay Area', 'Silicon Valley', 'Peninsula', 'East Bay'],
                'local_names': ['SF', 'San Fran', 'The City', 'San Francisco'],
                'country_code': 'US',
                'languages': ['en'],
                'business_tlds': ['.com', '.org', '.net']
            },
            'new york': {
                'neighborhoods': ['Manhattan', 'Brooklyn', 'Queens', 'Bronx', 'Staten Island'],
                'metro_areas': ['NYC Metro', 'Tri-State Area', 'Greater New York'],
                'local_names': ['NYC', 'New York City', 'The Big Apple', 'New York'],
                'country_code': 'US',
                'languages': ['en'],
                'business_tlds': ['.com', '.org', '.net']
            },
            'london': {
                'neighborhoods': ['City of London', 'Westminster', 'Camden', 'Shoreditch', 'Canary Wharf'],
                'metro_areas': ['Greater London', 'Home Counties', 'Thames Valley'],
                'local_names': ['London', 'The City'],
                'country_code': 'GB',
                'languages': ['en'],
                'business_tlds': ['.co.uk', '.org.uk', '.com']
            },
            'berlin': {
                'neighborhoods': ['Mitte', 'Kreuzberg', 'Prenzlauer Berg', 'Charlottenburg'],
                'metro_areas': ['Greater Berlin', 'Berlin-Brandenburg'],
                'local_names': ['Berlin'],
                'country_code': 'DE',
                'languages': ['de', 'en'],
                'business_tlds': ['.de', '.com', '.org']
            },
            'mumbai': {
                'neighborhoods': ['Bandra', 'Andheri', 'Lower Parel', 'Powai', 'Worli'],
                'metro_areas': ['Mumbai Metropolitan Region', 'Greater Mumbai'],
                'local_names': ['Mumbai', 'Bombay'],
                'country_code': 'IN',
                'languages': ['en', 'hi'],
                'business_tlds': ['.in', '.co.in', '.com']
            }
        }

    async def resolve_geography(self, region: str) -> GeographicData:
        """
        Always returns valid geographic data
        """
        try:
            region_lower = region.lower().strip()

            # Check if we have specific data for this city
            if region_lower in self.city_data:
                data = self.city_data[region_lower]
                return GeographicData(
                    primary_city=region,
                    neighborhoods=data['neighborhoods'],
                    metro_areas=data['metro_areas'],
                    local_names=data['local_names'],
                    country_code=data['country_code'],
                    languages=data['languages'],
                    business_tlds=data['business_tlds']
                )

            # Generic fallback for any other city
            return GeographicData(
                primary_city=region,
                neighborhoods=[],
                metro_areas=[region, f"Greater {region}"],
                local_names=[region],
                country_code="US",
                languages=["en"],
                business_tlds=[".com", ".org", ".net"]
            )

        except Exception as e:
            logger.error(f"Geographic service error: {e}")
            # Absolute fallback - this should never fail
            return GeographicData(
                primary_city=region if region else "Unknown",
                neighborhoods=[],
                metro_areas=[region if region else "Unknown"],
                local_names=[region if region else "Unknown"],
                country_code="US",
                languages=["en"],
                business_tlds=[".com"]
            )