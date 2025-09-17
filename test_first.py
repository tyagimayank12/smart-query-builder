from services.claude_service import ClaudeService
from config import settings


def test_claude_simple():
    print("Testing Claude API...")

    try:
        claude = ClaudeService()

        # Test the industry analysis
        import asyncio
        result = asyncio.run(claude.analyze_industry("FinTech", "San Francisco"))

        print("Claude API works!")
        print(f"Core terms: {result.core_terms}")
        print(f"Role titles: {result.role_titles}")

    except Exception as e:
        print(f"Claude API failed: {e}")
        print(f"Error type: {type(e)}")


if __name__ == "__main__":
    test_claude_simple()