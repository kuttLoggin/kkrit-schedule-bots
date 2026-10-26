from typing import List

from sqlalchemy import select, update, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, AsyncResult

from ...database.models import ChatSchedule


async def add_chat_schedule(
        session: AsyncSession,
        tg_id: int,
        chat_type: str,
        hull: str,
        group: str,
        **kwargs
) -> ChatSchedule:
    insert_stmt = select(
        ChatSchedule
    ).from_statement(
        insert(
            ChatSchedule
        ).values(
            tg_id=tg_id,
            chat_type=chat_type,
            hull=hull,
            group=group,
            **kwargs
        ).returning(ChatSchedule)
    )
    result = await session.scalars(insert_stmt)
    return result.first()


async def get_one_chat_schedule(session: AsyncSession, **kwargs) -> ChatSchedule:
    statement = select(ChatSchedule).filter_by(**kwargs)
    result: AsyncResult = await session.scalars(statement)
    return result.first()


async def get_some_chat_schedules(session: AsyncSession, *clauses) -> List[ChatSchedule]:
    statement = select(
        ChatSchedule
    ).where(
        *clauses
    ).order_by(
        ChatSchedule.created_at.desc()
    )
    result: AsyncResult = await session.scalars(statement)
    return result.unique().all()


async def get_pagination_chat_schedules(session: AsyncSession, offset: int, limit: int, *clauses) -> List[ChatSchedule]:
    statement = select(
        ChatSchedule
    ).where(
        *clauses
    ).order_by(
        ChatSchedule.created_at.asc()
    ).offset(offset).limit(limit)
    result: AsyncResult = await session.scalars(statement)
    return result.unique().all()


async def get_count_chat_schedules(session: AsyncSession, *clauses) -> int:
    statement = select(
        func.count(ChatSchedule.id)
    ).where(
        *clauses
    )
    result: AsyncResult = await session.scalar(statement)
    return result


async def update_chat_schedule(session: AsyncSession, *clauses, **values):
    statement = update(
        ChatSchedule
    ).where(
        *clauses
    ).values(
        **values
    )
    await session.execute(statement)


async def delete_chat_schedule(session: AsyncSession, *clauses):
    statement = delete(
        ChatSchedule
    ).where(
        *clauses
    )
    await session.execute(statement)
