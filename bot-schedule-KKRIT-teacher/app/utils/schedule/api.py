from typing import List, Dict, Any

import aiohttp
from yarl import URL

LINK = URL("http://schedule-control-KKRIT-bot")


async def _send_request(url: str, params: dict):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as request:
            return await request.json()


async def get_schedules(
        hull: str = None,
        date: str = None,
        limit: int = None,
        sort: str = None
) -> List[Dict[str, Any]]:
    """ Расписания """

    params = {key: str(value) for key, value in locals().items() if value is not None}

    return await _send_request(LINK / "schedules", params)


async def get_groups() -> List[str]:
    """ Группы """

    params = {}

    return await _send_request(LINK / "groups", params)


async def get_hulls() -> Dict[str, Dict[str, str]]:
    """ Корпуса """

    params = {}

    return await _send_request(LINK / "hulls", params)

