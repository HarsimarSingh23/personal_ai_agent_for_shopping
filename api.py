"""
api.py — FastAPI backend for the AI Shopping Agent.

    POST   /api/chat                  conversational onboarding
    POST   /api/search                translate → scrape → recommend → save
    GET    /api/sessions              this device's history (paginated)
    GET    /api/sessions/last         most recent search
    GET    /api/sessions/{id}         one search with full results
    DELETE /api/sessions/{id}         delete one search
    DELETE /api/sessions              clear this device's history
    GET    /health                    liveness + DB/LLM status (503 if DB down)

Production features: optional API-key auth (X-API-Key), per-IP rate limits,
per-device history (X-Client-ID), request-ID tracing, JSON logs, security
headers, and errors that never leak internals. Configuration: see config.py.
"""

import hmac
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import settings
from middleware import RateLimiter, client_ip, configure_logging, request_id_var

configure_logging(settings.log_level, settings.log_format)
log = logging.getLogger("api")

import monitoring  # noqa: E402  (imported after logging is configured)
import pipeline  # noqa: E402
from chat_agent import process_chat  # noqa: E402
from guardrails import mask_credit_card  # noqa: E402
from llm import LLMConfigError, llm_status  # noqa: E402
from storage import (  # noqa: E402
    check_db_connection,
    delete_session,
    delete_sessions_for_client,
    init_db,
    load_last_session,
    load_session_by_id,
    load_sessions,
    save_session,
)

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

limiter = RateLimiter()


# ──────────────────────────────────────────────────────────────────────────────
# Lifespan
# ──────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    monitoring.start_dashboard()
    if settings.is_production and "*" in settings.allowed_origins:
        log.warning("ALLOWED_ORIGINS is '*' in production — restrict it to your web app's origin.")
    if settings.is_production and not settings.api_key:
        log.warning("API_KEY is not set in production — the API is open to anyone who can reach it.")
    if llm_status() != "configured":
        log.warning("LLM provider not ready: %s", llm_status())
    log.info("AI Shopping Agent API %s started (env=%s)", settings.app_version, settings.app_env)
    yield
    pipeline.shutdown()


app = FastAPI(
    title="AI Shopping Agent API",
    version=settings.app_version,
    description="Personal AI Shopping Agent — searches Amazon, Flipkart, and the web.",
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

_wildcard = "*" in settings.allowed_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _wildcard else settings.allowed_origins,
    allow_credentials=not _wildcard,  # credentials + "*" is rejected by browsers
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-API-Key", "X-Client-ID", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Response-Time-Ms", "Retry-After"],
    max_age=600,
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    incoming = request.headers.get("X-Request-ID", "")
    request_id = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    try:
        response: Response = await call_next(request)
    except Exception:
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        response = JSONResponse(
            status_code=500,
            content={"detail": "Something went wrong on our side. Please try again.", "request_id": request_id},
        )
    finally:
        request_id_var.reset(token)

    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    log.info(
        "%s %s → %d (%.0fms) [%s]",
        request.method, request.url.path, response.status_code, duration_ms, request_id[:8],
    )
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Dependencies
# ──────────────────────────────────────────────────────────────────────────────
def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.api_key and not hmac.compare_digest(x_api_key or "", settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


def get_client_id(x_client_id: str | None = Header(default=None)) -> str | None:
    if x_client_id is None or x_client_id == "":
        return None
    if not _CLIENT_ID_RE.match(x_client_id):
        raise HTTPException(status_code=400, detail="Invalid X-Client-ID header.")
    return x_client_id


def rate_limited(bucket: str, setting: str):
    def _check(request: Request) -> None:
        retry_after = limiter.hit(f"{bucket}:{client_ip(request)}", getattr(settings, setting))
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail="You're going a bit fast. Please wait a moment and try again.",
                headers={"Retry-After": str(int(retry_after) + 1)},
            )
    return Depends(_check)


def _valid_session_id(session_id: str) -> str:
    try:
        return str(uuid.UUID(session_id))
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found.")


# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=200)


class ChatMessage(BaseModel):
    role: Literal["user", "agent", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    history: list[ChatMessage] = Field(..., min_length=1, max_length=100)


class ChatResponse(BaseModel):
    message: str
    is_ready_to_search: bool
    search_query: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# Ops
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["ops"])
def health(response: Response):
    """Docker/k8s probe. Returns 503 when the database is unreachable."""
    db_ok = check_db_connection()
    if not db_ok:
        response.status_code = 503
    return {
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "unreachable",
        "llm": llm_status(),
        "version": settings.app_version,
    }


