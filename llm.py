import os
import re
import json
import logging
import threading
from dotenv import load_dotenv

from openai import OpenAI

load_dotenv()

log = logging.getLogger(__name__)

# Using NVIDIA NIM API with Gemma or Llama3
_MODEL_PRIORITY = [
    "meta/llama-3.1-70b-instruct",
    "google/gemma-2-27b-it",
    "meta/llama-3.1-8b-instruct"
]
_client = None
_client_lock = threading.Lock()


def _get_client():
    global _client

    with _client_lock:
        if _client is not None:
            return _client

        api_key = os.getenv("NVIDIA_API_KEY")
        if not api_key or api_key == "your_nvidia_api_key_here":
            raise EnvironmentError(
                "NVIDIA_API_KEY is not set.\n"
                "1. Go to https://build.nvidia.com/\n"
                "2. Generate an API key\n"
                "3. Paste your key into .env as NVIDIA_API_KEY=..."
            )

        try:
            _client = OpenAI(
                base_url="https://integrate.api.nvidia.com/v1",
                api_key=api_key,
                timeout=15.0
            )
            log.info("NVIDIA client ready")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize OpenAI client: {e}")

    return _client


def _ask(prompt: str) -> str:
    client = _get_client()

    last_error = None
    for model in _MODEL_PRIORITY:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1024,
            )
            log.debug("Used model: %s", model)
            return response.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e)
            if (
                any(k in err_str for k in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE", "rate_limit"))
                or "quota" in err_str.lower()
                or "high demand" in err_str.lower()
            ):
                log.warning("Model %s unavailable — trying next…", model)
                last_error = e
                continue
            raise

    raise RuntimeError(
        f"All NVIDIA models exhausted their quota or failed.\n"
        f"Last error: {last_error}\n"
    )


def translate_query(raw_input: str) -> str:
    if len(raw_input) > 500:
        log.warning(
            "translate_query: input truncated from %d to 500 chars — LLM may receive "
            "an incomplete sentence. Consider increasing the limit or rejecting long inputs.",
            len(raw_input),
        )
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
    if not products:
        return {"product": None, "reason": "No products were found to compare."}

    capped_products = products[:20]
    if len(products) > 20:
        log.debug("recommend: capping %d products to 20 for LLM prompt", len(products))

    product_lines = []
    for i, p in enumerate(capped_products, 1):
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
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        clean = m.group(0) if m else raw
        result = json.loads(clean)
        idx = int(result["index"]) - 1
        if 0 <= idx < len(capped_products):
            return {
                "product": capped_products[idx],
                "reason":  result.get("reason", "No reason provided."),
            }
    except Exception as e:
        log.warning("Could not parse LLM recommendation JSON: %s | Raw: %s", e, raw)

    def _parse_rating(p):
        try:
            return float(p.get("rating", "0").split()[0])
        except (ValueError, AttributeError):
            return 0.0

    best = max(capped_products, key=_parse_rating)
    return {
        "product": best,
        "reason":  "Recommended based on highest rating (LLM parse failed).",
    }
