from datetime import datetime, date as _date
from typing import List

from sqlalchemy import select, update, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, AsyncResult

from ...database.models import Schedule


async def add_schedule(
        session: AsyncSession,
        name: str,
        path: str,
        hull: int,
        resource_id: str,
        tapes: dict,
        numbers: list,
        date: _date,
        created: datetime,
        modified: datetime,
        **kwargs
) -> Schedule:
    insert_stmt = select(
        Schedule
    ).from_statement(
        insert(
            Schedule
        ).values(
            name=name,
            path=path,
            hull=hull,
            resource_id=resource_id,
            tapes=tapes,
            numbers=numbers,
            date=date,
            created=created,
            modified=modified,
            **kwargs
        ).returning(Schedule).on_conflict_do_nothing()
    )
    result = await session.scalars(insert_stmt)
    return result.first()


async def get_one_schedule(session: AsyncSession, **kwargs) -> Schedule:
    statement = select(Schedule).filter_by(**kwargs)
    result: AsyncResult = await session.scalars(statement)
    return result.first()


async def get_some_schedules(session: AsyncSession, *clauses) -> List[Schedule]:
    statement = select(
        Schedule
    ).where(
        *clauses
    ).order_by(
        Schedule.created.asc()
    )
    result: AsyncResult = await session.scalars(statement)
    return result.unique().all()


async def get_pagination_schedules(session: AsyncSession, offset: int, limit: int, *clauses) -> List[Schedule]:
    statement = select(
        Schedule
    ).where(
        *clauses
    ).order_by(
        Schedule.created_at.asc()
    ).offset(offset).limit(limit)
    result: AsyncResult = await session.scalars(statement)
    return result.unique().all()


async def get_count_schedules(session: AsyncSession, *clauses) -> int:
    statement = select(
        func.count(Schedule.id)
    ).where(
        *clauses
    )
    result: AsyncResult = await session.scalar(statement)
    return result


async def update_schedule(session: AsyncSession, *clauses, **values):
    statement = update(
        Schedule
    ).where(
        *clauses
    ).values(
        **values
    )
    await session.execute(statement)


async def delete_schedule(session: AsyncSession, *clauses):
    statement = delete(
        Schedule
    ).where(
        *clauses
    )
    await session.execute(statement)
