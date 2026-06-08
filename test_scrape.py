"""
test_scrape.py
==============
Isolated Step-1 Test Script for the Personal AI Shopping Agent.

Purpose : Search Amazon for a hardcoded query, scrape the top-5 product
          results, and pretty-print the extracted data as JSON.

Anti-bot : undetected-chromedriver + CDP stealth injection + amazon.in
           (far less aggressive than amazon.com for Indian IP addresses) +
           realistic delays between every action.

CAPTCHA handling : If a CAPTCHA is detected the script pauses and asks
                   you to solve it in the open browser window, then resumes.
"""

import json
import logging
import random
import time
import sys

# Force UTF-8 output so ₹ and other Unicode characters print correctly
# on Windows terminals that default to CP1252.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# Third-party imports – make sure you have run:
#   pip install -r requirements.txt
# ---------------------------------------------------------------------------
try:
    import undetected_chromedriver as uc
except ImportError:
    sys.exit(
        "[FATAL] 'undetected_chromedriver' not found.\n"
        "Run:  pip install -r requirements.txt"
    )

try:
    from fake_useragent import UserAgent
except ImportError:
    sys.exit(
        "[FATAL] 'fake_useragent' not found.\n"
        "Run:  pip install -r requirements.txt"
    )

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
)

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEARCH_QUERY   = "mechanical keyboard"   # ← Change this to any product
MAX_RESULTS    = 5
PAGE_LOAD_WAIT = 30   # seconds — explicit wait timeout
# Using amazon.in — far fewer bot-checks for Indian IP addresses
AMAZON_BASE    = "https://www.amazon.in"

# Chrome version installed on this machine
CHROME_VERSION = 148

# CSS selectors for product cards on the search results page.
# Amazon occasionally changes its markup; fallback selectors are tried in order.
CARD_SELECTORS = [
    "div[data-component-type='s-search-result']",
    "div.s-result-item[data-asin]",
]

FIELD_SELECTORS = {
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
        "span[aria-label*='5 में से']",  # Hindi localisation on amazon.in
    ],
    "reviews_count": [
        "span.a-size-base.s-underline-text",
        "a[href*='#customerReviews'] span.a-size-base",
        "span.a-size-base",
    ],
    "url": [
        "h2 a.a-link-normal",
        "a.a-link-normal.s-no-outline",
        "h2 a",
    ],
}

# ---------------------------------------------------------------------------
# CDP stealth script — injected into every new page before any JS executes.
# Removes all the standard Selenium/webdriver fingerprints.
# ---------------------------------------------------------------------------
_STEALTH_JS = """
// Remove the automation flag
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Fake a realistic plugin list
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

// Realistic language settings
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-IN', 'en-US', 'en']
});

// Spoof a real hardware concurrency
Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });

// Provide chrome runtime so sites can't detect its absence
window.chrome = window.chrome || {};
window.chrome.runtime = window.chrome.runtime || {};

// Prevent iframe-based detection
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.call(this, parameter);
};
"""


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def human_pause(min_s: float = 0.5, max_s: float = 1.5) -> None:
    """Sleep for a random duration to mimic human think-time."""
    time.sleep(random.uniform(min_s, max_s))


def safe_get_text(card, selectors: list[str]) -> str | None:
    """
    Try each CSS selector in order and return the first non-empty text found.
    Returns None if nothing matches.
    """
    for sel in selectors:
        try:
            el = card.find_element(By.CSS_SELECTOR, sel)
            text = el.get_attribute("innerText") or el.text
            if text and text.strip():
                return text.strip()
        except NoSuchElementException:
            continue
    return None


def safe_get_attr(card, selectors: list[str], attr: str) -> str | None:
    """Return the value of *attr* from the first matching element, or None."""
    for sel in selectors:
        try:
            el = card.find_element(By.CSS_SELECTOR, sel)
            value = el.get_attribute(attr)
            if value and value.strip():
                return value.strip()
        except NoSuchElementException:
            continue
    return None


