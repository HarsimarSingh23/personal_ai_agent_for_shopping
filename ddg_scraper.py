"""
ddg_scraper.py — Other Indian online shops, found through web search (ddgs).

Search engines mostly return review sites and "best X under Y" articles for
shopping queries. To keep results honest, this module:

  * runs a general query plus `site:` queries for a few big Indian shops,
  * keeps only pages on known shop domains (no review sites or blogs),
  * keeps only pages whose title or link matches the product words,
  * never shows a budget phrase ("under ₹3,000", "upto ₹500 off") as a price.

Amazon and Flipkart have their own scrapers and are skipped here. This is the
fallback used by store_scraper.py when Croma and Reliance Digital find nothing.
"""

import logging
import re
import time
from urllib.parse import quote_plus, urlparse

try:
    # pyrefly: ignore [missing-import]
    from ddgs import DDGS
except ImportError:
    raise ImportError("'ddgs' not found.\nRun: pip install ddgs")

from products import is_relevant, query_keywords

log = logging.getLogger(__name__)

MAX_RESULTS = 8
MAX_PER_SHOP = 2
TIME_BUDGET_SECONDS = 10        # stop starting new queries after this
SITE_QUERIES = ("croma.com", "reliancedigital.in", "myntra.com")

_SKIP_DOMAINS = ("amazon.in", "amazon.com", "flipkart.com")

# Root domain → shop name. Only these domains are shown as "other stores".
_KNOWN_SHOPS = {
    "croma.com": "Croma", "reliancedigital.in": "Reliance Digital", "vijaysales.com": "Vijay Sales",
    "tatacliq.com": "Tata CLiQ", "myntra.com": "Myntra", "ajio.com": "AJIO", "nykaa.com": "Nykaa",
    "meesho.com": "Meesho", "snapdeal.com": "Snapdeal", "jiomart.com": "JioMart",
    "shopclues.com": "ShopClues", "decathlon.in": "Decathlon", "boat-lifestyle.com": "boAt",
    "gonoise.com": "Noise", "samsung.com": "Samsung", "mi.com": "Xiaomi", "oneplus.in": "OnePlus",
    "apple.com": "Apple", "lenovo.com": "Lenovo", "hp.com": "HP", "dell.com": "Dell",
    "asus.com": "ASUS", "puma.com": "PUMA", "nike.com": "Nike", "adidas.co.in": "adidas",
    "firstcry.com": "FirstCry", "pepperfry.com": "Pepperfry", "urbanladder.com": "Urban Ladder",
    "lenskart.com": "Lenskart", "bewakoof.com": "Bewakoof", "bigbasket.com": "BigBasket",
    "poorvika.com": "Poorvika", "industrybuying.com": "IndustryBuying",
}

# Shop pages that are articles, not things you can buy.
_ARTICLE_PATH = re.compile(r"/(blog|blogs|unboxed|resource-center|article|articles|news|stories|guide|guides|reviews?|compare)(/|$)")
_ARTICLE_TITLE = re.compile(r"^(best|top\s*\d+|\d+\s+best)\b|\bvs\.?\b|\breview\b", re.IGNORECASE)

_PRICE = re.compile(r"(₹|\bRs\.?|\bINR)\s?(\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE)
# Words that turn a number into a budget or a discount rather than a price.
_BUDGET_BEFORE = re.compile(r"(under|below|upto|up to|within|less than|max|budget|save|off)\s*$", re.IGNORECASE)
_DISCOUNT_AFTER = re.compile(r"^\s*(off|discount|cashback)\b", re.IGNORECASE)


def _shop_for(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if host.startswith(("store.", "stores.", "blog.", "help.", "support.")):
        return None
    for domain, name in _KNOWN_SHOPS.items():
        if host == domain or host.endswith("." + domain):
            return name
    return None


def _is_article(url: str, title: str) -> bool:
    return bool(_ARTICLE_PATH.search(urlparse(url).path.lower()) or _ARTICLE_TITLE.search(title))


def _extract_price(text: str) -> str | None:
    """First real price in `text`; skips budgets ("under ₹3,000") and discounts ("₹500 off")."""
    for m in _PRICE.finditer(text or ""):
        before = text[max(0, m.start() - 15):m.start()]
        after = text[m.end():m.end() + 12]
        if _BUDGET_BEFORE.search(before) or _DISCOUNT_AFTER.search(after):
            continue
        return f"₹{m.group(2)}"
    return None


def _search(ddgs: DDGS, query: str, n: int) -> list[dict]:
    try:
        return list(ddgs.text(query, max_results=n))
    except Exception as e:  # "No results found", rate limits, timeouts
        log.info("Web search returned nothing for %r (%s)", query, type(e).__name__)
        return []


def scrape_ddg(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    started = time.monotonic()
    queries = [f"{query} buy online India"] + [f"{query} site:{site}" for site in SITE_QUERIES]
    keywords = query_keywords(query)
    results: list[dict] = []
    seen_urls: set[str] = set()
    per_shop: dict[str, int] = {}

    log.info("Web shop search for: %r", query)
    try:
        with DDGS(timeout=6) as ddgs:
            for q in queries:
                if len(results) >= max_results or time.monotonic() - started > TIME_BUDGET_SECONDS:
                    break
                for item in _search(ddgs, q, 10):
                    url = (item.get("href") or "").strip()
                    title = (item.get("title") or "").strip()
                    body = item.get("body") or ""
                    shop = _shop_for(url) if url else None
                    if (not shop or not title or url in seen_urls
                            or any(d in url.lower() for d in _SKIP_DOMAINS)
                            or _is_article(url, title)
                            or not is_relevant(keywords, title, url)
                            or per_shop.get(shop, 0) >= MAX_PER_SHOP):
                        continue
                    seen_urls.add(url)
                    per_shop[shop] = per_shop.get(shop, 0) + 1
                    results.append({
                        "title": title,
                        "price": _extract_price(title) or _extract_price(body) or "N/A",
                        "rating": "N/A",
                        "reviews_count": "N/A",
                        "url": url,
                        "image": f"https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url={quote_plus(url)}&size=128",
                        "source": shop,
                    })
                    if len(results) >= max_results:
                        break
    except Exception as e:
        log.error("Web shop search failed: %s", e, exc_info=True)

    log.info("Web shop search done: %d results from %s (%.1fs)", len(results), sorted(per_shop), time.monotonic() - started)
    return results


if __name__ == "__main__":
    import json
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(json.dumps(scrape_ddg(" ".join(sys.argv[1:]) or "wireless earbuds under 3000"), indent=2, ensure_ascii=False))
