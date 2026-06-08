"""
scraper.py — Amazon product scraper for the Personal AI Shopping Agent.

    from scraper import scrape
    results = scrape("mechanical keyboard")
    # returns list[dict]: title, price, rating, reviews_count, url
"""

import json
import logging
import random
import re
import subprocess
import time
import sys

# stdout/stderr encoding is set by the entry-point (agent.py), not here.

try:
    import undetected_chromedriver as uc
except ImportError:
    raise ImportError("'undetected_chromedriver' not found. Run: pip install -r requirements.txt")

try:
    from fake_useragent import UserAgent
except ImportError:
    raise ImportError("'fake_useragent' not found. Run: pip install -r requirements.txt")

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

log = logging.getLogger(__name__)

AMAZON_BASE    = "https://www.amazon.in"
MAX_RESULTS    = 10
PAGE_LOAD_WAIT = 30


def _detect_chrome_version() -> int:
    """Auto-detect installed Chrome major version from the Windows registry."""
    try:
        result = subprocess.run(
            ["reg", "query",
             r"HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon",
             "/v", "version"],
            capture_output=True, text=True, timeout=5,
        )
        match = re.search(r"(\d+)\.\d+", result.stdout)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return 148  # fallback if registry lookup fails


CHROME_VERSION = _detect_chrome_version()

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

_DESKTOP_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.7490.110 Safari/537.36",
]

# Injected via CDP before any page JS runs — removes Selenium/webdriver fingerprints.
_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [
            { name: 'Chrome PDF Plugin',   filename: 'internal-pdf-viewer' },
            { name: 'Chrome PDF Viewer',   filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
            { name: 'Native Client',       filename: 'internal-nacl-plugin' },
        ];
        arr.__proto__ = PluginArray.prototype;
        return arr;
    }
});
Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en-US', 'en'] });
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
window.chrome = window.chrome || {};
window.chrome.runtime = window.chrome.runtime || {};
"""


def _human_pause(min_s: float = 0.5, max_s: float = 1.5) -> None:
    time.sleep(random.uniform(min_s, max_s))


def _desktop_ua() -> str:
    """Return a guaranteed Windows-desktop Chrome user-agent string."""
    try:
        ua = UserAgent(os="windows", browsers=["chrome"])
        candidate = ua.random
        bad = ("Android", "iPhone", "iPad", "Mobile", "Pixel", "arm")
        if not any(k in candidate for k in bad):
            return candidate
    except Exception:
        pass
    return random.choice(_DESKTOP_UAS)


def _safe_text(card, selectors: list[str]) -> str | None:
    for sel in selectors:
        try:
            el = card.find_element(By.CSS_SELECTOR, sel)
            text = el.get_attribute("innerText") or el.text
            if text and text.strip():
                return text.strip()
        except NoSuchElementException:
            continue
    return None


def _safe_attr(card, selectors: list[str], attr: str) -> str | None:
    for sel in selectors:
        try:
            el = card.find_element(By.CSS_SELECTOR, sel)
            val = el.get_attribute(attr)
            if val and val.strip():
                return val.strip()
        except NoSuchElementException:
            continue
    return None


def _is_captcha(driver) -> bool:
    src = driver.page_source.lower()
    return any(k in src for k in (
        "captcha", "robot check", "unusual traffic",
        "automated access", "verify you", "are you a human",
    ))


def _build_driver() -> uc.Chrome:
    ua = _desktop_ua()
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-agent={ua}")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins-discovery")
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")

    log.debug("Starting headless Chrome with UA: %s", ua[:80])
    driver = uc.Chrome(options=options, use_subprocess=True, version_main=CHROME_VERSION)
    driver.set_window_size(1366, 768)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": _STEALTH_JS})
    return driver


def scrape(query: str, max_results: int = MAX_RESULTS) -> list[dict]:
    """
    Search Amazon for *query* and return up to *max_results* products.
    Returns an empty list on failure — never raises.
    Each dict has keys: title, price, rating, reviews_count, url, image.
    """
    results: list[dict] = []
    driver = None

    try:
        driver = _build_driver()

        log.info("Scraping Amazon for: '%s'", query)
        driver.get(AMAZON_BASE)
        _human_pause(2.0, 3.5)

        if _is_captcha(driver):
            log.error("CAPTCHA on homepage — cannot proceed in headless mode.")
            return results

        search_box = None
        for by, sel in [
            (By.ID,   "twotabsearchtextbox"),
            (By.NAME, "field-keywords"),
            (By.CSS_SELECTOR, "input[type='text'][name='field-keywords']"),
            (By.CSS_SELECTOR, "input.nav-input"),
        ]:
            try:
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((by, sel))
                )
                break
            except TimeoutException:
                continue

        if search_box is None:
            log.error("Search box not found — Amazon layout may have changed.")
            return results

        search_box.clear()
        _human_pause(0.3, 0.7)
        for char in query:
            search_box.send_keys(char)
            time.sleep(random.uniform(0.05, 0.14))
        _human_pause(0.5, 1.0)
        search_box.send_keys(Keys.RETURN)

        try:
            WebDriverWait(driver, PAGE_LOAD_WAIT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
                )
            )
        except TimeoutException:
            if _is_captcha(driver):
                log.error("CAPTCHA on results page — cannot solve in headless mode.")
            else:
                log.error("Results page timed out. URL: %s", driver.current_url)
            return results

        _human_pause(0.8, 1.5)

        if _is_captcha(driver):
            log.error("CAPTCHA detected after results load.")
            return results

        cards = []
        for sel in _CARD_SELECTORS:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards:
                break

        if not cards:
            log.error("No product cards found. URL: %s", driver.current_url)
            return results

        log.info("Found %d cards — extracting top %d", len(cards), max_results)

        seen: set[str] = set()
        for card in cards:
            if len(results) >= max_results:
                break
            asin = card.get_attribute("data-asin")
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

    except WebDriverException as e:
        log.error("WebDriver error: %s", e)
    except Exception as e:
        log.error("Unexpected scraper error: %s", e, exc_info=True)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass  # suppress known WinError 6 on Windows cleanup

    log.info("Scrape complete — %d products returned.", len(results))
    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  [%(levelname)s]  %(message)s",
        datefmt="%H:%M:%S",
    )

    query = " ".join(sys.argv[1:]) or "mechanical keyboard"
    data  = scrape(query)

    print(f"\n{'='*60}")
    print(f"  {len(data)} results for: '{query}'")
    print(f"{'='*60}\n")
    print(json.dumps(data, indent=4, ensure_ascii=False))
    print(f"\n{'='*60}\n")