def is_captcha_page(driver) -> bool:
    """Return True if Amazon is showing a CAPTCHA or bot-check page."""
    src = driver.page_source.lower()
    keywords = ("captcha", "robot check", "unusual traffic", "automated access",
                 "verify you", "prove you", "are you a human")
    return any(kw in src for kw in keywords)


def wait_for_captcha_solve(driver, timeout: int = 120) -> bool:
    """
    Pause execution, notify the user to solve the CAPTCHA in the open browser,
    and wait up to *timeout* seconds for the results page to appear.
    Returns True if solved successfully, False if timed out.
    """
    log.warning("=" * 60)
    log.warning("  ⚠  CAPTCHA DETECTED")
    log.warning("  Please solve it in the browser window, then wait…")
    log.warning("=" * 60)
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
            )
        )
        log.info("✓ CAPTCHA solved — results page loaded.")
        return True
    except TimeoutException:
        log.error("CAPTCHA was not solved within %ds. Giving up.", timeout)
        return False


# ---------------------------------------------------------------------------
# Driver factory
# ---------------------------------------------------------------------------

# Fallback pool of desktop Windows Chrome user-agents
_DESKTOP_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.7490.110 Safari/537.36",
]


def _desktop_ua() -> str:
    """Return a guaranteed-desktop Chrome user-agent string."""
    try:
        ua = UserAgent(os="windows", browsers=["chrome"])
        candidate = ua.random
        mobile_keywords = ("Android", "iPhone", "iPad", "Mobile", "Pixel", "arm")
        if not any(kw in candidate for kw in mobile_keywords):
            return candidate
    except Exception:
        pass
    return random.choice(_DESKTOP_UAS)


def build_driver() -> uc.Chrome:
    """
    Construct an undetected-chromedriver instance with comprehensive
    anti-fingerprint options and CDP stealth injection.
    """
    spoofed_ua = _desktop_ua()

    options = uc.ChromeOptions()

    # ── Stealth flags ──────────────────────────────────────────────────────
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--user-agent={spoofed_ua}")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins-discovery")
    # Headless mode — no browser window opens (required for backend/server deployment)
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")          # prevents GPU errors on headless servers
    # NOTE: excludeSwitches / useAutomationExtension are patched automatically
    #       by undetected_chromedriver — do NOT set them via add_experimental_option.

    log.info("Launching browser (HEADLESS) with user-agent: %s", spoofed_ua[:80] + "…")

    driver = uc.Chrome(
        options=options,
        use_subprocess=True,
        version_main=CHROME_VERSION,
    )
    driver.set_window_size(1366, 768)

    # ── Inject CDP stealth patches ─────────────────────────────────────────
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": _STEALTH_JS},
    )
    log.info("CDP stealth patches injected.")
    return driver


# ---------------------------------------------------------------------------
# Core scraping logic
# ---------------------------------------------------------------------------

