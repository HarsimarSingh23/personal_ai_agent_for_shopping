
import logging
import random
import time
from urllib.parse import quote_plus


try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError(
        "'requests' or 'beautifulsoup4' not found.\n"
        "Run: pip install -r requirements.txt"
    )

try:
    import lxml  # noqa: F401
    _PARSER = "lxml"
except ImportError:
    import warnings
    warnings.warn(
        "lxml is not installed — falling back to html.parser. "
        "Flipkart CSS selectors may not work correctly. "
        "Install lxml: pip install lxml",
        stacklevel=2,
    )
    _PARSER = "html.parser"

log = logging.getLogger(__name__)

FLIPKART_BASE   = "https://www.flipkart.com"
FLIPKART_SEARCH = "https://www.flipkart.com/search?q={query}&otracker=search"
MAX_RESULTS     = 10
REQUEST_TIMEOUT = 15

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

_session = requests.Session()
_session.headers.update({
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.flipkart.com/",
    "DNT": "1",
})

_CARD_CONFIGS = [
    {
        "container": "div[data-id]",
        "title":     ["div._4rR01T", "a.s1Q9rs", "div.KzDlHZ", "a.wjcEIp"],
        "price":     ["div._30jeq3", "div.Nx9bqj", "div._1_WHN1"],
        "rating":    ["div._3LWZlK", "div.XQDdHH"],
        "reviews":   ["span._2_R_DZ", "span.Wphh3N"],
        "link":      ["a._1fQZEK", "a.s1Q9rs", "a.wjcEIp", "a._2rpwqI"],
        "image":     ["img._396cs4", "img.DByuf4", "img"],
    },
    {
        "container": "div._1AtVbE",
        "title":     ["div._4rR01T", "a.IRpwTa", "div.s1Q9rs"],
        "price":     ["div._30jeq3", "div._25b18c div._30jeq3"],
        "rating":    ["div._3LWZlK"],
        "reviews":   ["span._2_R_DZ"],
        "link":      ["a.s1Q9rs", "a._1fQZEK"],
        "image":     ["img._396cs4", "img._2r_T1I", "img"],
    },
]

_POPUP_SELECTORS = [
    "button._2KpZ6l._2doB4z",
    "button.LbYjBf-geS5jf-fAtFfn",
]


def _headers() -> dict:
    return {"User-Agent": random.choice(_USER_AGENTS)}


def _safe_text(tag, selectors: list[str]) -> str | None:
    for sel in selectors:
        el = tag.select_one(sel)
        if el and el.get_text(strip=True):
            return el.get_text(strip=True)
    return None


def _safe_href(tag, selectors: list[str]) -> str | None:
    for sel in selectors:
        el = tag.select_one(sel)
        if el and el.get("href"):
            href = el["href"]
            return href if href.startswith("http") else FLIPKART_BASE + href
    return None


def _safe_src(tag, selectors: list[str]) -> str | None:
    for sel in selectors:
        el = tag.select_one(sel)
        if el and el.get("src") and el.get("src").startswith("http"):
            return el["src"]
    return None


def _dismiss_login_popup(soup: BeautifulSoup) -> BeautifulSoup:
    for sel in _POPUP_SELECTORS:
        if soup.select_one(sel):
            log.warning(
                "Flipkart: login popup detected in HTML source. "
                "Product selectors may find fewer results. "
                "Consider adding a logged-in session cookie or using a headless browser."
            )
            break
    return soup


def scrape_flipkart(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    results: list[dict] = []
    url = FLIPKART_SEARCH.format(query=quote_plus(query))

    try:
        log.info("Scraping Flipkart for: '%s'", query)
        time.sleep(random.uniform(0.5, 1.2))

        resp = _session.get(url, headers=_headers(), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, _PARSER)

        soup = _dismiss_login_popup(soup)

        cards = []
        config = None
        for cfg in _CARD_CONFIGS:
            cards = soup.select(cfg["container"])
            valid = [c for c in cards if any(c.select_one(s) for s in cfg["title"])]
            if valid:
                cards = valid
                config = cfg
                log.info("Flipkart: %d cards via '%s'", len(cards), cfg["container"])
                break

        if not cards or config is None:
            log.warning("Flipkart: No product cards found for '%s'", query)
            return results

        for card in cards:
            if len(results) >= max_results:
                break
            try:
                title = _safe_text(card, config["title"])
                if not title:
                    continue

                price   = _safe_text(card, config["price"])
                rating  = _safe_text(card, config["rating"])
                reviews = _safe_text(card, config["reviews"])
                url_    = _safe_href(card, config["link"])
                image   = _safe_src(card, config["image"])

                results.append({
                    "title":         title   or "N/A",
                    "price":         price   or "N/A",
                    "rating":        rating  or "N/A",
                    "reviews_count": reviews or "N/A",
                    "url":           url_    or "N/A",
                    "image":         image   or "N/A",
                    "source":        "flipkart",
                })
                log.debug("  [FK %d] %s", len(results), title[:70])

            except Exception as e:
                log.warning("Flipkart: skipped a card — %s", e)
                continue

    except requests.exceptions.RequestException as e:
        log.error("Flipkart request failed: %s", e)
    except Exception as e:
        log.error("Flipkart unexpected error: %s", e, exc_info=True)

    log.info("Flipkart scrape complete — %d products returned.", len(results))
    return results
