"""Data access, kept out of the routers.

Routers translate HTTP; repositories translate SQL. Neither knows about the other's
vocabulary, which is what makes both of them testable on their own.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError
from app.models import Item
from app.schemas import ItemCreate, ItemUpdate


class ItemRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payload: ItemCreate) -> Item:
        item = Item(name=payload.name, description=payload.description)
        self.session.add(item)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError(
                "An item with that name already exists.", name=payload.name
            ) from exc
        # created_at / updated_at are filled in by the database, so the in-memory
        # object does not have them until we read them back.
        await self.session.refresh(item)
        return item

    async def get(self, item_id: uuid.UUID) -> Item:
        item = await self.session.get(Item, item_id)
        if item is None:
            raise NotFoundError("Item not found.", item_id=str(item_id))
        return item

    async def list(self, limit: int, offset: int, q: str | None = None) -> tuple[list[Item], int]:
        stmt = select(Item)
        count_stmt = select(func.count()).select_from(Item)
        if q:
            pattern = f"%{q}%"
            stmt = stmt.where(Item.name.ilike(pattern))
            count_stmt = count_stmt.where(Item.name.ilike(pattern))

        total = (await self.session.execute(count_stmt)).scalar_one()
        rows = await self.session.execute(
            stmt.order_by(Item.created_at.desc()).limit(limit).offset(offset)
        )
        return list(rows.scalars().all()), int(total)

    async def update(self, item_id: uuid.UUID, payload: ItemUpdate) -> Item:
        item = await self.get(item_id)
        data = payload.model_dump(exclude_unset=True)
        for field, value in data.items():
            setattr(item, field, value)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictError("An item with that name already exists.") from exc
        await self.session.refresh(item)
        return item

    async def delete(self, item_id: uuid.UUID) -> None:
        item = await self.get(item_id)
        await self.session.delete(item)
        await self.session.flush()
