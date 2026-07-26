"""
api.py — Production-ready FastAPI backend for the AI Shopping Agent.

Features:
  - /health endpoint for Docker health checks
  - Request-ID tracing via X-Request-ID header
  - Configurable CORS via ALLOWED_ORIGINS env var
  - 60-second timeout on parallel scraping
  - Structured JSON logging in production
  - Full session CRUD endpoints
"""

import contextvars
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Imports (after logging is configured)
# ──────────────────────────────────────────────────────────────────────────────
from scraper import scrape as scrape_amazon
from flipkart_scraper import scrape_flipkart
from ddg_scraper import scrape_ddg
from llm import translate_query, recommend
from storage import save_session, load_sessions, load_last_session, load_session_by_id, check_db_connection, init_db
from chat_agent import process_chat
from guardrails import mask_credit_card

import monitoring

# Wrap agent tools so AgentMonitor records every call — arguments, results,
# latency, and errors. These are no-ops when monitoring is disabled.
translate_query = monitoring.tool(translate_query, "translate_query")
scrape_amazon   = monitoring.tool(scrape_amazon,   "scrape_amazon")
scrape_flipkart = monitoring.tool(scrape_flipkart, "scrape_flipkart")
scrape_ddg      = monitoring.tool(scrape_ddg,      "scrape_ddg")
recommend       = monitoring.tool(recommend,       "recommend")

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")
]
_SCRAPE_TIMEOUT = int(os.getenv("SCRAPE_TIMEOUT_SECONDS", "60"))

# ──────────────────────────────────────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Shopping Agent API",
    version="1.0.0",
    description="Personal AI Shopping Agent — searches Amazon, Flipkart, and the web.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────────
# Request-ID middleware
# ──────────────────────────────────────────────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()
    response: Response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
    log.info(
        "%s %s → %d  (%.1fms)  [%s]",
        request.method, request.url.path, response.status_code,
        duration_ms, request_id[:8],
    )
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=200)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    history: list[ChatMessage] = Field(..., max_length=50)


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    init_db()
    monitoring.start_dashboard()
    log.info("Pre-warming Chrome driver to prevent first-request timeout...")
    try:
        from scraper import _build_driver
        driver = _build_driver()
        driver.quit()
        log.info("Chrome driver pre-warmed successfully.")
    except Exception as e:
        log.warning("Failed to pre-warm Chrome driver: %s", e)


@app.get("/health", tags=["ops"])
def health():
    """Docker/k8s health probe — verifies API and DB are alive."""
    db_ok = check_db_connection()
    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "db": "connected" if db_ok else "unreachable",
        "version": "1.0.0",
    }


@app.post("/api/chat", tags=["chat"])
def chat(request: ChatRequest):
    """
    Conversational onboarding endpoint for the AI Shopping Agent.
    Masks PII/Credit Cards before processing.
    """
    history_dict = []
    for msg in request.history:
        # 1. Guardrail: Mask Credit Card details in the message
        safe_content = mask_credit_card(msg.content)
        history_dict.append({"role": msg.role, "content": safe_content})
        
    try:
        response_data = process_chat(history_dict)
        return response_data
    except Exception as e:
        log.exception("Chat processing failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search", tags=["search"])
