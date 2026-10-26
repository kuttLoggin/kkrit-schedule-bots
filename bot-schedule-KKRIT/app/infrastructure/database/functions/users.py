from typing import List

from aiogram import types
from sqlalchemy import select, update, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, AsyncResult

from ...database.models import User


async def add_user(
        session: AsyncSession, tg_id: int, first_name: str = None, last_name: str = None, username: str = None,
        **kwargs
) -> User:
    insert_stmt = select(
        User
    ).from_statement(
        insert(
            User
        ).values(
            tg_id=tg_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            **kwargs
        ).returning(User).on_conflict_do_nothing()
    )
    result = await session.scalars(insert_stmt)
    return result.first()


async def create_user(session: AsyncSession, user: types.User, chat_type: str):
    return await add_user(
        session,
        user.id, user.first_name, user.last_name, user.username,
        active=True if chat_type == "private" else False
    )


async def get_one_user(session: AsyncSession, **kwargs) -> User:
    statement = select(User).filter_by(**kwargs)
    result: AsyncResult = await session.scalars(statement)
    return result.first()


async def get_some_users(session: AsyncSession, *clauses) -> List[User]:
    statement = select(
        User
    ).where(
        *clauses
    ).order_by(
        User.created_at.desc()
    )
    result: AsyncResult = await session.scalars(statement)
    return result.unique().all()


async def get_count_users(session: AsyncSession, *clauses) -> int:
    statement = select(
        func.count(User.tg_id)
    ).where(
        *clauses
    )
    result: AsyncResult = await session.scalar(statement)
    return result


async def update_user(session: AsyncSession, *clauses, **values):
    statement = update(
        User
    ).where(
        *clauses
    ).values(
        **values
    )
    await session.execute(statement)


async def delete_user(session: AsyncSession, *clauses):
    statement = delete(
        User
    ).where(
        *clauses
    )
    await session.execute(statement)
