"""Application factory, lifespan, and the middleware every request passes through."""

import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from app.cache import build_cache
from app.config import Settings, get_settings
from app.db import Database
from app.errors import install_error_handlers
from app.logging import configure_logging, request_id_var
from app.routers import health, items

log = logging.getLogger("app.access")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Connections are opened once at startup, not per request, and closed on the
    way out. Anything created here belongs on app.state."""
    settings: Settings = app.state.settings
    app.state.db = Database(settings)
    app.state.cache = build_cache(settings)
    logging.getLogger("app").info("service.start", extra={"env": settings.env})
    try:
        yield
    finally:
        await app.state.cache.close()
        await app.state.db.dispose()
        logging.getLogger("app").info("service.stop")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="fastapi-service-template",
        version="0.1.0",
        summary="Async FastAPI service with Postgres, Redis, API-key auth and migrations.",
        lifespan=lifespan,
        docs_url=None if settings.is_prod else "/docs",
        redoc_url=None,
    )
    app.state.settings = settings

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Attach a correlation id and emit one structured access line per request."""
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        log.info(
            "http.request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "request_id": request_id,
            },
        )
        return response

    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(items.router)
    return app


app = create_app()
