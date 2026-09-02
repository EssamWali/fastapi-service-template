"""Liveness and readiness.

They are different questions. Liveness asks "is this process wedged, restart me?".
Readiness asks "can I serve traffic right now?" - which depends on the database and
the cache. Conflating them makes a brief database blip restart every replica.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.cache import Cache
from app.config import Settings
from app.db import Database
from app.deps import get_cache, get_db, get_settings

router = APIRouter(tags=["ops"])


@router.get("/healthz", summary="Liveness - is the process up")
async def healthz(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str]:
    return {"status": "ok", "env": settings.env}


@router.get("/readyz", summary="Readiness - can it serve traffic")
async def readyz(
    response: Response,
    db: Annotated[Database, Depends(get_db)],
    cache: Annotated[Cache, Depends(get_cache)],
) -> dict[str, object]:
    checks = {"database": await db.ping(), "cache": await cache.ping()}
    ready = all(checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"ready": ready, "checks": checks}
