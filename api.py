import asyncio
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


from scraper import scrape as scrape_amazon
from flipkart_scraper import scrape_flipkart
from ddg_scraper import scrape_ddg
from llm import translate_query, recommend
from storage import save_session, load_sessions, load_last_session, load_session_by_id, check_db_connection, init_db


_raw_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
if not _raw_origins or _raw_origins == "*":
    _ALLOWED_ORIGINS = ["*"]
    _ALLOW_CREDENTIALS = False
else:
    _ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]
    _ALLOW_CREDENTIALS = True

_SCRAPE_TIMEOUT = int(os.getenv("SCRAPE_TIMEOUT_SECONDS", "60"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI Shopping Agent API",
    version="1.0.0",
    description="Personal AI Shopping Agent — searches Amazon, Flipkart, and the web.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)



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



class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=256)



@app.get("/health", tags=["ops"])
def health():
    db_ok = check_db_connection()
    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "db": "connected" if db_ok else "unreachable",
        "version": "1.0.0",
    }


@app.post("/api/search", tags=["search"])
async def search(request: SearchRequest):
    user_input = request.query.strip()
    loop = asyncio.get_running_loop()

    try:
        english_query = await loop.run_in_executor(None, translate_query, user_input)
    except EnvironmentError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        err_str = str(e)
        log.error(f"Translation failed: {err_str}")
        if "401 UNAUTHENTICATED" in err_str or "API_KEY_INVALID" in err_str or "invalid authentication" in err_str.lower():
            safe_msg = "Invalid or expired AI API Key configured."
        else:
            safe_msg = "AI processing service is temporarily unavailable."
        raise HTTPException(status_code=500, detail=safe_msg)

    amazon_results:   list[dict] = []
    flipkart_results: list[dict] = []
    ddg_results:      list[dict] = []

    def _run_scrapers():
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures_map = {
                pool.submit(scrape_amazon,   english_query): "amazon",
                pool.submit(scrape_flipkart, english_query): "flipkart",
                pool.submit(scrape_ddg,      english_query): "web",
            }

            done, not_done = wait(futures_map.keys(), timeout=_SCRAPE_TIMEOUT, return_when=ALL_COMPLETED)

            results_local = {"amazon": [], "flipkart": [], "web": []}

            for future in done:
                site = futures_map[future]
                try:
                    data = future.result()
                    if site == "amazon":
                        results_local["amazon"]   = [dict(p, source="amazon")             for p in data]
                    elif site == "flipkart":
                        results_local["flipkart"] = [dict(p, source="flipkart")           for p in data]
                    else:
                        results_local["web"]      = [dict(p, source=p.get("source", "web")) for p in data]
                    log.info("✓ %s: %d results", site, len(data))
                except Exception as e:
                    log.error("✗ %s scrape failed: %s", site, e)

            for future in not_done:
                future.cancel()
                log.warning("⚠ %s scraper timed out after %ds — future cancelled", futures_map[future], _SCRAPE_TIMEOUT)

            return results_local

    scraped = await loop.run_in_executor(None, _run_scrapers)
    amazon_results   = scraped["amazon"]
    flipkart_results = scraped["flipkart"]
    ddg_results      = scraped["web"]

    combined = amazon_results + flipkart_results + ddg_results

    if not combined:
        return {
            "session_id":     None,
            "query":          english_query,
            "results":        {"amazon": [], "flipkart": [], "web": []},
            "recommendation": None,
            "message":        "No products found. Try a different query.",
        }

    try:
        rec = await loop.run_in_executor(None, recommend, english_query, combined)
    except Exception as e:
        log.error("Recommendation failed: %s", e)
        rec = {"product": combined[0], "reason": "AI unavailable — showing first result."}

    session_id = None
    try:
        session_id = await loop.run_in_executor(
            None,
            lambda: save_session(
                query_original=user_input,
                query_english=english_query,
                amazon_results=amazon_results,
                flipkart_results=flipkart_results,
                ddg_results=ddg_results,
                recommendation=rec,
            ),
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
    try:
        return load_sessions()
    except Exception as e:
        log.error("Failed to load sessions: %s", e)
        raise HTTPException(status_code=500, detail="Could not load sessions")


@app.get("/api/sessions/last", tags=["sessions"])
def get_last_session():
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



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
