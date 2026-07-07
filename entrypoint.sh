#!/bin/sh
# entrypoint.sh — Detect the installed Chrome version at container startup
# and export it so scraper.py uses the correct ChromeDriver version.
#
# /etc/environment is NOT sourced by CMD-launched processes, so we detect
# the version here and pass it via the environment directly.

set -e

if [ -z "${CHROME_VERSION}" ]; then
    DETECTED=$(google-chrome --version 2>/dev/null | grep -oP '\d+' | head -1 || true)
    if [ -n "${DETECTED}" ]; then
        export CHROME_VERSION="${DETECTED}"
        echo "[entrypoint] Chrome ${DETECTED} detected — CHROME_VERSION exported"
    else
        echo "[entrypoint] Warning: could not detect Chrome version — scraper will auto-detect at runtime"
    fi
fi

# Hand off to the main process (CMD from Dockerfile).
exec "$@"
