"""Items CRUD - the worked example. Delete it and keep the shape."""

import uuid

from fastapi import APIRouter, Depends, Query, status

from app.deps import CacheDep, PageDep, SessionDep, SettingsDep, require_api_key
from app.repository import ItemRepository
from app.schemas import ItemCreate, ItemOut, ItemUpdate, Page

router = APIRouter(
    prefix="/items",
    tags=["items"],
    dependencies=[Depends(require_api_key)],
)


def _cache_key(item_id: uuid.UUID) -> str:
    return f"item:{item_id}"


@router.post("", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
async def create_item(payload: ItemCreate, session: SessionDep) -> ItemOut:
    item = await ItemRepository(session).create(payload)
    return ItemOut.model_validate(item)


@router.get("", response_model=Page[ItemOut])
async def list_items(
    session: SessionDep,
    page: PageDep,
    q: str | None = Query(default=None, description="Case-insensitive name filter"),
) -> Page[ItemOut]:
    items, total = await ItemRepository(session).list(page.limit, page.offset, q)
    return Page[ItemOut](
        items=[ItemOut.model_validate(i) for i in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{item_id}", response_model=ItemOut)
async def get_item(
    item_id: uuid.UUID,
    session: SessionDep,
    cache: CacheDep,
    settings: SettingsDep,
) -> ItemOut:
    if cached := await cache.get(_cache_key(item_id)):
        return ItemOut.model_validate_json(cached)

    item = ItemOut.model_validate(await ItemRepository(session).get(item_id))
    await cache.set(_cache_key(item_id), item.model_dump_json(), settings.cache_ttl_seconds)
    return item


@router.patch("/{item_id}", response_model=ItemOut)
async def update_item(
    item_id: uuid.UUID,
    payload: ItemUpdate,
    session: SessionDep,
    cache: CacheDep,
) -> ItemOut:
    item = await ItemRepository(session).update(item_id, payload)
    # Invalidate rather than rewrite: the write path should not have to know the
    # shape of every cached representation.
    await cache.delete(_cache_key(item_id))
    return ItemOut.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: uuid.UUID, session: SessionDep, cache: CacheDep) -> None:
    await ItemRepository(session).delete(item_id)
    await cache.delete(_cache_key(item_id))