def search(request: SearchRequest):
    """
    Translate user query → parallel scrape Amazon + Flipkart + DDG
    → LLM recommendation → save session → return results.
    """
    user_input = request.query.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    search_start = time.perf_counter()
    log.info("🔍 Search request: '%s'", user_input)

    # Open a monitored session so AgentMonitor records this whole run.
    mon_ctx = monitoring.session(query=user_input)
    mon = mon_ctx.__enter__()
    try:
        mon.log_user_message(user_input)

        # 1. Translate query to English
        try:
            t0 = time.perf_counter()
            english_query = translate_query(user_input)
            log.info(
                "🌐 Translated query: '%s' → '%s'  (%.0fms)",
                user_input, english_query, (time.perf_counter() - t0) * 1000,
            )
            log.info("🌐 Translated query: '%s' → '%s'", user_input, english_query)
        except EnvironmentError as e:
            log.error("✗ Translation failed (config): %s", e)
            raise HTTPException(status_code=503, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            log.exception("✗ Translation failed: %s", e)
            raise HTTPException(status_code=500, detail=f"Translation failed: {e}")

        # 2. Parallel scrape with timeout
        amazon_results:   list[dict] = []
        flipkart_results: list[dict] = []
        ddg_results:      list[dict] = []

        log.info("🛒 Scraping Amazon + Flipkart + Web for '%s' …", english_query)
        scrape_start = time.perf_counter()
        with mon.turn("scrape"), ThreadPoolExecutor(max_workers=3) as pool:
            # Copy the current context per thread so scraper tool-calls are
            # recorded under this session/turn (contextvars don't cross threads).
            futures_map = {}
            for _fn, _site in (
                (scrape_amazon,   "amazon"),
                (scrape_flipkart, "flipkart"),
                (scrape_ddg,      "web"),
            ):
                _ctx = contextvars.copy_context()
                futures_map[pool.submit(_ctx.run, _fn, english_query)] = _site

            done, not_done = wait(futures_map.keys(), timeout=_SCRAPE_TIMEOUT, return_when=ALL_COMPLETED)

            for future in done:
                site = futures_map[future]
                try:
                    data = future.result()
                    if site == "amazon":
                        amazon_results   = [dict(p, source="amazon")             for p in data]
                    elif site == "flipkart":
                        flipkart_results = [dict(p, source="flipkart")           for p in data]
                    else:
                        ddg_results      = [dict(p, source=p.get("source", "web")) for p in data]
                    log.info("  ✓ %-8s → %d results", site, len(data))
                except Exception as e:
                    log.exception("  ✗ %-8s scrape failed: %s", site, e)

            for future in not_done:
                site = futures_map[future]
                log.warning("  ⚠ %-8s scraper timed out after %ds", site, _SCRAPE_TIMEOUT)

        combined = amazon_results + flipkart_results + ddg_results
        
        # Filter out accessories if the query doesn't ask for them
        accessory_keywords = ["bag", "case", "cover", "sleeve", "backpack", "charger", "adapter", "stand", "skin", "cable"]
        q_lower = english_query.lower()
        wants_accessory = any(k in q_lower for k in accessory_keywords)
        
        if not wants_accessory:
            filtered_combined = []
            for p in combined:
                title_lower = p.get("title", "").lower()
                is_accessory = any(k in title_lower for k in accessory_keywords)
                if not is_accessory:
                    filtered_combined.append(p)
            
            # Reassign only if filtering didn't remove everything (safety fallback)
            if len(filtered_combined) > 0:
                combined = filtered_combined
                # Rebuild source lists if needed, though they aren't strictly used after this except for logging/saving
                amazon_results = [p for p in amazon_results if not any(k in p.get("title", "").lower() for k in accessory_keywords)]
                flipkart_results = [p for p in flipkart_results if not any(k in p.get("title", "").lower() for k in accessory_keywords)]
                ddg_results = [p for p in ddg_results if not any(k in p.get("title", "").lower() for k in accessory_keywords)]

        log.info(
            "📦 Scrape complete for '%s': amazon=%d flipkart=%d web=%d (total=%d)  (%.0fms)",
            english_query, len(amazon_results), len(flipkart_results),
            len(ddg_results), len(combined), (time.perf_counter() - scrape_start) * 1000,
        )

        if not combined:
            log.warning("🚫 No products found for '%s' — returning empty result", english_query)
            mon.log_response("No products found.", query=english_query, products=0)
            return {
                "session_id":     None,
                "query":          english_query,
                "results":        {"amazon": [], "flipkart": [], "web": []},
                "recommendation": None,
                "message":        "No products found. Try a different query.",
            }

        # 3. LLM recommendation
        try:
            t0 = time.perf_counter()
            rec = recommend(english_query, combined)
            _rp = (rec or {}).get("product") or {}
            log.info(
                "🤖 Recommendation: [%s] %s — %s  (%.0fms)",
                _rp.get("source", "?"),
                (_rp.get("title") or "N/A")[:80],
                (rec or {}).get("reason", "")[:120],
                (time.perf_counter() - t0) * 1000,
            )
        except Exception as e:
            log.exception("✗ Recommendation failed for '%s': %s", english_query, e)
            rec = {"product": combined[0], "reason": "AI unavailable — showing first result."}

        # 4. Persist session
        session_id = None
        try:
            session_id = save_session(
                query_original=user_input,
                query_english=english_query,
                amazon_results=amazon_results,
                flipkart_results=flipkart_results,
                ddg_results=ddg_results,
                recommendation=rec,
            )
            log.info("💾 Saved session %s", session_id)
        except Exception as e:
            log.exception("✗ Failed to save session for '%s': %s", english_query, e)

        _rp = (rec or {}).get("product") or {}
        mon.log_response(
            f"Recommended [{_rp.get('source', '?')}] "
            f"{(_rp.get('title') or 'N/A')[:80]} — {(rec or {}).get('reason', '')[:200]}",
            query=english_query, products=len(combined), session_id=session_id,
        )
        log.info(
            "✅ Search done: '%s' → %d products, session=%s  (total %.0fms)",
            english_query, len(combined), session_id,
            (time.perf_counter() - search_start) * 1000,
        )
        return {
            "session_id": session_id,
            "query":      english_query,
            "results": {
                "amazon":   amazon_results,
                "flipkart": flipkart_results,
                "web":      ddg_results,
            },
            "recommendation": rec,
        }
    finally:
        mon_ctx.__exit__(None, None, None)


@app.get("/api/sessions", tags=["sessions"])
def get_sessions():
    """Return all saved search sessions, newest first."""
    try:
        return load_sessions()
    except Exception as e:
        log.error("Failed to load sessions: %s", e)
        raise HTTPException(status_code=500, detail="Could not load sessions")


@app.get("/api/sessions/last", tags=["sessions"])
def get_last_session():
    """Return the most recent search session."""
    try:
        session = load_last_session()
        if not session:
            raise HTTPException(status_code=404, detail="No sessions found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        log.error("Failed to load last session: %s", e)
        raise HTTPException(status_code=500, detail="Could not load session")


@app.get("/api/sessions/{session_id}", tags=["sessions"])
def get_session(session_id: str):
    """Return a specific session by ID."""
    try:
        session = load_session_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        return session
    except HTTPException:
        raise
    except Exception as e:
        log.error("Failed to load session %s: %s", session_id, e)
        raise HTTPException(status_code=500, detail="Could not load session")


# ──────────────────────────────────────────────────────────────────────────────
# Dev entry point
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
