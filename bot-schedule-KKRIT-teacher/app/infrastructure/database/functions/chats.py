from typing import List, Optional

from aiogram import types
from sqlalchemy import select, update, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, AsyncResult

from ...database.models import Chat


async def add_chat(session: AsyncSession, tg_id: int, title: str, username: str = None, group_type: str = "supergroup", **kwargs) -> Chat:
    insert_stmt = select(
        Chat
    ).from_statement(
        insert(
            Chat
        ).values(
            tg_id=tg_id,
            title=title,
            username=username,
            group_type=group_type,
            **kwargs
        ).returning(Chat).on_conflict_do_nothing()
    )
    result = await session.scalars(insert_stmt)
    return result.first()


async def create_chat(session: AsyncSession, chat: types.Chat, owner_id: Optional[int] = None):
    return await add_chat(
        session,
        chat.id, chat.title, chat.username, chat.type,
        owner=owner_id
    )


async def get_one_chat(session: AsyncSession, **kwargs) -> Chat:
    statement = select(Chat).filter_by(**kwargs)
    result: AsyncResult = await session.scalars(statement)
    return result.first()


async def get_some_chats(session: AsyncSession, *clauses) -> List[Chat]:
    statement = select(
        Chat
    ).where(
        *clauses
    ).order_by(
        Chat.created_at.desc()
    )
    result: AsyncResult = await session.scalars(statement)
    return result.unique().all()


async def get_count_chats(session: AsyncSession, *clauses) -> int:
    statement = select(
        func.count(Chat.id)
    ).where(
        *clauses
    )
    result: AsyncResult = await session.scalar(statement)
    return result


async def update_chat(session: AsyncSession, *clauses, **values):
    statement = update(
        Chat
    ).where(
        *clauses
    ).values(
        **values
    )
    await session.execute(statement)


async def delete_chat(session: AsyncSession, *clauses):
    statement = delete(
        Chat
    ).where(
        *clauses
    )
    await session.execute(statement)
