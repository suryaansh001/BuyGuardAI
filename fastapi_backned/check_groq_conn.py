import os
from groq import Groq
import dotenv
dotenv.load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Minimal tool just to test function calling
tools = [
    {
        "type": "function",
        "function": {
            "name": "test_tool",
            "description": "A test function for checking tool calling support.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string"
                    }
                },
                "required": ["message"]
            }
        }
    }
]

print("\n=== Checking Groq models for tool-calling support ===\n")

models = client.models.list()

for model in models.data:
    model_id = model.id

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "user",
                    "content": "Call test_tool with message 'hello'."
                }
            ],
            tools=tools,
            tool_choice="required",
            max_tokens=100,
        )

        message = response.choices[0].message

        if message.tool_calls:
            print(f"✅ {model_id} - Tool calling: YES")
        else:
            print(f"⚠️  {model_id} - Tool calling: NO (no tool call returned)")

    except Exception as e:
        error = str(e)
        if "tool" in error.lower() or "function" in error.lower():
            print(f"❌ {model_id} - Tool calling: NO ({error[:180]})")
        else:
            print(f"⚠️  {model_id} - Other error: {error[:180]}")

print("\n=== Checking Groq models for JSON mode support ===\n")

for model in models.data:
    model_id = model.id

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {
                    "role": "system",
                    "content": "Return JSON with keys: name, age"
                },
                {
                    "role": "user",
                    "content": "John, 30"
                }
            ],
            temperature=0,
            response_format={"type": "json_object"},
            max_tokens=100,
        )

        content = response.choices[0].message.content
        import json
        json.loads(content)  # Validate JSON
        print(f"✅ {model_id} - JSON mode: YES")

    except Exception as e:
        error = str(e)
        if "json" in error.lower() or "format" in error.lower():
            print(f"❌ {model_id} - JSON mode: NO ({error[:180]})")
        else:
            print(f"⚠️  {model_id} - Other error: {error[:180]}")

print("\nDone.")