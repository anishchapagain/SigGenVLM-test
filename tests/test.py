from openai import OpenAI
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (one level above /tests/)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

def test_openai():
    # Initialize client (API key should be set in env variable)
    key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=key)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Do you know Author Anish Chapagain, a web scraping expert? Answer in brief."}]
        )

        print("✅ API is working!\n")
        print("Response:")
        print(response.choices[0].message.content)

        # Token usage
        if response.usage:
            print("\nUsage:")
            print(f"  prompt_tokens    : {response.usage.prompt_tokens}")
            print(f"  completion_tokens: {response.usage.completion_tokens}")
            print(f"  total_tokens     : {response.usage.total_tokens}")

    except Exception as e:
        print("❌ API call failed:")
        print(str(e))


if __name__ == "__main__":
    test_openai()