# ──────────────────────────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────────────────────────
api = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


@api.post(
    "/chat",
    tags=["chat"],
    response_model=ChatResponse,
    dependencies=[rate_limited("chat", "rate_limit_chat_per_min")],
)
def chat(request: ChatRequest):
    """Conversational onboarding. Card numbers are masked before the LLM sees them."""
    history = [
        {
            "role": "user" if m.role == "user" else "agent",
            "content": mask_credit_card(m.content.strip())[: settings.max_message_chars],
        }
        for m in request.history[-settings.max_chat_messages:]
    ]
    try:
        return process_chat(history)
    except LLMConfigError:
        log.error("Chat unavailable: LLM provider is not configured.")
        raise HTTPException(status_code=503, detail="The AI assistant is not available right now.")


@api.post(
    "/search",
    tags=["search"],
    dependencies=[rate_limited("search", "rate_limit_search_per_min")],
)
def search(request: SearchRequest, client_id: str | None = Depends(get_client_id)):
    """Translate → parallel scrape Amazon + Flipkart + web → LLM pick → save."""
    user_input = mask_credit_card(request.query.strip())
    if len(user_input) < 2:
        raise HTTPException(status_code=422, detail="Please describe what you want to buy.")

    with monitoring.session(query=user_input) as mon:
        mon.log_user_message(user_input)
        try:
            out = pipeline.run_search(user_input, mon)
        except LLMConfigError:
            log.error("Search unavailable: LLM provider is not configured.")
            raise HTTPException(status_code=503, detail="The AI assistant is not available right now.")

        results, rec = out["results"], out["recommendation"]
        base = {
            "query": out["query"],
            "results": results,
            "source_status": out["source_status"],
            "recommendation": rec,
        }

        if out["total"] == 0:
            mon.log_response("No products found.", query=out["query"], products=0)
            return {**base, "session_id": None, "message": "No products found. Try different keywords."}

        session_id = None
        try:
            session_id = save_session(
                query_original=user_input,
                query_english=out["query"],
                amazon_results=results["amazon"],
                flipkart_results=results["flipkart"],
                ddg_results=results["web"],
                recommendation=rec,
                client_id=client_id,
            )
        except Exception as e:  # the user still gets results if the DB hiccups
            log.exception("Failed to save session: %s", e)

        pick = (rec or {}).get("product") or {}
        mon.log_response(
            f"Recommended [{pick.get('source', '?')}] {(pick.get('title') or 'N/A')[:80]}",
            query=out["query"], products=out["total"], session_id=session_id,
        )
        return {**base, "session_id": session_id}


@api.get(
    "/sessions",
    tags=["sessions"],
    dependencies=[rate_limited("read", "rate_limit_read_per_min")],
)
def get_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    summary: bool = Query(False, description="Omit full product lists (much smaller payload)."),
    client_id: str | None = Depends(get_client_id),
):
    """This device's saved searches, newest first."""
    return load_sessions(limit=limit, offset=offset, client_id=client_id, summary=summary)


@api.get(
    "/sessions/last",
    tags=["sessions"],
    dependencies=[rate_limited("read", "rate_limit_read_per_min")],
)
def get_last_session(client_id: str | None = Depends(get_client_id)):
    session = load_last_session(client_id=client_id)
    if not session:
        raise HTTPException(status_code=404, detail="No sessions found.")
    return session


@api.get(
    "/sessions/{session_id}",
    tags=["sessions"],
    dependencies=[rate_limited("read", "rate_limit_read_per_min")],
)
def get_session(session_id: str, client_id: str | None = Depends(get_client_id)):
    session = load_session_by_id(_valid_session_id(session_id), client_id=client_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@api.delete(
    "/sessions/{session_id}",
    tags=["sessions"],
    status_code=204,
    dependencies=[rate_limited("read", "rate_limit_read_per_min")],
)
def remove_session(session_id: str, client_id: str | None = Depends(get_client_id)):
    if not delete_session(_valid_session_id(session_id), client_id=client_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    return Response(status_code=204)


@api.delete(
    "/sessions",
    tags=["sessions"],
    dependencies=[rate_limited("read", "rate_limit_read_per_min")],
)
def clear_sessions(client_id: str | None = Depends(get_client_id)):
    if not client_id:
        raise HTTPException(status_code=400, detail="X-Client-ID header is required.")
    return {"deleted": delete_sessions_for_client(client_id)}


app.include_router(api)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=not settings.is_production)
