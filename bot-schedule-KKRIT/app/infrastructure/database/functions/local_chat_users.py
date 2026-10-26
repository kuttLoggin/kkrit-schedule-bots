from typing import List

from sqlalchemy import select, update, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, AsyncResult

from .. import models
from ...database.models import LocalChatUser


async def add_local_chat_user(session: AsyncSession, chat_id: int, user_id: int, **kwargs) -> LocalChatUser:
    insert_stmt = select(
        LocalChatUser
    ).from_statement(
        insert(
            LocalChatUser
        ).values(
            chat_id=chat_id,
            user_id=user_id,
            **kwargs
        ).returning(LocalChatUser).on_conflict_do_nothing()
    )
    result = await session.scalars(insert_stmt)
    return result.first()


async def create_local_chat_user(session: AsyncSession, chat_db: models.Chat, user_db: models.User):
    return await add_local_chat_user(
        session,
        chat_db.id, user_db.id
    )


async def get_one_local_chat_user(session: AsyncSession, **kwargs) -> LocalChatUser:
    statement = select(LocalChatUser).filter_by(**kwargs)
    result: AsyncResult = await session.scalars(statement)
    return result.first()


async def get_some_local_chat_users(session: AsyncSession, *clauses) -> List[LocalChatUser]:
    statement = select(
        LocalChatUser
    ).where(
        *clauses
    ).order_by(
        LocalChatUser.created_at.desc()
    )
    result: AsyncResult = await session.scalars(statement)
    return result.unique().all()


async def get_count_local_chat_users(session: AsyncSession, *clauses) -> int:
    statement = select(
        func.count(LocalChatUser.id)
    ).where(
        *clauses
    )
    result: AsyncResult = await session.scalar(statement)
    return result


async def update_local_chat_user(session: AsyncSession, *clauses, **values):
    statement = update(
        LocalChatUser
    ).where(
        *clauses
    ).values(
        **values
    )
    await session.execute(statement)


async def delete_local_chat_user(session: AsyncSession, *clauses):
    statement = delete(
        LocalChatUser
    ).where(
        *clauses
    )
    await session.execute(statement)
