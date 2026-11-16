"""
flipkart_scraper.py — Flipkart search results via the page's embedded state.

Flipkart server-renders `window.__INITIAL_STATE__ = {...};` into the search
page. We fetch it with a browser-impersonating HTTP client (curl_cffi, the
same client the Amazon scraper uses) and walk the JSON for product objects.
"""

import json
import logging
import random
import sys
import time
from urllib.parse import quote_plus

from curl_cffi import requests

from config import settings

log = logging.getLogger(__name__)

PAGES = settings.scrape_pages     # SCRAPE_PAGES, default 2
MAX_RESULTS = 20 * PAGES          # one search page holds about 24–40 products
FLIPKART_BASE = "https://www.flipkart.com"
_STATE_MARKER = "window.__INITIAL_STATE__"
_IMPERSONATE = ("chrome", "safari", "edge")


def _find_products(obj, results=None):
    if results is None:
        results = []
    if isinstance(obj, dict):
        info = obj.get("productInfo")
        if isinstance(info, dict) and isinstance(info.get("value"), dict):
            results.append(info["value"])
        for v in obj.values():
            _find_products(v, results)
    elif isinstance(obj, list):
        for item in obj:
            _find_products(item, results)
    return results


def _extract_state(html: str) -> dict | None:
    """Decode the JSON object assigned to window.__INITIAL_STATE__."""
    start = html.find(_STATE_MARKER)
    if start == -1:
        return None
    brace = html.find("{", start)
    if brace == -1:
        return None
    try:
        state, _ = json.JSONDecoder().raw_decode(html, brace)
        return state if isinstance(state, dict) else None
    except json.JSONDecodeError as e:
        log.error("Failed to parse Flipkart JSON state: %s", e)
        return None


def _fetch(url: str, attempts: int = 3) -> str:
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(
                url,
                impersonate=random.choice(_IMPERSONATE),
                headers={"Accept-Language": "en-IN,en;q=0.9"},
                timeout=12,
            )
            if response.status_code == 200 and _STATE_MARKER in response.text:
                return response.text
            log.warning("Flipkart returned %s (attempt %d/%d)", response.status_code, attempt, attempts)
        except Exception as e:
            log.warning("Flipkart request failed (attempt %d/%d): %s", attempt, attempts, e)
        if attempt < attempts:
            time.sleep(random.uniform(0.8, 1.6))
    return ""


def _price(pricing: dict):
    price = (pricing.get("finalPrice") or {}).get("value")
    if price is None:
        for entry in pricing.get("prices") or []:
            if not entry.get("strikeOff"):
                return entry.get("value")
    return price


def scrape_flipkart(query: str, max_results: int = MAX_RESULTS, pages: int = PAGES) -> list[dict]:
    """Flipkart search results from up to `pages` pages (page 2+ only if more are needed)."""
    log.info("Scraping Flipkart for: '%s' (up to %d pages)", query, pages)
    results: list[dict] = []
    seen_urls: set[str] = set()

    for page in range(1, pages + 1):
        if len(results) >= max_results:
            break
        if page > 1:
            time.sleep(random.uniform(0.8, 1.6))
        url = f"{FLIPKART_BASE}/search?q={quote_plus(query)}&otracker=search"
        if page > 1:
            url += f"&page={page}"
        # Page 1 is retried; a failed later page just ends the search with what we have.
        html = _fetch(url, attempts=3 if page == 1 else 1)
        state = _extract_state(html) if html else None
        if state is None:
            if page == 1:
                log.error("Could not read the Flipkart search page — layout changed or bot protection is active.")
            else:
                log.info("Flipkart page %d not available; keeping %d products.", page, len(results))
            break
        before = len(results)
        _add_products(_find_products(state), results, seen_urls, max_results)
        log.info("Flipkart page %d: %d new products.", page, len(results) - before)
        if len(results) == before:
            break   # an empty page means there are no more results

    log.info("Flipkart: %d products returned.", len(results))
    return results


def _add_products(products: list[dict], results: list[dict], seen_urls: set[str], max_results: int) -> None:
    for p in products:
        if len(results) >= max_results:
            break
        try:
            title = (p.get("titles") or {}).get("title")
            price = _price(p.get("pricing") or {})
            p_url = p.get("smartUrl") or p.get("baseUrl")
            if not title or price is None or not p_url or p_url in seen_urls:
                continue
            seen_urls.add(p_url)

            rating = p.get("rating") or {}
            images = (p.get("media") or {}).get("images") or [{}]
            image = (images[0] or {}).get("url", "")
            if image:
                image = image.replace("{@width}", "400").replace("{@height}", "400").replace("{@quality}", "70")

            results.append({
                "title": str(title),
                "price": f"₹{price}",
                "rating": str(rating.get("average", "N/A")),
                "reviews_count": str(rating.get("count", "N/A")),
                "url": p_url if p_url.startswith("http") else f"{FLIPKART_BASE}{p_url}",
                "image": image or "N/A",
                "source": "flipkart",
            })
        except Exception as e:
            log.warning("Error parsing a Flipkart product: %s", e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(json.dumps(scrape_flipkart(" ".join(sys.argv[1:]) or "mechanical keyboard"), indent=2, ensure_ascii=False))
