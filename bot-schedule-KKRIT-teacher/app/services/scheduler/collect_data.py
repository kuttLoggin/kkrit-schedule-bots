import json
import logging
from datetime import datetime, timedelta

from aioredis import Redis

from app.config import Config
from app.utils.cloud_api_yandex import get_public_resource, get_schedule


async def collect_hulls():
    resource = await get_public_resource(Config.KKRIT_DISK, sort="created")
    hulls = {}
    for i, item in enumerate(resource["_embedded"]["items"], start=1):
        if item["type"] != "dir":
            continue

        hull = {"name": item["name"], "path": item["path"]}
        hulls[i] = hull

    return hulls


async def collect_groups(hulls: dict):
    groups = {}
    for num, hull in hulls.copy().items():
        data = await get_public_resource(Config.KKRIT_DISK, hull["path"], "-created")
        items = data["_embedded"]["items"]

        if not items:
            del hulls[num]
            continue

        for item in items:
            if item["type"] != "file":
                continue
            if item["mime_type"] != "application/pdf":
                continue
            if "расписание" not in item["name"].lower():
                continue

            created = datetime.strptime(item["created"], "%Y-%m-%dT%H:%M:%S+00:00")

            if created <= datetime.now() - timedelta(days=30):
                del hulls[num]
                break

            schedule, _ = await get_schedule(item["name"], item["file"])

            groups[num] = [group for group, _ in schedule.items()]

            break

        if not groups.get(num):
            del hulls[num]

    return groups, hulls


async def collect_all_data(redis: Redis):
    hulls = await collect_hulls()
    groups, hulls = await collect_groups(hulls)

    await redis.set("hulls", json.dumps(hulls))
    await redis.set("groups", json.dumps(groups))

    logging.info("Collect hulls and groups")
