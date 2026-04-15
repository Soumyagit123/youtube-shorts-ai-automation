import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(".env")

def test_gemini_full():
    api_key = os.getenv("GEMINI_API_KEY") 
    if not api_key:
        try:
            import json
            with open("config.json") as f:
                config = json.load(f)
                api_key = config.get("api_keys", {}).get("gemini", "")
        except Exception:
            pass

    if not api_key:
        print("No API key found in backend env or config.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    
    prompt = """You are a viral YouTube Shorts scriptwriter for AI and Technology content.

IMPORTANT LANGUAGE RULES:
- "voiceover_text" MUST be written in Hindi. 
- "english_subtitle_text" MUST be in plain English, no emojis, no special characters.
- "image_prompts" MUST always be in English (for Stable Diffusion quality).
- "title" MUST be in Hindi.

Return a JSON with format: {"voiceover_text": "...", "image_prompts": ["..."], "metadata": {"title": "..."}}
Topic: Tech News"""

    try:
        print("Sending full request like scripter.py...")
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.9,
            ),
        )
        print("SUCCESS! Output:")
        print(response.text)
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_gemini_full()
