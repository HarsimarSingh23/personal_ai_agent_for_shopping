"""
ddg_scraper.py — DuckDuckGo product search across any shopping site.

    from ddg_scraper import scrape_ddg
    results = scrape_ddg("Intel i5 gaming CPU processor")
    # returns list[dict]: title, price, url, source, rating, reviews_count
"""

import logging
import re
import time

# stdout/stderr encoding is set by the entry-point (agent.py), not here.

try:
    from duckduckgo_search import DDGS
except ImportError:
    raise ImportError(
        "'duckduckgo-search' not found.\n"
        "Run: pip install duckduckgo-search"
    )

log = logging.getLogger(__name__)

MAX_RESULTS = 10

_SKIP_DOMAINS = {"amazon.in", "amazon.com", "flipkart.com"}

_KNOWN_SHOPS = {
    "croma.com":       "Croma",
    "meesho.com":      "Meesho",
    "snapdeal.com":    "Snapdeal",
    "myntra.com":      "Myntra",
    "tatacliq.com":    "Tata Cliq",
    "reliancedigital": "Reliance Digital",
    "vijaysales.com":  "Vijay Sales",
    "paytmmall.com":   "Paytm Mall",
    "shopclues.com":   "ShopClues",
    "industrybuying":  "IndustryBuying",
}


def _domain_label(url: str) -> str:
    url_lower = url.lower()
    for domain, label in _KNOWN_SHOPS.items():
        if domain in url_lower:
            return label
    match = re.search(r"https?://(?:www\.)?([^/]+)", url_lower)
    return match.group(1).split(".")[0].capitalize() if match else "Web"


def _extract_price(text: str) -> str | None:
    """Pull a price string (₹/Rs./INR/$) out of a snippet."""
    match = re.search(r"(₹|Rs\.?|INR|\$)\s?[\d,]+(?:\.\d{1,2})?", text)
    return match.group(0).strip() if match else None


def scrape_ddg(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    """
    Search DuckDuckGo for shopping results across the web (excludes Amazon/Flipkart).
    Returns an empty list on failure — never raises.
    """
    results: list[dict] = []
    search_query = f"{query} buy online India price -site:amazon.in -site:flipkart.com"

    try:
        log.info("DDG search for: '%s'", query)
        raw = []
        # Retry up to 3 times with exponential backoff on DDG rate-limit errors
        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    raw = list(ddgs.text(search_query, max_results=max_results * 3))
                break
            except Exception as ddg_err:
                err_str = str(ddg_err)
                if attempt < 2 and any(
                    k in err_str for k in ("202", "429", "Ratelimit", "rate", "timeout")
                ):
                    wait = 2 ** attempt
                    log.warning(
                        "DDG rate-limited (attempt %d/3) — retrying in %ds… (%s)",
                        attempt + 1, wait, ddg_err,
                    )
                    time.sleep(wait)
                else:
                    raise

        seen_domains: set[str] = set()
        for item in raw:
            if len(results) >= max_results:
                break

            url   = item.get("href", "")
            title = item.get("title", "").strip()
            body  = item.get("body", "")

            if not url or not title:
                continue

            url_lower = url.lower()
            if any(d in url_lower for d in _SKIP_DOMAINS):
                continue

            # One result per domain — avoids flooding from one site
            match = re.search(r"https?://(?:www\.)?([^/]+)", url_lower)
            domain = match.group(1) if match else url_lower
            if domain in seen_domains:
                continue
            seen_domains.add(domain)

            price = _extract_price(title) or _extract_price(body)

            results.append({
                "title":         title,
                "price":         price  or "N/A",
                "rating":        "N/A",
                "reviews_count": "N/A",
                "url":           url,
                "image":         "N/A",
                "source":        _domain_label(url),
            })
            log.debug("  [DDG] %s — %s", _domain_label(url), title[:60])

    except Exception as e:
        log.error("DuckDuckGo search failed: %s", e, exc_info=True)

    log.info("DDG search complete — %d results.", len(results))
    return results
