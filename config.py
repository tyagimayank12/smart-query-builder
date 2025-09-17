"""
Configuration settings for Smart Query Builder
"""
import os

class Settings:
    # API Keys
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Query Builder Settings
    DEFAULT_TOP_K: int = 25
    MAX_TOP_K: int = 100

    # Email Providers
    EMAIL_PROVIDERS = [
        "gmail.com", "yahoo.com", "outlook.com",
        "hotmail.com", "aol.com", "live.com"
    ]

    SEARCH_ENGINES = {
        "bing": "https://www.bing.com/search?q=",
        "duckduckgo": "https://duckduckgo.com/?q=",
        "google": "https://www.google.com/search?q="
    }

    # Business TLDs
    BUSINESS_TLDS = [".com", ".org", ".net", ".co"]

    # Claude Settings
    CLAUDE_MODEL: str = "claude-3-haiku-20240307"
    CLAUDE_MAX_TOKENS: int = 2000

    # Geographic Settings
    GEOLOCATOR_USER_AGENT: str = "smart_query_builder_v1"

# Create settings instance
settings = Settings()

def validate_config():
    """Check if configuration is valid"""
    if settings.ANTHROPIC_API_KEY == "your-api-key-here":
        print("⚠️  WARNING: Please set your ANTHROPIC_API_KEY")
        return False
    return True