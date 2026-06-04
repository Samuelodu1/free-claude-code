"""
Claude Code Proxy - Entry Point

Minimal entry point that builds the ASGI app via :func:`api.app.create_app`.
Run with: uv run uvicorn server:app --host 0.0.0.0 --port 8082 --timeout-graceful-shutdown 5
"""

from api.app import create_app, create_asgi_app

app = create_asgi_app()

__all__ = ["app", "create_app"]

if __name__ == "__main__":
    import uvicorn

    from cli.process_registry import kill_all_best_effort
    from config.settings import get_settings

    settings = get_settings()
    try:
        # timeout_graceful_shutdown ensures uvicorn doesn't hang on task cleanup.
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level="debug",
            timeout_graceful_shutdown=5,
        )
    finally:
        # Safety net: cleanup subprocesses if lifespan shutdown doesn't fully run.
        kill_all_best_effort()

import secrets
import os
from fastapi import Request
from fastapi.responses import Response

@app.middleware("http")
async def basic_auth(request: Request, call_next):
    # Skip auth for the API routes used by Claude Code itself
    if request.url.path.startswith("/v1/"):
        auth = request.headers.get("authorization", "")
        token = os.getenv("ANTHROPIC_AUTH_TOKEN", "freecc")
        if auth == f"Bearer {token}":
            return await call_next(request)
        return Response("Unauthorized", status_code=401)
    
    # Basic auth for /admin and everything else
    auth = request.headers.get("authorization", "")
    correct_user = os.getenv("ADMIN_USER", "admin")
    correct_pass = os.getenv("ADMIN_PASS", "changeme")
    import base64
    try:
        scheme, credentials = auth.split(" ", 1)
        decoded = base64.b64decode(credentials).decode("utf-8")
        username, password = decoded.split(":", 1)
        if scheme.lower() == "basic" and secrets.compare_digest(username, correct_user) and secrets.compare_digest(password, correct_pass):
            return await call_next(request)
    except Exception:
        pass
    return Response(
        "Unauthorized",
        status_code=401,
        headers={"WWW-Authenticate": 'Basic realm="Admin"'}
    )
