
import json
import logging
import random
import sys
import time
from urllib.parse import quote_plus

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError("'beautifulsoup4' not found. Run: pip install beautifulsoup4")

try:
    from curl_cffi import requests
except ImportError:
    raise ImportError("'curl_cffi' not found. Run: pip install curl_cffi")

from config import settings

log = logging.getLogger(__name__)

AMAZON_BASE    = "https://www.amazon.in"
PAGES          = settings.scrape_pages          # SCRAPE_PAGES, default 2
MAX_RESULTS    = 16 * PAGES                     # one search page has about 16 products

_CARD_SELECTORS = [
    "div[data-component-type='s-search-result']",
    "div.s-result-item[data-asin]",
]

_FIELD_SELECTORS = {
    "title": [
        # 2026 layout: brand in h2.s-line-clamp-1, product name in h2.a-text-normal.
        "h2.a-text-normal span",
        "h2.a-text-normal",
        "h2.a-size-mini a span",
        "h2 a.a-link-normal span",
        "span.a-size-medium.a-color-base.a-text-normal",
        "h2 span",
        "span.a-text-normal",
    ],
    "price": [
        "span.a-price > span.a-offscreen",
        "span.a-price-whole",
        "span.a-color-price",
    ],
    "rating": [
        "span.a-icon-alt",
        "i.a-icon-star span.a-icon-alt",
        "span[aria-label*='out of 5 stars']",
    ],
    "reviews_count": [
        "span.a-size-base.s-underline-text",
        "a[href*='#customerReviews'] span.a-size-base",
        "a[href*='customerReviews'] span",
    ],
    "url": [
        "h2 a.a-link-normal",
        "a.a-link-normal.s-no-outline",
        "h2 a",
    ],
    "image": [
        "img.s-image",
        "img[data-image-latency='s-product-image']",
    ],
}


_BRAND_SELECTORS = ["h2.s-line-clamp-1:not(.a-text-normal)"]


def _is_sponsored(card) -> bool:
    """Paid placements are often a different product (iPhone 16 for "iphone 15")."""
    return "AdHolder" in (card.get("class") or []) or bool(
        card.select_one(".puis-sponsored-label-text, .s-sponsored-label-text")
    )


_REVIEW_LABEL_SELECTORS = [
    "a[aria-label$=' ratings']",
    "a[aria-label$=' rating']",
    "span[aria-label$=' ratings']",
]


def _safe_text(card, selectors: list[str]) -> str | None:
    for sel in selectors:
        el = card.select_one(sel)
        if el:
            text = el.get_text(strip=True)
            if text:
                return text
    return None


def _safe_attr(card, selectors: list[str], attr: str) -> str | None:
    for sel in selectors:
        el = card.select_one(sel)
        if el:
            val = el.get(attr)
            if val and val.strip():
                return val.strip()
    return None


def _is_captcha(html: str) -> bool:
    src = html.lower()
    return any(k in src for k in (
        "captcha", "robot check", "unusual traffic",
        "automated access", "verify you", "are you a human",
    ))


def _fetch_cards(session, url: str, attempts: int) -> list | None:
    """Product cards of one search page, or None if Amazon blocked or changed the page."""
    for attempt in range(1, attempts + 1):
        try:
            log.info("Fetching %s (attempt %d of %d)", url, attempt, attempts)
            response = session.get(url, timeout=15)
            html = response.text

            # Check for Akamai Interstitial Challenge
            if "triggerInterstitialChallenge" in html:
                log.warning("Akamai Interstitial challenge detected. Attempting to solve...")
                import re
                math_match = re.search(r'var i = (\d+);\s*var j = i \+ Number\("(\d+)" \+ "(\d+)"\);', html)
                if math_match:
                    j_val = int(math_match.group(1)) + int(math_match.group(2) + math_match.group(3))
                    bm_match = re.search(r'"bm-verify":\s*"([^"]+)"', html)
                    if bm_match:
                        post_data = {"bm-verify": bm_match.group(1), "pow": j_val}
                        session.post("https://www.amazon.in/_sec/verify?provider=interstitial", json=post_data, timeout=15)
                        # Fetch the page again now that we have the clearance cookie
                        response = session.get(url, timeout=15)
                        html = response.text
                        log.info("Solved interstitial challenge.")
                    else:
                        log.warning("Could not find bm-verify payload.")
                else:
                    log.warning("Could not parse JS math problem.")

            if response.status_code == 503 or _is_captcha(html):
                log.warning("Amazon blocked the request (status %s) on attempt %d.", response.status_code, attempt)
            else:
                soup = BeautifulSoup(html, "html.parser")
                for sel in _CARD_SELECTORS:
                    cards = soup.select(sel)
                    if cards:
                        return cards
                log.error("No product cards found. Amazon may have changed its markup.")
        except Exception as e:
            log.error("Error on attempt %d: %s", attempt, e)
        if attempt < attempts:
            time.sleep(random.uniform(2, 4))
    return None


