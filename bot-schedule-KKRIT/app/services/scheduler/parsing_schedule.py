import json
import logging
import os
import re
from contextlib import suppress
from datetime import datetime

from aioredis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.infrastructure.database.functions.schedules import add_schedule, get_one_schedule, update_schedule
from app.infrastructure.database.models import Schedule
from app.utils import schedule_pdf, schedule_excel
from app.utils.cloud_api_yandex import get_public_resource
from app.utils.lock_factory import LockFactory
from app.utils.tools import download_file

PATH_DATA = "data/schedule"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def get_date_on_name(item_name: str):
    text_date = re.search(r"(\d{1,2}\.\d{1,2}\.\d{4})", item_name)

    with suppress(AttributeError):
        return datetime.strptime(text_date.group(), "%d.%m.%Y").date()


async def go_parsing_schedule(session_pool: sessionmaker, redis: Redis):
    session: AsyncSession = session_pool()

    hulls = await redis.get("hulls")
    hulls = json.loads(hulls) if hulls else {}

    for hull_num, hull in hulls.items():
        resource = await get_public_resource(Config.KKRIT_DISK, hull["path"], "-created")
        for item in reversed(resource["_embedded"]["items"]):
            if item["type"] != "file":
                continue
            if item["mime_type"] not in ("application/pdf", "application/xlsx"):
                continue
            if "расписание" not in item["name"].lower():
                continue

            date = get_date_on_name(item["name"])
            created = datetime.strptime(item["created"], DATE_FORMAT)
            modified = datetime.strptime(item["modified"], DATE_FORMAT)

            # Игнорирование документов, где нет даты в названии
            if date is None:
                continue

            record = await get_one_schedule(session, resource_id=item["resource_id"])
            # 1 год, время при котором документ будет тупо пропускаться
            if record and (record.modified == modified or record.modified.year == 1):
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

            if not record:
                await add_schedule(
                    session,
                    item["name"], item["path"],
                    int(hull_num), item["resource_id"], schedule["schedule"],
                    schedule["numbers"], date, created, modified
                )
            else:
                if record.modified != modified:
                    await update_schedule(
                        session,
                        Schedule.hull == int(hull_num),
                        Schedule.resource_id == item["resource_id"],
                        tapes=schedule["schedule"], old_tapes=record.tapes,
                        modified=modified, date=date, name=item["name"]
                    )

            await session.commit()

    await session.close()


async def parsing_schedule(session_pool: sessionmaker, redis: Redis, lock_factory: LockFactory):
    if (
            lock := lock_factory.get_key("collect_data")
    ) and lock.locked():
        return

    async with lock_factory.get_lock("parsing_schedule"):
        await go_parsing_schedule(session_pool, redis)
