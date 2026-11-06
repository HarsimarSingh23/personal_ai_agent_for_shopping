"""
pipeline.py — The search pipeline behind POST /api/search.

    translate → parallel scrape (Amazon, Flipkart, web) → normalise →
    accessory filter → LLM recommendation

Scrapers run on a shared, long-lived thread pool. The request waits at most
SCRAPE_TIMEOUT_SECONDS; a slow source is reported as "timeout" and the
response goes out with whatever finished. (Using `with ThreadPoolExecutor()`
would block on shutdown until every straggler finished, defeating the timeout.)
"""

from __future__ import annotations

import contextvars
import logging
import threading
import time
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait
from contextlib import nullcontext

import monitoring
from config import settings
from ddg_scraper import scrape_ddg as _scrape_ddg
from flipkart_scraper import scrape_flipkart as _scrape_flipkart
from llm import LLMConfigError
from llm import recommend as _recommend
from llm import translate_query as _translate_query
from products import is_accessory, normalize_all, wants_accessory
from scraper import scrape as _scrape_amazon

log = logging.getLogger(__name__)

# Wrapped so AgentMonitor records every call (no-ops when monitoring is off).
translate_query = monitoring.tool(_translate_query, "translate_query")
scrape_amazon = monitoring.tool(_scrape_amazon, "scrape_amazon")
scrape_flipkart = monitoring.tool(_scrape_flipkart, "scrape_flipkart")
scrape_ddg = monitoring.tool(_scrape_ddg, "scrape_ddg")
recommend = monitoring.tool(_recommend, "recommend")

SOURCES = ("amazon", "flipkart", "web")

_pool: ThreadPoolExecutor | None = None
_pool_lock = threading.Lock()


def _get_pool() -> ThreadPoolExecutor:
    global _pool
    with _pool_lock:
        if _pool is None:
            _pool = ThreadPoolExecutor(max_workers=max(3, settings.scraper_workers), thread_name_prefix="scraper")
        return _pool


def shutdown() -> None:
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.shutdown(wait=False, cancel_futures=True)
            _pool = None


def scrape_all(query: str, timeout: float | None = None) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """Run every scraper in parallel.

    Returns ({source: products}, {source: "ok" | "empty" | "failed" | "timeout"}).
    """
    timeout = settings.scrape_timeout_seconds if timeout is None else timeout
    # Looked up at call time so tests can monkeypatch the module attributes.
    jobs = {"amazon": scrape_amazon, "flipkart": scrape_flipkart, "web": scrape_ddg}

    pool = _get_pool()
    futures = {}
    for site, fn in jobs.items():
        ctx = contextvars.copy_context()  # keep AgentMonitor session/turn in the worker
        futures[pool.submit(ctx.run, fn, query)] = site

    done, not_done = wait(futures.keys(), timeout=timeout, return_when=ALL_COMPLETED)

    results: dict[str, list[dict]] = {s: [] for s in SOURCES}
    status: dict[str, str] = {}

    for future in done:
        site = futures[future]
        try:
            data = future.result() or []
            # Web results carry the retailer name ("Croma", …) as their source.
            results[site] = normalize_all(data, None if site == "web" else site)
            status[site] = "ok" if results[site] else "empty"
            log.info("  ✓ %-8s → %d results", site, len(results[site]))
        except Exception as e:  # one broken source must not sink the search
            status[site] = "failed"
            log.exception("  ✗ %-8s scrape failed: %s", site, e)

    for future in not_done:
        site = futures[future]
        future.cancel()  # no-op if already running; it finishes in the background
        status[site] = "timeout"
        log.warning("  ⚠ %-8s scraper timed out after %ss", site, timeout)

    return results, status


def drop_accessories(results: dict[str, list[dict]], query: str) -> dict[str, list[dict]]:
    """Remove accessories from every source, unless that would leave nothing."""
    if wants_accessory(query):
        return results
    filtered = {site: [p for p in items if not is_accessory(p["title"])] for site, items in results.items()}
    return filtered if any(filtered.values()) else results


def _fallback_recommendation(products: list[dict]) -> dict:
    best = max(products, key=lambda p: (p.get("rating_value") or 0, p.get("reviews_value") or 0))
    return {"product": best, "reason": "Our AI is busy right now, so this is the highest-rated option we found."}


def run_search(user_input: str, mon=None) -> dict:
    """Execute the full pipeline. Raises EnvironmentError on LLM misconfiguration."""
    started = time.perf_counter()

    t0 = time.perf_counter()
    try:
        english_query = (translate_query(user_input) or "").strip()
    except LLMConfigError:
        raise
    except Exception as e:  # a flaky LLM shouldn't block searching with the raw text
        log.warning("Translation failed, searching with the original text: %s", e)
        english_query = ""
    english_query = english_query.splitlines()[0].strip()[:200] if english_query else user_input
    log.info("🌐 Translated '%s' → '%s' (%.0fms)", user_input, english_query, (time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    with mon.turn("scrape") if mon else nullcontext():
        results, status = scrape_all(english_query)
    results = drop_accessories(results, english_query)
    combined = [p for site in SOURCES for p in results[site]]
    log.info(
        "📦 Scrape done: amazon=%d flipkart=%d web=%d (%.0fms)",
        len(results["amazon"]), len(results["flipkart"]), len(results["web"]),
        (time.perf_counter() - t0) * 1000,
    )

    rec = None
    if combined:
        try:
            t0 = time.perf_counter()
            rec = recommend(english_query, combined)
            log.info("🤖 Recommendation ready (%.0fms)", (time.perf_counter() - t0) * 1000)
        except Exception as e:
            log.exception("✗ Recommendation failed: %s", e)
        if not rec or not rec.get("product"):
            rec = _fallback_recommendation(combined)

    log.info("✅ Search '%s' → %d products in %.0fms", english_query, len(combined), (time.perf_counter() - started) * 1000)
    return {
        "query": english_query,
        "results": results,
        "source_status": status,
        "recommendation": rec,
        "total": len(combined),
    }