def search_amazon(driver: uc.Chrome, query: str) -> list[dict]:
    """
    Navigate to Amazon, search for *query*, and scrape up to MAX_RESULTS products.
    Returns a list of product dicts.
    """
    results: list[dict] = []

    try:
        log.info("Navigating to %s …", AMAZON_BASE)
        driver.get(AMAZON_BASE)
        human_pause(2.0, 3.5)   # longer initial wait to appear human

        # Check for CAPTCHA immediately on homepage
        if is_captcha_page(driver):
            if not wait_for_captcha_solve(driver):
                return results

        # ── Locate search box ─────────────────────────────────────────────
        log.info("Waiting for search box…")
        SEARCH_BOX_SELECTORS = [
            (By.ID,   "twotabsearchtextbox"),
            (By.NAME, "field-keywords"),
            (By.CSS_SELECTOR, "input[type='text'][name='field-keywords']"),
            (By.CSS_SELECTOR, "input.nav-input"),
        ]
        search_box = None
        for by, selector in SEARCH_BOX_SELECTORS:
            try:
                search_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((by, selector))
                )
                log.info("Search box found via: %s=%s", by, selector)
                break
            except TimeoutException:
                continue

        if search_box is None:
            log.error("Could not locate search box — page source snippet:\n%s",
                      driver.page_source[:500])
            return results

        search_box.clear()
        human_pause(0.4, 0.8)

        # Type character-by-character to mimic human input speed
        for char in query:
            search_box.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))

        human_pause(0.6, 1.2)
        search_box.send_keys(Keys.RETURN)

        # ── Wait for results page ─────────────────────────────────────────
        log.info("Waiting for results page…")
        try:
            WebDriverWait(driver, PAGE_LOAD_WAIT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[data-component-type='s-search-result']")
                )
            )
        except TimeoutException:
            # Results div not found — might be CAPTCHA or slow load
            if is_captcha_page(driver):
                if not wait_for_captcha_solve(driver):
                    return results
            else:
                log.error(
                    "Results page timed out after %ds. "
                    "Current URL: %s", PAGE_LOAD_WAIT, driver.current_url
                )
                return results

        human_pause(1.0, 2.0)

        # Final CAPTCHA check after results load
        if is_captcha_page(driver):
            if not wait_for_captcha_solve(driver):
                return results

        # ── Find product cards ────────────────────────────────────────────
        cards = []
        for sel in CARD_SELECTORS:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards:
                log.info("Found %d product cards via selector: %s", len(cards), sel)
                break

        if not cards:
            log.error("No product cards found — Amazon may have changed its markup.")
            log.error("Current URL: %s", driver.current_url)
            return results

        # ── Extract fields from each card ─────────────────────────────────
        seen_asins: set[str] = set()
        for card in cards:
            if len(results) >= MAX_RESULTS:
                break

            asin = card.get_attribute("data-asin")
            if not asin or asin in seen_asins:
                continue
            seen_asins.add(asin)

            try:
                title         = safe_get_text(card, FIELD_SELECTORS["title"])
                price         = safe_get_text(card, FIELD_SELECTORS["price"])
                rating        = safe_get_text(card, FIELD_SELECTORS["rating"])
                reviews_count = safe_get_text(card, FIELD_SELECTORS["reviews_count"])

                relative_url = safe_get_attr(card, FIELD_SELECTORS["url"], "href")
                if relative_url:
                    full_url = relative_url if relative_url.startswith("http") \
                               else AMAZON_BASE + relative_url
                else:
                    full_url = None

                if not title:
                    continue

                product = {
                    "title":         title         or "N/A",
                    "price":         price         or "N/A",
                    "rating":        rating        or "N/A",
                    "reviews_count": reviews_count or "N/A",
                    "url":           full_url      or "N/A",
                }
                results.append(product)
                log.info("  ✓ [%d] %s", len(results),
                         title[:72] + ("…" if len(title) > 72 else ""))

            except Exception as field_err:
                log.warning("Skipped one card due to error: %s", field_err)
                continue

    except TimeoutException:
        log.error("Unexpected timeout. Current URL: %s", driver.current_url)
    except WebDriverException as wd_err:
        log.error("WebDriver error: %s", wd_err)
    except Exception as ex:
        log.error("Unexpected error during scraping: %s", ex, exc_info=True)

    return results


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    log.info("=" * 60)
    log.info("  Amazon Scraper  —  Query: '%s'", SEARCH_QUERY)
    log.info("  Target: %s", AMAZON_BASE)
    log.info("=" * 60)

    driver = None
    try:
        driver = build_driver()
        data = search_amazon(driver, SEARCH_QUERY)
    finally:
        if driver:
            log.info("Closing browser…")
            try:
                driver.quit()
            except Exception:
                pass  # suppress the known WinError 6 on Windows cleanup

    # ── Pretty-print results ───────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  RESULTS  ({len(data)} products found for: '{SEARCH_QUERY}')")
    print("=" * 60 + "\n")

    if data:
        print(json.dumps(data, indent=4, ensure_ascii=False))
    else:
        print("No products were scraped. Check the log messages above for clues.")

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
