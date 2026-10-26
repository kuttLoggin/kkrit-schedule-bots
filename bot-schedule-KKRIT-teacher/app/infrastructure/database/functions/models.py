from typing import List

from sqlalchemy import select, update, delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, AsyncResult


async def add_model(session: AsyncSession, model, **kwargs):
    insert_stmt = select(
        model
    ).from_statement(
        insert(
            model
        ).values(
            **kwargs
        ).returning(model).on_conflict_do_nothing()
    )
    result = await session.scalars(insert_stmt)
    return result.first()


async def get_one_model(session: AsyncSession, model, **kwargs):
    statement = select(model).filter_by(**kwargs)
    result: AsyncResult = await session.scalars(statement)
    return result.first()


async def get_some_models(session: AsyncSession, model, *clauses) -> List:
    statement = select(
        model
    ).where(
        *clauses
    ).order_by(
        model.created_at.desc()
    )
    result: AsyncResult = await session.scalars(statement)
    return result.unique().all()


async def get_pagination_models(session: AsyncSession, model, offset: int, limit: int, *clauses):
    statement = select(
        model
    ).where(
        *clauses
    ).order_by(
        model.id.asc()
    ).offset(offset).limit(limit)
    result: AsyncResult = await session.scalars(statement)
    return result.unique().all()


async def get_count_models(session: AsyncSession, model, *clauses) -> int:
    statement = select(
        func.count(model.id)
    ).where(
        *clauses
    )
    result: AsyncResult = await session.scalar(statement)
    return result


async def update_model(session: AsyncSession, model, *clauses, **values):
    statement = update(
        model
    ).where(
        *clauses
    ).values(
        **values
    )
    await session.execute(statement)


async def delete_model(session: AsyncSession, model, *clauses):
    statement = delete(
        model
    ).where(
        *clauses
    )
    await session.execute(statement)
