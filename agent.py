"""
agent.py — Main orchestrator for the Personal AI Shopping Agent.

Flow: user input → translate → parallel scrape (Amazon + Flipkart + DDG) →
      merge → LLM recommendation → display → save session.

Run: python agent.py
"""

import logging
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("undetected_chromedriver").setLevel(logging.WARNING)

from scraper          import scrape             as scrape_amazon
from flipkart_scraper import scrape_flipkart
from ddg_scraper      import scrape_ddg
from llm              import translate_query, recommend
from storage          import save_session


def _print_banner() -> None:
    print("\n" + "=" * 70)
    print("  🛒  Personal AI Shopping Agent")
    print("     Type your request in any language (Punjabi / Hindi / English)")
    print("     Type 'quit' or 'exit' to stop")
    print("=" * 70 + "\n")


def _print_results_table(products: list[dict]) -> None:
    if not products:
        print("  (no products found)\n")
        return

    print(f"\n{'─'*70}")
    print(f"  {'#':<3} {'SOURCE':<10} {'PRICE':<12} {'RATING':<22} TITLE")
    print(f"{'─'*70}")
    for i, p in enumerate(products, 1):
        src    = p.get("source", "?").upper()[:8]
        price  = p.get("price", "N/A")[:10]
        rating = p.get("rating", "N/A")[:20]
        title  = p.get("title", "N/A")[:45] + ("…" if len(p.get("title", "")) > 45 else "")
        print(f"  {i:<3} {src:<10} {price:<12} {rating:<22} {title}")
    print(f"{'─'*70}\n")


def _print_recommendation(rec: dict, query_original: str) -> None:
    product = rec.get("product")
    reason  = rec.get("reason", "N/A")

    print("╔" + "═" * 68 + "╗")
    print("║  🏆  AI RECOMMENDATION                                            ║")
    print("╠" + "═" * 68 + "╣")

    if product:
        source  = product.get("source", "?").upper()
        title   = product.get("title", "N/A")
        price   = product.get("price", "N/A")
        rating  = product.get("rating", "N/A")
        reviews = product.get("reviews_count", "N/A")
        url     = product.get("url", "N/A")

        def _wrap(line, width=66):
            words, cur, lines = line.split(), "", []
            for w in words:
                if len(cur) + len(w) + 1 > width:
                    lines.append(cur)
                    cur = w
                else:
                    cur = (cur + " " + w).strip()
            if cur:
                lines.append(cur)
            return lines

        print(f"║  Platform : {source:<55}║")
        for ln in _wrap(title):
            print(f"║  {ln:<66}║")
        print(f"║  Price    : {price:<55}║")
        print(f"║  Rating   : {rating:<55}║")
        print(f"║  Reviews  : {reviews:<55}║")
        print("╠" + "═" * 68 + "╣")
        print("║  Why this product?                                               ║")
        for ln in _wrap(reason):
            print(f"║  {ln:<66}║")
        print("╚" + "═" * 68 + "╝")
        print(f"\n  🔗 Link: {url}\n")
    else:
        print("║  Could not determine a recommendation.                           ║")
        print("╚" + "═" * 68 + "╝\n")


def run_search(user_input: str) -> None:
    print(f"\n🔍 Translating your request…")
    try:
        english_query = translate_query(user_input)
    except EnvironmentError as e:
        print(f"\n❌ {e}\n")
        return

    print(f"   Search query: \"{english_query}\"\n")

    print("⏳ Searching Amazon, Flipkart, and the web (DuckDuckGo) in parallel…")
    amazon_results:   list[dict] = []
    flipkart_results: list[dict] = []
    ddg_results:      list[dict] = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(scrape_amazon,   english_query): "amazon",
            pool.submit(scrape_flipkart, english_query): "flipkart",
            pool.submit(scrape_ddg,      english_query): "web (DDG)",
        }
        for future in as_completed(futures):
            site = futures[future]
            try:
                data = future.result()
                if site == "amazon":
                    amazon_results   = [dict(p, source="amazon")                  for p in data]
                elif site == "flipkart":
                    flipkart_results = [dict(p, source="flipkart")                for p in data]
                else:
                    ddg_results      = [dict(p, source=p.get("source", "web"))    for p in data]
                print(f"   ✓ {site.capitalize()}: {len(data)} results found")
            except Exception as e:
                log.error("%s scrape failed: %s", site, e)

    combined = amazon_results + flipkart_results + ddg_results

    if not combined:
        print("\n⚠  No products found on any site. Try a different query.\n")
        return

    print(f"\n📋 All results ({len(combined)} products across Amazon, Flipkart, and the web):")
    _print_results_table(combined)

    print("🤖 Asking AI to pick the best option…\n")
    try:
        rec = recommend(english_query, combined)
    except Exception as e:
        log.error("Recommendation failed: %s", e)
        rec = {"product": combined[0], "reason": "AI unavailable — showing first result."}

    _print_recommendation(rec, user_input)

    try:
        session_id = save_session(
            query_original   = user_input,
            query_english    = english_query,
            amazon_results   = amazon_results,
            flipkart_results = flipkart_results,
            ddg_results      = ddg_results,
            recommendation   = rec,
        )
        print(f"💾 Session saved (ID: {session_id[:8]}…)\n")
    except Exception as e:
        log.warning("Could not save session: %s", e)


def main() -> None:
    _print_banner()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye! 👋\n")
            break

        if not user_input:
            continue

        if user_input.lower() in {"quit", "exit", "bye", "q"}:
            print("\nGoodbye! 👋\n")
            break

        run_search(user_input)


if __name__ == "__main__":
    main()
