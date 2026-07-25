
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

log = logging.getLogger(__name__)

AMAZON_BASE    = "https://www.amazon.in"
MAX_RESULTS    = 10

_CARD_SELECTORS = [
    "div[data-component-type='s-search-result']",
    "div.s-result-item[data-asin]",
]

_FIELD_SELECTORS = {
    "title": [
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


def scrape(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    results: list[dict] = []
    
    search_url = f"{AMAZON_BASE}/s?k={quote_plus(query)}"
    log.info("Scraping Amazon via curl_cffi: %s", search_url)

    # Use a session to maintain cookies from JS challenges
    session = requests.Session(impersonate="safari15_5")

    for attempt in range(1, 4):
        try:
            log.info("Attempt %d of 3...", attempt)
            response = session.get(search_url, timeout=15)
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
                        response = session.get(search_url, timeout=15)
                        html = response.text
                        log.info("Solved interstitial challenge.")
                    else:
                        log.warning("Could not find bm-verify payload.")
                else:
                    log.warning("Could not parse JS math problem.")

            if response.status_code == 503:
                log.warning("Got 503 Service Unavailable.")
                if _is_captcha(html):
                    log.warning("CAPTCHA detected in 503 response on attempt %d. Retrying...", attempt)
                time.sleep(random.uniform(2, 4))
                continue
                
            if _is_captcha(html):
                log.warning("CAPTCHA detected on attempt %d. Retrying...", attempt)
                time.sleep(random.uniform(2, 4))
                continue

            soup = BeautifulSoup(html, "html.parser")

            cards = []
            for sel in _CARD_SELECTORS:
                cards = soup.select(sel)
                if cards:
                    break

            if not cards:
                log.error("No product cards found. Amazon may have changed its markup.")
                time.sleep(random.uniform(2, 4))
                continue

            log.info("Found %d cards — extracting top %d", len(cards), max_results)

            seen: set[str] = set()
            for card in cards:
                if len(results) >= max_results:
                    break
                asin = card.get("data-asin")
                if not asin or asin in seen:
                    continue
                seen.add(asin)

                try:
                    title = _safe_text(card, _FIELD_SELECTORS["title"])
                    if not title:
                        continue

                    price   = _safe_text(card, _FIELD_SELECTORS["price"])
                    rating  = _safe_text(card, _FIELD_SELECTORS["rating"])
                    reviews = _safe_text(card, _FIELD_SELECTORS["reviews_count"])
                    href    = _safe_attr(card, _FIELD_SELECTORS["url"], "href")
                    url     = href if (href and href.startswith("http")) \
                              else (AMAZON_BASE + href if href else None)
                    img_src = _safe_attr(card, _FIELD_SELECTORS["image"], "src")

                    results.append({
                        "title":         title   or "N/A",
                        "price":         price   or "N/A",
                        "rating":        rating  or "N/A",
                        "reviews_count": reviews or "N/A",
                        "url":           url     or "N/A",
                        "image":         img_src or "N/A",
                    })
                    log.debug("  [%d] %s", len(results), title[:70])

                except Exception as e:
                    log.warning("Skipped a card: %s", e)
                    continue

            if results:
                break

        except Exception as e:
            log.error("Error on attempt %d: %s", attempt, e)
            time.sleep(random.uniform(2, 4))

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
