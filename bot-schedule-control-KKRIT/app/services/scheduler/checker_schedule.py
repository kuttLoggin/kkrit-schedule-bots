import json

from aiogram import Bot
from aiogram.types import URLInputFile
from aioredis import Redis
from arrow import Arrow
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.infrastructure.database.functions.check_schedules import (
    get_one_check_schedule, add_check_schedule, update_check_schedule
)
from app.infrastructure.database.models import CheckSchedule
from app.keyboards.admin.inline import IgnoreFile, ConvertFilePDFToXLSX
from app.utils.cloud_api_yandex import get_public_resource
from app.utils.tools import text_, get_date_on_name

PATH_DATA = "data/check_schedule"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


async def checker_schedule(bot: Bot, session_pool: sessionmaker, redis: Redis):
    session: AsyncSession = session_pool()

    hulls = await redis.get("hulls")
    hulls = json.loads(hulls) if hulls else {}

    for hull_num, hull in hulls.items():
        resource = await get_public_resource(Config.KKRIT_DISK, hull["path"], "-created", 100)
        for item in resource["_embedded"]["items"]:
            if item["type"] != "file":
                continue
            if item["mime_type"] != "application/pdf":
                continue

            try:
                date = get_date_on_name(item["name"])
            except ValueError:
                continue

            created = Arrow.strptime(item["created"], DATE_FORMAT).shift(hours=+7).datetime
            modified = Arrow.strptime(item["modified"], DATE_FORMAT).shift(hours=+7).datetime

            # Игнорирование документов, где нет даты в названии
            if date is None:
                continue

            record = await get_one_check_schedule(session, resource_id=item["resource_id"])
            if record and (record.ignore is True or record.modified == modified):
                continue

            availability_schedule = record and record.modified != modified

            old_modified = record.modified if record else None

            if not record:
                record = await add_check_schedule(
                    session,
                    item["name"], item["path"],
                    int(hull_num), item["resource_id"],
                    date, created, modified
                )
            else:
                await update_check_schedule(
                    session,
                    CheckSchedule.resource_id == item["resource_id"],
                    modified=modified, date=date, name=item["name"]
                )

            await session.commit()

            text = text_(
                f"🗞 <b>Новое расписание</b> [ID <code>{record.id}</code>]"
                if not availability_schedule else
                f"🔎 <b>Изменение расписания</b> [ID <code>{record.id}</code>]",
                "",
                f"📁 {hulls[hull_num]['name']} [<code>{hull_num}</code>]",
                ""
                f"\n🔺 <b>Изменено</b>: {old_modified:%Y-%m-%d %H:%M:%S} –> {modified:%Y-%m-%d %H:%M:%S}"
                if old_modified else "",
                f"🔻 <b>Создано</b>: {created:%Y-%m-%d %H:%M:%S}"
            )

            reply_markup = (
                ConvertFilePDFToXLSX().get(record.id)
                if item["name"][-4:] == ".pdf" else
                IgnoreFile().get(record.id, False)
            )

            token = Bot.set_current(bot)
            await bot.send_document(
                chat_id=Config.GROUP_ID,
                document=URLInputFile(item["file"], item['name']),
                caption=text,
                reply_markup=reply_markup
            )
            Bot.reset_current(token)

    await session.close()
