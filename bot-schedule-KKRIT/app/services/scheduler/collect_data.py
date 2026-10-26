import json
import logging
import os
from datetime import datetime, timedelta

from aioredis import Redis

from app.config import Config
from app.services.scheduler.parsing_schedule import get_date_on_name
from app.utils import schedule_pdf, schedule_excel
from app.utils.cloud_api_yandex import get_public_resource
from app.utils.lock_factory import LockFactory
from app.utils.tools import download_file

PATH_DATA = "data/collect_data"


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
            if item["mime_type"] not in ("application/pdf", "application/xlsx"):
                continue
            if "расписание" not in item["name"].lower():
                continue

            created = datetime.strptime(item["created"], "%Y-%m-%dT%H:%M:%S+00:00")

            # TODO: Для будущего, это условие под сомнением
            if created.date() <= (datetime.now() - timedelta(days=30)).date():
                del hulls[num]
                break

            # Игнорирование документов, где нет даты в названии
            if get_date_on_name(item["name"]) is None:
                continue

            file_path = f"{PATH_DATA}/{item['name']}"

            download_status = await download_file(item["file"], file_path)
            if download_status != 200:
                logging.warning(f"Schedule file not download! Status - {download_status}")
                continue

            if item["mime_type"] == "application/pdf":
                schedule, converted_file_path = await schedule_pdf.go_parse_schedule(file_path)
                os.remove(file_path)
                os.remove(converted_file_path)
            else:
                schedule = schedule_excel.parse_schedule(file_path)
                os.remove(file_path)

            groups[num] = schedule["groups"]
            break

        if not groups.get(num):
            del hulls[num]

    return groups, hulls


async def collect_all_data(redis: Redis, lock_factory: LockFactory):
    async with lock_factory.get_lock("collect_data"):
        change: bytes = await redis.get("collect_all_data_last_time_change")
        change = change.decode() if change else None
        if change == f"{datetime.now():%d.%m}":
            return

        hulls = await collect_hulls()
        groups, hulls = await collect_groups(hulls)

        await redis.set("hulls", json.dumps(hulls))
        await redis.set("groups", json.dumps(groups))

        await redis.set("collect_all_data_last_time_change", f"{datetime.now():%d.%m}")

    logging.info("Collect hulls and groups")
