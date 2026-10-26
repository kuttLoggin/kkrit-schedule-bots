import json
import logging
import os
from datetime import datetime

from aiogram import Bot
from aiogram.types import FSInputFile
from aioredis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.infrastructure.database.functions.moderated_schedules import add_moderated_schedule, get_one_moderated_schedule, update_moderated_schedule
from app.infrastructure.database.models import ModeratedSchedule
from app.utils.cloud_api_yandex import get_public_resource
from app.utils.lock_factory import LockFactory
from app.utils.tools import download_file, text_, get_date_on_name

PATH_DATA = "data/schedule"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


async def send_moderate(bot: Bot, redis: Redis, resource_id: str):
    hulls = await redis.get("hulls")
    hulls = json.loads(hulls) if hulls else {}

    groups = await redis.get("groups")
    groups = json.loads(groups) if groups else {}


async def go_parsing_schedule(bot: Bot, session_pool: sessionmaker, redis: Redis):
    session: AsyncSession = session_pool()

    hulls = await redis.get("hulls")
    hulls = json.loads(hulls) if hulls else {}

    for hull_num, hull in hulls.items():
        resource = await get_public_resource(Config.KKRIT_DISK, hull["path"], "-created")
        for item in resource["_embedded"]["items"]:
            if item["type"] != "file":
                continue
            if item["mime_type"] != "application/pdf":
                continue
            if "расписание" not in item["name"].lower():
                continue

            date = get_date_on_name(item["name"])
            created = datetime.strptime(item["created"], DATE_FORMAT)
            modified = datetime.strptime(item["modified"], DATE_FORMAT)

            # Игнорирование документов, где нет даты в названии
            if date is None:
                continue

            record = await get_one_moderated_schedule(session, resource_id=item["resource_id"])
            if record and (record.verify is False or record.modified == modified):
                continue

            file_path = f"{PATH_DATA}/{item['name']}"
            os.makedirs(PATH_DATA, exist_ok=True)

            download_status = await download_file(item["file"], file_path)
            if download_status != 200:
                logging.warning(f"Schedule file not download! Status - {download_status}")
                continue

            schedule, converted_file_path = await schedule_pdf.go_parse_schedule(file_path)

            availability_schedule = bool(record)

            if not record:
                record = await add_moderated_schedule(
                    session,
                    item["name"], item["path"],
                    int(hull_num), item["resource_id"], schedule["groups"],
                    schedule["schedule"], schedule["numbers"],
                    date, created, modified
                )
            else:
                # Т.к. парсинг расписания долгий процесс (примерно на минуту), мы проверяем ещё раз отклонено ли расписание
                record = await get_one_moderated_schedule(session, resource_id=item["resource_id"])
                if record.verify is False:
                    os.remove(file_path)
                    os.remove(converted_file_path)
                    continue

                await update_moderated_schedule(
                    session,
                    ModeratedSchedule.resource_id == item["resource_id"],
                    groups=schedule["groups"],
                    tapes=schedule["schedule"], old_tapes=record.tapes,
                    modified=modified, date=date, name=item["name"]
                )

            await session.commit()

            exact_groups = await redis.get(f"exact_groups_on_hull:{hull_num}")
            exact_groups = json.loads(exact_groups) if exact_groups else None

            text = text_(
                f"🗞 <b>Новое расписание</b> [ID:<code>{record.id}</code>]"
                if not availability_schedule else
                f"🔎 <b>Изменение расписания</b> [ID:<code>{record.id}</code>]",
                f"✏ {item['name']}",
                f"📁 [<i>{hull_num}</i>] {hulls[hull_num]['name']}",
                f"🛡 <b>Проверка</b>:",
                f"👥 - Группы: "
            )

            msg_id = await redis.get(f"moderated_schedule:msg_id:{record.id}")

            msg = await bot.send_document(
                chat_id=Config.GROUP_ID,
                document=FSInputFile(converted_file_path),
                caption=text
            )
            await bot.send_document(
                chat_id=Config.GROUP_ID,
                document=FSInputFile(file_path),
                caption="🔼"
            )

            os.remove(file_path)
            os.remove(converted_file_path)

    await session.close()


async def parsing_schedule(bot: Bot, session_pool: sessionmaker, redis: Redis, lock_factory: LockFactory):
    if (
            lock := lock_factory.get_key("collect_data")
    ) and lock.locked():
        return

    async with lock_factory.get_lock("parsing_schedule"):
        await go_parsing_schedule(bot, session_pool, redis)
