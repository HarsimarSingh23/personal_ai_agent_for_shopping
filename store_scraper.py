"""
store_scraper.py — "Other stores": Croma and Reliance Digital.

Both shops have a public product-search API that their own websites use, so
we get real products with prices, ratings and images (not just links). They
sell electronics and appliances; for anything else (shoes, clothes, …) they
return nothing useful, and we fall back to a web search for other Indian
shops (ddg_scraper.py).

Every product is checked against the query words, so a search for "running
shoes" never shows a "shoe rack dehumidifier".
"""

from __future__ import annotations

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from itertools import zip_longest
from urllib.parse import quote

from curl_cffi import requests

from config import settings
from ddg_scraper import scrape_ddg
from products import is_relevant, parse_price, query_keywords, split_budget

log = logging.getLogger(__name__)

PAGES = max(2, settings.scrape_pages)   # SCRAPE_PAGES; Croma reads at least 2 pages
PER_STORE = 8 * PAGES
TIMEOUT_SECONDS = 10

_CROMA_API = (
    "https://api.croma.com/searchservices/v1/search?currentPage={page}&query={query}"
    "&fields=FULL&channel=WEB&channelCode=400049&spellOpt=DEFAULT"
)
_RELIANCE_API = "https://www.reliancedigital.in/ext/raven-api/catalog/v1.0/products?q={query}&page_size={size}"


def _get_json(url: str) -> dict:
    resp = requests.get(url, impersonate="chrome", timeout=TIMEOUT_SECONDS,
                        headers={"Accept": "application/json"})
    resp.raise_for_status()
    return resp.json()


def _pick(products: list[dict], keywords: list[str], max_price: float | None) -> list[dict]:
    """Relevant, within budget, no duplicates, at most PER_STORE."""
    out, seen = [], set()
    for p in products:
        price = parse_price(p["price"])
        # Colour variants ("… (Black)", "…, Awesome Lilac") of one model count once.
        key = (re.split(r"[(,]", p["title"].lower())[0].strip(), price)
        if (key in seen or not is_relevant(keywords, p["title"])
                or (max_price is not None and (price is None or price > max_price))):
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= PER_STORE:
            break
    return out


def scrape_croma(query: str) -> list[dict]:
    text, max_price = split_budget(query)
    # Croma gives 21 products per page; read PAGES pages so enough remain after
    # the relevance and budget checks. Only the first page is required.
    raw = []
    for page in range(PAGES):
        try:
            data = _get_json(_CROMA_API.format(page=page, query=quote(f"{text}:relevance")))
        except Exception:
            if page == 0:
                raise
            log.info("Croma page %d failed; keeping the earlier pages", page + 1)
            break
        for item in data.get("products") or []:
            price = (item.get("price") or {}).get("value")
            rating = item.get("averageRating") or 0
            count = item.get("numberOfRatings") or 0
            if not item.get("name") or not item.get("url") or not price:
                continue
            raw.append({
                "title": item["name"].strip(),
                "price": f"₹{price:.0f}",
                "rating": f"{rating:.1f}" if rating > 0 and count > 0 else "N/A",
                "reviews_count": str(count) if count > 0 else "N/A",
                "url": "https://www.croma.com" + item["url"],
                "image": item.get("plpImage") or "N/A",
                "source": "Croma",
            })
    return _pick(raw, query_keywords(query), max_price)


def scrape_reliance(query: str) -> list[dict]:
    _, max_price = split_budget(query)
    # Reliance's search understands "under 3000" itself, so send the full query.
    # One request returns up to 100 products, so no paging is needed.
    data = _get_json(_RELIANCE_API.format(query=quote(query), size=min(100, 40 * PAGES)))
    raw = []
    for item in data.get("items") or []:
        price = (((item.get("price") or {}).get("effective")) or {}).get("min")
        if not item.get("name") or not item.get("slug") or not price or item.get("sellable") is False:
            continue
        medias = [m for m in item.get("medias") or [] if m.get("type") == "image" and m.get("url")]
        rating = item.get("rating") or 0
        count = item.get("rating_count") or 0
        raw.append({
            "title": item["name"].strip(),
            "price": f"₹{price:.0f}",
            "rating": f"{rating:.1f}" if rating > 0 else "N/A",
            "reviews_count": str(count) if count else "N/A",
            "url": "https://www.reliancedigital.in/product/" + item["slug"],
            "image": medias[0]["url"] if medias else "N/A",
            "source": "Reliance Digital",
        })
    return _pick(raw, query_keywords(query), max_price)


_STORES = {"Croma": scrape_croma, "Reliance Digital": scrape_reliance}


def scrape_other_stores(query: str) -> list[dict]:
    """Croma + Reliance Digital in parallel; web search if both have nothing."""
    started = time.monotonic()
    found: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=len(_STORES), thread_name_prefix="store") as pool:
        futures = {name: pool.submit(fn, query) for name, fn in _STORES.items()}
        for name, future in futures.items():
            try:
                found[name] = future.result()
            except Exception as e:  # one shop being down must not hide the other
                log.warning("%s search failed: %s", name, e)
                found[name] = []

    # Alternate between shops so both show near the top.
    results = [p for row in zip_longest(*found.values()) for p in row if p]
    log.info("Other stores: %s (%.1fs)", {k: len(v) for k, v in found.items()}, time.monotonic() - started)

    if not results:
        log.info("Croma and Reliance had nothing for %r; trying web search", query)
        results = scrape_ddg(query)
    return results


if __name__ == "__main__":
    import json
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(json.dumps(scrape_other_stores(" ".join(sys.argv[1:]) or "wireless earbuds under 3000"),
                     indent=2, ensure_ascii=False))
