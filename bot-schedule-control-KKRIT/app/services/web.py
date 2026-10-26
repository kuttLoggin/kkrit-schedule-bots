import json
import logging
from datetime import datetime
from typing import List

from aiohttp import web
from aiohttp.web_request import Request
from aioredis import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, AsyncResult
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.models import Schedule


async def get_schedule(request: Request):
    redis: Redis = request.app["redis"]

    power = await redis.get("power-schedule")
    if not int(power if isinstance(power, bytes) else None):
        return web.json_response([])

    session: AsyncSession = request["session"]

    hull = request.query.get("hull")
    date = request.query.get("date")
    limit = request.query.get("limit", 10)
    sort = request.query.get("sort", "asc")

    clauses = []
    if hull:
        clauses.append(Schedule.hull == hull)
    if date:
        try:
            query_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            pass
        else:
            clauses.append(Schedule.date >= query_date)
    if isinstance(limit, str):
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
        else:
            if limit > 15:
                limit = 15

    statement = select(
        Schedule
    ).where(
        *clauses
    ).order_by(
        Schedule.date.asc() if sort != "desc" else Schedule.date.desc()
    ).limit(limit)
    result: AsyncResult = await session.scalars(statement)
    result: List[Schedule] = result.unique().all()

    data = []
    for record in result:
        json_data = {
            "id": record.id,

            "name": record.name,
            # "path": record.path,

            "hull": record.hull,
            # "resource_id": record.resource_id,

            "tapes": record.tapes,
            "old_tapes": record.old_tapes,

            "date": record.date.isoformat(),
            "created": record.created.isoformat(),
            "modified": record.modified.isoformat()
        }
        data.append(json_data)

    return web.json_response(data)


async def get_groups(request: Request):
    redis: Redis = request.app["redis"]

    groups = await redis.get("groups")
    groups = json.loads(groups.decode()) if groups else {}

    return web.json_response(groups)


async def get_hulls(request: Request):
    redis: Redis = request.app["redis"]

    hulls = await redis.get("hulls")
    hulls = json.loads(hulls.decode()) if hulls else {}

    return web.json_response(hulls)


@web.middleware
async def middleware_session(request: Request, handler):
    session_pool: sessionmaker = request.app["session_pool"]
    session: AsyncSession = session_pool()

    request["session"] = session

    async with session:
        resp = await handler(request)

    return resp


async def start(ctx: dict, host: str = None):
    app = web.Application(middlewares=[middleware_session])

    for name, instance in ctx.items():
        app[name] = instance

    app.add_routes(
        [
            web.get("/schedules", get_schedule),
            web.get("/groups", get_groups),
            web.get("/hulls", get_hulls)
        ]
    )

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host, 80)
    await site.start()
