"""Shared FastAPI dependencies: settings, session, cache, auth, pagination."""

import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query, Request, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import Cache
from app.config import Settings
from app.db import Database
from app.errors import UnauthorizedError

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_settings(request: Request) -> Settings:
    """Settings come from the app that is handling this request, never from a module
    level cache - otherwise a test app built with different settings silently reads
    the real environment."""
    settings: Settings = request.app.state.settings
    return settings


def get_db(request: Request) -> Database:
    db: Database = request.app.state.db
    return db


def get_cache(request: Request) -> Cache:
    cache: Cache = request.app.state.cache
    return cache


async def get_session(
    db: Annotated[Database, Depends(get_db)],
) -> AsyncIterator[AsyncSession]:
    async for session in db.session():
        yield session


async def require_api_key(
    key: Annotated[str | None, Security(api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """Constant-time comparison against every configured key.

    `==` on secrets leaks length and prefix through timing. compare_digest does not.
    """
    if key and any(secrets.compare_digest(key, valid) for valid in settings.api_keys):
        return key
    raise UnauthorizedError("Missing or invalid X-API-Key header.")


@dataclass(frozen=True)
class Pagination:
    limit: int
    offset: int


def pagination(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


SessionDep = Annotated[AsyncSession, Depends(get_session)]
CacheDep = Annotated[Cache, Depends(get_cache)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
PageDep = Annotated[Pagination, Depends(pagination)]
