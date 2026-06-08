"""
llm.py — Gemini LLM gateway for the AI Shopping Agent.

    from llm import translate_query, recommend

Set GEMINI_API_KEY in .env  (https://aistudio.google.com/app/apikey)
"""

import os
import re
import json
import logging
import threading
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

_MODEL_PRIORITY = [
    "gemini-2.5-flash",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-flash-latest",
]
_client = None
_client_lock = threading.Lock()


def _get_client():
    global _client
    if _client is not None:         # fast path — no lock needed
        return _client

    with _client_lock:              # slow path — only one thread initialises
        if _client is not None:     # double-checked locking
            return _client

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            raise EnvironmentError(
                "GEMINI_API_KEY is not set.\n"
                "1. Go to https://aistudio.google.com/app/apikey  (free)\n"
                "2. Copy .env.example → .env\n"
                "3. Paste your key into .env"
            )

        try:
            from google import genai
            _client = genai.Client(api_key=api_key)
            log.info("Gemini client ready")
        except ImportError:
            raise ImportError("'google-genai' not found. Run: pip install google-genai")

    return _client


def _ask(prompt: str) -> str:
    """Send prompt to Gemini, falling back across models on quota exhaustion."""
    from google import genai
    client = _get_client()

    last_error = None
    for model in _MODEL_PRIORITY:
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            log.debug("Used model: %s", model)
            return response.text.strip()
        except Exception as e:
            err_str = str(e)
            if (
                any(k in err_str for k in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE"))
                or "quota" in err_str.lower()
                or "high demand" in err_str.lower()
            ):
                log.warning("Model %s unavailable — trying next…", model)
                last_error = e
                continue
            raise

    raise RuntimeError(
        f"All Gemini models exhausted their quota.\n"
        f"Last error: {last_error}\n"
        f"Free tier resets daily — try again tomorrow, or add billing at "
        f"https://console.cloud.google.com"
    )


def translate_query(raw_input: str) -> str:
    """
    Translate a natural-language product request (any language) into a
    concise English Amazon/Flipkart search query (3–8 words).
    """
    safe_input = raw_input[:500].replace('"', "'").replace("\n", " ").strip()

    prompt = f"""
You are a product search assistant. The user has described a product they want
to buy. Their input may be in any language (Hindi, Punjabi, English, or a mix).

Your task:
1. Understand what product and features the user wants.
2. Output ONLY a clean, concise English search query suitable for Amazon/Flipkart.
3. Keep it 3-8 words. No explanation, no punctuation, just the search query.

User input: "{safe_input}"

English search query:"""

    query = _ask(prompt)
    query = query.strip().strip('"').strip("'").strip()
    log.info("Translated query: '%s' → '%s'", raw_input[:50], query)
    return query


def recommend(original_query: str, products: list[dict]) -> dict:
    """
    Pick the best product from a combined list and explain why.

    Returns dict with keys: product (dict), reason (str).
    Falls back to highest-rated product if LLM JSON parse fails.
    """
    if not products:
        return {"product": None, "reason": "No products were found to compare."}

    product_lines = []
    for i, p in enumerate(products, 1):
        product_lines.append(
            f"{i}. [{p.get('source', '?').upper()}] {p.get('title', 'N/A')}\n"
            f"   Price: {p.get('price', 'N/A')} | "
            f"Rating: {p.get('rating', 'N/A')} | "
            f"Reviews: {p.get('reviews_count', 'N/A')}"
        )
    product_list = "\n".join(product_lines)

    prompt = f"""
You are an expert AI shopping assistant. A user searched for: "{original_query}"

Here are the top products found across Amazon, Flipkart, and the Web:

{product_list}

Your task:
1. STRICTLY filter the products to match the user's explicit requirements (e.g., if they asked for an i7 12th gen, ignore all i5 or 13th/14th gen laptops).
2. From the filtered list, identify the single BEST product that gives the best value (balance of price, rating, and reviews).
3. If NO product in the list meets the strict requirements, pick the closest alternative and explicitly mention in your reason that the exact match wasn't found but this is the closest option.
4. Return your answer as a valid JSON object with exactly these keys:
   - "index": the 1-based number of the best product
   - "reason": a 1-3 sentence plain English explanation of why it is the best choice.

Reply with ONLY the JSON object, no markdown, no extra text.
"""

    raw = _ask(prompt)

    try:
        # Strip markdown code fences the model sometimes wraps around the JSON
        clean = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        clean = re.sub(r"\s*```$", "", clean).strip()
        result = json.loads(clean)
        idx = int(result["index"]) - 1
        if 0 <= idx < len(products):
            return {
                "product": products[idx],
                "reason":  result.get("reason", "No reason provided."),
            }
    except Exception as e:
        log.warning("Could not parse LLM recommendation JSON: %s | Raw: %s", e, raw)

    def _parse_rating(p):
        try:
            return float(p.get("rating", "0").split()[0])
        except (ValueError, AttributeError):
            return 0.0

    best = max(products, key=_parse_rating)
    return {
        "product": best,
        "reason":  "Recommended based on highest rating (LLM parse failed).",
    }
