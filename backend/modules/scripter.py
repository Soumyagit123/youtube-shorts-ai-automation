"""
modules/scripter.py — Gemini AI Script Generator (SaaS Optimized)
=================================================
Sends a structured prompt to Gemini and parses its JSON response into:
  {
    "voiceover_text": str,
    "image_prompts": [str x5-6],
    "metadata": {
      "title": str,
      "description": str,
      "tags": [str]
    }
  }
"""

import json
import re
import time
import asyncio
import os

from google import genai
from google.genai import types
from google.genai import errors

from config import get_logger, GEMINI_MODEL, VOICEOVER_LANG
from core.config_manager import config
from core.utils import get_user_conf

log = get_logger("scripter")

# ── Prompt Template ───────────────────────────────────────────────────────────
def _build_prompt(topic: str, lang: str, image_count: int = 6) -> str:
    """
    Build the full Gemini prompt for the given topic and voiceover language.
    """
    lang_display = lang.capitalize()
    hindi_note = "Use Devanagari script." if lang.lower() == "hindi" else ""
    
    # Build dynamic JSON scene templates based on exactly how many images we want
    scenes = ['"<English Stable Diffusion prompt, scene 1 — cinematic, photorealistic, 8K>"']
    for i in range(2, image_count + 1):
        scenes.append(f'"<scene {i}>"')
    scenes_json = ",\n    ".join(scenes)
    
    return f"""You are a viral YouTube Shorts scriptwriter for AI and Technology content.

IMPORTANT LANGUAGE RULES:
- "voiceover_text" MUST be written in {lang_display}. {hindi_note}
- "english_subtitle_text" MUST be in plain English, no emojis, no special characters.
- "image_prompts" MUST always be in English (for Stable Diffusion quality).
- "title" MUST be in {lang_display}.
- "description" and "tags" MUST be in English (for YouTube SEO).

Output ONLY a valid JSON object. No markdown fences, no extra text.

JSON schema:
{{
  "voiceover_text": "<45-60 second energetic {lang_display} narration — punchy sentences, hook opening, strong CTA>",
  "english_subtitle_text": "<exact English translation of voiceover_text — plain text only, no emojis, no symbols>",
  "image_prompts": [
    {scenes_json}
  ],
  "metadata": {{
    "title": "<viral {lang_display} YouTube Short title, max 70 chars>",
    "description": "<compelling English description with SEO keywords, ~200 words>",
    "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7","tag8","tag9","tag10"]
  }}
}}

Rules for voiceover_text:
- First sentence: shocking hook question/statement
- Short punchy sentences throughout
- Build to a mind-blowing fact or tip
- End: "Follow karo aur notification on karo" (if Hindi) or equivalent CTA
- Target: 112-150 words

Topic: "{topic}"

Generate the EXACT structure now:"""

def _extract_json(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().replace("```", "")
    start = cleaned.find("{")
    if start == -1:
        raise ValueError("No JSON object found in Gemini response.")
    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(cleaned, start)
    return obj

async def generate_script(topic: str, lang: str | None = None, user_config: dict | None = None) -> dict:
    language = (lang or VOICEOVER_LANG).lower()
    image_count = int(get_user_conf("image.image_count", user_config, 6))
    
    log.info(f"Generating script: topic={topic!r}  lang={language!r}  images={image_count}")
    
    api_key = get_user_conf("api_keys.gemini", user_config, "").strip() or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("No Gemini API key was provided. Please add it in Settings.")
        
    client = genai.Client(api_key=api_key)
    prompt = _build_prompt(topic, language, image_count)
    
    # Use dynamic model from config
    model_name = get_user_conf("pipeline.gemini_model", user_config, GEMINI_MODEL)

    for attempt in range(1, 11):
        log.debug(f"Gemini API call ({model_name}, attempt {attempt}) …")
        try:
            # Wrap the blocking generate_content call in a thread
            def _gen():
                return client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.9,
                    ),
                )
            
            response = await asyncio.to_thread(_gen)
            raw_text = response.text
            log.debug(f"Raw Gemini response (length: {len(raw_text)})")
            script = _extract_json(raw_text)

            # Validate
            required = {"voiceover_text", "image_prompts", "metadata"}
            if not required.issubset(script.keys()):
                raise KeyError(f"Missing keys: {required - script.keys()}")

            if "english_subtitle_text" not in script:
                script["english_subtitle_text"] = script["voiceover_text"]

            log.info(f"Script generated: {script['metadata']['title']}")
            return script

        except errors.ClientError as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                backoff = 2 ** attempt
                log.warning(f"Quota Exhausted (429). Retrying in {backoff}s... (Attempt {attempt}/10)")
                await asyncio.sleep(backoff)
                continue
            raise e
        except Exception as e:
            log.warning(f"Attempt {attempt} failed: {e}")
            if attempt >= 10: raise e
            await asyncio.sleep(2)

    raise RuntimeError("Script generation failed after 10 attempts.")

if __name__ == "__main__":
    t = "Future of AI Chips"
    try:
        res = generate_script(t)
        print("\n✅ SUCCESS!")
        print(f"Title: {res['metadata']['title']}")
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