def _parse_card(card) -> dict | None:
    title = _safe_text(card, _FIELD_SELECTORS["title"])
    if not title:
        return None
    brand = _safe_text(card, _BRAND_SELECTORS)
    if brand and brand != title and not title.lower().startswith(brand.lower()):
        title = f"{brand} {title}"      # "Apple" + "iPhone 15 (128 GB)"

    price   = _safe_text(card, _FIELD_SELECTORS["price"])
    rating  = _safe_text(card, _FIELD_SELECTORS["rating"])
    # Amazon (2026) shows "(53.4K)" with aria-label "53,496 ratings"; the label is exact.
    reviews = (_safe_attr(card, _REVIEW_LABEL_SELECTORS, "aria-label")
               or _safe_text(card, _FIELD_SELECTORS["reviews_count"]))
    href    = _safe_attr(card, _FIELD_SELECTORS["url"], "href")
    url     = href if (href and href.startswith("http")) \
              else (AMAZON_BASE + href if href else None)
    img_src = _safe_attr(card, _FIELD_SELECTORS["image"], "src")

    return {
        "title":         title   or "N/A",
        "price":         price   or "N/A",
        "rating":        rating  or "N/A",
        "reviews_count": reviews or "N/A",
        "url":           url     or "N/A",
        "image":         img_src or "N/A",
    }


def scrape(query: str, max_results: int = MAX_RESULTS, pages: int = PAGES) -> list[dict]:
    """Amazon.in search results from up to `pages` result pages.

    Page 1 is retried if Amazon blocks it. Later pages are tried once, after a
    short pause; if one is blocked we keep what we already have.
    """
    results: list[dict] = []
    seen: set[str] = set()
    search_url = f"{AMAZON_BASE}/s?k={quote_plus(query)}"
    log.info("Scraping Amazon via curl_cffi: %s (up to %d pages)", search_url, pages)

    # Use a session to maintain cookies from JS challenges
    session = requests.Session(impersonate="safari15_5")

    for page in range(1, pages + 1):
        if len(results) >= max_results:
            break
        if page > 1:
            time.sleep(random.uniform(1.0, 2.0))
        url = search_url if page == 1 else f"{search_url}&page={page}"
        cards = _fetch_cards(session, url, attempts=3 if page == 1 else 1)
        if not cards:
            if page > 1:
                log.info("Amazon page %d not available; keeping %d products.", page, len(results))
            break

        before = len(results)
        for card in cards:
            if len(results) >= max_results:
                break
            asin = card.get("data-asin")
            # Sponsored check first, so an ad doesn't hide the same product's normal listing.
            if not asin or asin in seen or _is_sponsored(card):
                continue
            seen.add(asin)
            try:
                item = _parse_card(card)
            except Exception as e:
                log.warning("Skipped a card: %s", e)
                continue
            if item:
                results.append(item)
                log.debug("  [%d] %s", len(results), item["title"][:70])
        log.info("Amazon page %d: %d cards, %d new products.", page, len(cards), len(results) - before)

    log.info("Scrape complete — %d products returned.", len(results))
    return results


if __name__ == "__main__":
    if sys.stdout.encoding.lower() != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  [%(levelname)s]  %(message)s",
        datefmt="%H:%M:%S",
    )

    query_str = " ".join(sys.argv[1:]) or "mechanical keyboard"
    scraped_data = scrape(query_str)

    print(f"\n{'='*60}")
    print(f"  {len(scraped_data)} results for: '{query_str}'")
    print(f"{'='*60}\n")
    print(json.dumps(scraped_data, indent=4, ensure_ascii=False))
    print(f"\n{'='*60}\n")
