# syntax=docker/dockerfile:1
# AI Shopping Agent API — production image.
# Scrapers use curl_cffi (no browser), so no Chrome/Selenium layers are needed.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Optional AgentMonitor observability (installed from GitHub, needs git).
ARG INSTALL_MONITORING=false
COPY requirements-monitoring.txt .
RUN if [ "$INSTALL_MONITORING" = "true" ]; then \
        apt-get update && apt-get install -y --no-install-recommends git \
        && pip install -r requirements-monitoring.txt \
        && apt-get purge -y git && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*; \
    fi

COPY *.py ./

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV APP_ENV=production \
    WEB_CONCURRENCY=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
# --proxy-headers lets rate limiting see the real client IP behind a reverse proxy.
# Set FORWARDED_ALLOW_IPS to your proxy's address in production.
CMD ["sh", "-c", "exec uvicorn api:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY} --proxy-headers --forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-127.0.0.1} --no-access-log --no-server-header --timeout-keep-alive 75"]
