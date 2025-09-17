import anthropic
from config import settings


def check_anthropic_methods():
    print("Checking available Anthropic methods...")

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        print("Client created successfully")

        # Check available methods
        methods = [method for method in dir(client) if not method.startswith('_')]
        print(f"Available methods: {methods}")

        # Check for completions
        if hasattr(client, 'completions'):
            print("✅ Has completions")
            comp_methods = [method for method in dir(client.completions) if not method.startswith('_')]
            print(f"Completion methods: {comp_methods}")

        # Check for messages
        if hasattr(client, 'messages'):
            print("✅ Has messages")
        else:
            print("❌ No messages attribute")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_anthropic_methods()