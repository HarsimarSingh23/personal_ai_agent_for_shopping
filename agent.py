"""
agent.py — Main orchestrator for the Personal AI Shopping Agent.

Flow: user input → translate → parallel scrape (Amazon + Flipkart + DDG) →
      merge → LLM recommendation → display → save session.

Run: python agent.py
"""

import logging
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

logging.getLogger("urllib3").setLevel(logging.WARNING)

import pipeline
from llm     import LLMConfigError
from storage import init_db, save_session


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
    print("\n🔍 Translating your request and searching Amazon, Flipkart and the web…")
    try:
        out = pipeline.run_search(user_input)
    except LLMConfigError as e:
        print(f"\n❌ {e}\n")
        return

    print(f"   Search query: \"{out['query']}\"")
    for site, state in out["source_status"].items():
        print(f"   {'✓' if state == 'ok' else '⚠'} {site.capitalize()}: {len(out['results'][site])} results ({state})")

    results = out["results"]
    combined = results["amazon"] + results["flipkart"] + results["web"]
    if not combined:
        print("\n⚠  No products found on any site. Try a different query.\n")
        return

    print(f"\n📋 All results ({len(combined)} products across Amazon, Flipkart, and the web):")
    _print_results_table(combined)
    _print_recommendation(out["recommendation"] or {}, user_input)

    try:
        session_id = save_session(
            query_original   = user_input,
            query_english    = out["query"],
            amazon_results   = results["amazon"],
            flipkart_results = results["flipkart"],
            ddg_results      = results["web"],
            recommendation   = out["recommendation"],
        )
        print(f"💾 Session saved (ID: {session_id[:8]}…)\n")
    except Exception as e:
        log.warning("Could not save session: %s", e)


def main() -> None:
    init_db()
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
