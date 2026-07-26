
import logging
import re
import time
from urllib.parse import quote_plus


try:
    # pyrefly: ignore [missing-import]
    from ddgs import DDGS
except ImportError:
    raise ImportError(
        "'ddgs' not found.\n"
        "Run: pip install ddgs"
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


def _root_domain(url: str) -> str:
    match = re.search(r"https?://(?:www\.)?([^/]+)", url.lower())
    if not match:
        return url.lower()
    host = match.group(1)
    host = match.group(1)
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) > 2 else host


def _domain_label(url: str) -> str:
    url_lower = url.lower()
    for domain, label in _KNOWN_SHOPS.items():
        if domain in url_lower:
            return label
    match = re.search(r"https?://(?:www\.)?([^/]+)", url_lower)
    return match.group(1).split(".")[0].capitalize() if match else "Web"


def _extract_price(text: str) -> str | None:
    match = re.search(r"(₹|Rs\.?|INR|\$)\s?[\d,]+(?:\.\d{1,2})?", text)
    return match.group(0).strip() if match else None


def scrape_ddg(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    results: list[dict] = []
    search_query = f"{query} buy online India price -site:amazon.in -site:flipkart.com"

    _RETRYABLE_SIGNALS = (
        "202", "429", "Ratelimit", "rate", "timeout",
        "connection", "ssl", "ConnectionError", "SSLError",
        "RemoteDisconnected", "IncompleteRead",
    )

    try:
        log.info("DDG search for: '%s'", query)
        raw = []
        for attempt in range(3):
            try:
                with DDGS() as ddgs:
                    raw = list(ddgs.text(search_query, max_results=max_results * 3))
                break
            except Exception as ddg_err:
                err_str = str(ddg_err)
                err_type = type(ddg_err).__name__
                is_retryable = attempt < 2 and (
                    any(k in err_str for k in _RETRYABLE_SIGNALS)
                    or any(k in err_type for k in _RETRYABLE_SIGNALS)
                )
                if is_retryable:
                    wait = 2 ** attempt
                    log.warning(
                        "DDG error (attempt %d/3) — retrying in %ds… (%s: %s)",
                        attempt + 1, wait, err_type, ddg_err,
                    )
                    time.sleep(wait)
                else:
                    raise

        seen_root_domains: set[str] = set()
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

            root = _root_domain(url)
            if root in seen_root_domains:
                continue
            seen_root_domains.add(root)

            price = _extract_price(title) or _extract_price(body)

            results.append({
                "title":         title,
                "price":         price  or "N/A",
                "rating":        "N/A",
                "reviews_count": "N/A",
                "url":           url,
                "image":         f"https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url={quote_plus(url)}&size=128",
                "source":        _domain_label(url),
            })
            log.debug("  [DDG] %s — %s", _domain_label(url), title[:60])

    except Exception as e:
        log.error("DuckDuckGo search failed: %s", e, exc_info=True)

    log.info("DDG search complete — %d results.", len(results))
    return results
