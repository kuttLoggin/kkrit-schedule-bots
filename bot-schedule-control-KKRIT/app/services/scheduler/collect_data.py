import json
import logging
import os
from datetime import datetime

from aiogram import Bot
from aiogram.types import Document
from aioredis import Redis
from arrow import Arrow

from app.config import Config
from app.utils.tools import get_date_on_name
from app.utils.parser_schedule import schedule_pdf_v1  # , schedule_pdf_v2
from app.utils.cloud_api_yandex import get_public_resource
from app.utils.lock_factory import LockFactory
from app.utils.tools import download_file


PATH_DATA = "data/collect_data"


async def collect_hulls():
    resource = await get_public_resource(Config.KKRIT_DISK, sort="created")
    hulls = {}
    for i, item in enumerate(resource["_embedded"]["items"]):
        if item["type"] != "dir":
            continue

        hull = {"name": item["name"], "path": item["path"]}
        hulls[i] = hull

    return hulls


async def collect_groups_on_file(bot: Bot, file: Document, parser_version: str):
    path = f"data/{file.file_name}"
    await bot.download(file, path)

    if parser_version.startswith("v2"):
        return await schedule_pdf_v1.go_parse_schedule(path)
    # elif parser_version.startswith("v1"):
    #     return await schedule_pdf_v2.go_parse_schedule(path)
    else:
        raise Exception(f"Unknown parser version: {parser_version}")


async def collect_groups(hulls: dict):
    groups = {}
    for num, hull in hulls.copy().items():
        data = await get_public_resource(Config.KKRIT_DISK, hull["path"], "-created", limit=5)
        items = data["_embedded"]["items"]

        if not items:
            del hulls[num]
            continue

        for item in items:
            if item["type"] != "file":
                continue
            if item["mime_type"] != "application/pdf":
                continue
            # if "расписание" not in item["name"].lower():
            #     continue

            # created = datetime.strptime(item["created"], "%Y-%m-%dT%H:%M:%S+00:00")

            # Если файлу больше полу года, то лучше его пропустить
            # if created.date() <= (datetime.now() - timedelta(days=180)).date():
            #     continue

            # Игнорирование документов, где нет даты в названии
            if get_date_on_name(item["name"]) is None:
                continue

            file_path = f"{PATH_DATA}/{item['name']}"
            os.makedirs(PATH_DATA, exist_ok=True)

            download_status = await download_file(item["file"], file_path)
            if download_status != 200:
                logging.warning(f"Schedule file not download! Status - {download_status}")
                continue

            schedule, converted_file_path = await schedule_pdf_v1.go_parse_schedule(file_path)
            os.remove(file_path)
            os.remove(converted_file_path)

            groups[num] = schedule["groups"]
            break

        if not groups.get(num):
            del hulls[num]

    return groups, hulls


async def collect_all_data(redis: Redis, lock_factory: LockFactory, type_update_data: str):
    async with lock_factory.get_lock("collect_data"):
        if type_update_data == "once":
            if await redis.get("groups") and await redis.get("hulls"):
                return
        elif type_update_data == "forcibly":
            ...
        else:
            return

        logging.info("Collect hulls and groups...")

        last_time_change: bytes = await redis.get("collect_all_data:last_time_change")
        last_time_change = last_time_change.decode() if last_time_change else None

        last_time_change = datetime.fromisoformat(last_time_change) if last_time_change else datetime.utcnow()
        last_time_change_humanize = Arrow.fromdatetime(last_time_change).humanize()

        hulls = await collect_hulls()
        groups, hulls = await collect_groups(hulls)

        await redis.set("groups", json.dumps(groups))
        await redis.set("hulls", json.dumps(hulls))

        await redis.set("collect_all_data:last_time_change", datetime.utcnow().isoformat())

        logging.info(f"Update hulls and groups, last change: {last_time_change_humanize}")
        logging.info(f"hulls: {hulls}")
        logging.info(f"groups: {groups}")
