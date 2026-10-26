import json
from typing import Callable, AsyncContextManager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from ...database.models.base import DatabaseModel


async def create_session_pool(sqlalchemy_url: str, echo=False) -> Callable[[], AsyncContextManager[AsyncSession]]:
    engine = create_async_engine(
        sqlalchemy_url,
        query_cache_size=1200,
        pool_size=10,
        max_overflow=200,
        future=True,
        echo=echo,
        json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False)
    )

    async with engine.begin() as conn:
        await conn.run_sync(DatabaseModel.metadata.create_all)

    session_pool = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    return session_pool
