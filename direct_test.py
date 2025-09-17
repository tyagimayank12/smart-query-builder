import anthropic
import os

api_key = os.getenv("ANTHROPIC_API_KEY")
client = anthropic.Anthropic(api_key=api_key)

# Test with current Claude models for v0.40.0
current_models = [
    "claude-3-haiku-20240307",
    "claude-3-sonnet-20240229",
    "claude-3-opus-20240229"
]

for model in current_models:
    try:
        response = client.messages.create(
            model=model,
            max_tokens=100,
            messages=[{"role": "user", "content": "Say hello and confirm you're working!"}]
        )
        print(f"✅ {model} works!")
        print(f"Response: {response.content[0].text}")
        break
    except Exception as e:
        print(f"❌ {model} failed: {e}")