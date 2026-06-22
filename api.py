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

import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
from storage import save_session, load_sessions, load_last_session, load_session_by_id, check_db_connection

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
    query: str


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────
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


@app.post("/api/search", tags=["search"])
def search(request: SearchRequest):
    """
    Translate user query → parallel scrape Amazon + Flipkart + DDG
    → LLM recommendation → save session → return results.
    """
    user_input = request.query.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # 1. Translate query to English
    try:
        english_query = translate_query(user_input)
    except EnvironmentError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {e}")

    # 2. Parallel scrape with timeout
    amazon_results:   list[dict] = []
    flipkart_results: list[dict] = []
    ddg_results:      list[dict] = []

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(scrape_amazon,   english_query): "amazon",
            pool.submit(scrape_flipkart, english_query): "flipkart",
            pool.submit(scrape_ddg,      english_query): "web",
        }
        for future in as_completed(futures, timeout=_SCRAPE_TIMEOUT):
            site = futures[future]
            try:
                data = future.result(timeout=5)   # individual result timeout
                if site == "amazon":
                    amazon_results   = [dict(p, source="amazon")             for p in data]
                elif site == "flipkart":
                    flipkart_results = [dict(p, source="flipkart")           for p in data]
                else:
                    ddg_results      = [dict(p, source=p.get("source", "web")) for p in data]
                log.info("✓ %s: %d results", site, len(data))
            except FuturesTimeout:
                log.warning("⚠ %s scraper timed out after %ds", site, _SCRAPE_TIMEOUT)
            except Exception as e:
                log.error("✗ %s scrape failed: %s", site, e)

    combined = amazon_results + flipkart_results + ddg_results

    if not combined:
        return {
            "session_id":     None,
            "query":          english_query,
            "results":        {"amazon": [], "flipkart": [], "web": []},
            "recommendation": None,
            "message":        "No products found. Try a different query.",
        }

    # 3. LLM recommendation
    try:
        rec = recommend(english_query, combined)
    except Exception as e:
        log.error("Recommendation failed: %s", e)
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
    except Exception as e:
        log.error("Failed to save session: %s", e)

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
