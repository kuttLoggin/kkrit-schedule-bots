import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, html
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aioredis import Redis
from arrow import Arrow
from sqlalchemy import true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.infrastructure.database.functions.chat_schedules import get_some_chat_schedules, get_count_chat_schedules, \
    update_chat_schedule
from app.infrastructure.database.functions.chats import get_one_chat
from app.infrastructure.database.functions.users import get_one_user
from app.infrastructure.database.models import ChatSchedule
from app.keyboards.private.inline import ScheduleUrl
from app.services.fluent import FluentService
from app.utils.cloud_api_yandex import get_schedule, get_public_resource, get_teacher_schedule
from app.utils.tools import natural_future_day


async def pin_message_in_chat(
        bot: Bot,
        tg_id: int,
        chat_schedule: ChatSchedule,
        session: AsyncSession,
        msg_pin_id: int,
        schedule_edit: bool,
        resource_id: str,
        schedule_date: datetime
):
    pin_msgs = chat_schedule.pin_msgs or {}

    for pin_msg_id, data in pin_msgs.copy().items():
        if (
                Arrow.strptime(data["date"], "%Y-%m-%d").date() <= Arrow.now().shift(days=-1).date()
        ) or schedule_edit and resource_id == data["resource_id"]:
            del pin_msgs[pin_msg_id]

            try:
                await bot.unpin_chat_message(tg_id, int(pin_msg_id))
            except TelegramAPIError as err:
                logging.warning(f"Failed unpin schedule {tg_id} - {err}")
            else:
                await asyncio.sleep(0.035)

    if schedule_date.date() >= Arrow.now().date():
        try:
            await bot.pin_chat_message(tg_id, msg_pin_id)
        except TelegramAPIError as err:
            logging.warning(f"Failed pin schedule {tg_id} - {err}")
        else:
            pin_msgs[str(msg_pin_id)] = {"date": f"{schedule_date:%Y-%m-%d}", "resource_id": resource_id}

            await asyncio.sleep(0.035)

    await update_chat_schedule(
        session,
        ChatSchedule.id == chat_schedule.id,
        pin_msgs=pin_msgs
    )

    await session.commit()


async def get_item_schedule(resource: dict, chat_schedule_id: int, redis: Redis):
    for item in reversed(resource["_embedded"]["items"]):
        if item["type"] != "file":
            continue
        if item["mime_type"] != "application/pdf":
            continue
        if "расписание" not in item["name"].lower():
            continue

        natural_day = get_natural_day_schedule(item["name"])
        if natural_day[1] is None:
            continue

        if (
                natural_day[1]
                or
                Arrow.strptime(item["created"], "%Y-%m-%dT%H:%M:%S+00:00")
        ).date() <= Arrow.now().shift(days=-1).date():
            continue

        modified_schedule: bytes = await redis.get(f"modified_schedule-{chat_schedule_id}-{item['resource_id']}")
        modified_schedule = modified_schedule.decode() if modified_schedule else None

        if modified_schedule != item["modified"]:
            return item, modified_schedule

    return None, None


def get_natural_day_schedule(item_name: str):
    schedule_date = None
    date = "не определено"
    for date_item in item_name.split(".pdf")[0].split()[::-1]:
        try:
            schedule_date = datetime.strptime(date_item, "%d.%m.%Y")
            date = natural_future_day(schedule_date)
        except ValueError:
            continue
        break

    return date, schedule_date


def get_text_tapes(teacher_schedule: list, chat_schedule_groups: Optional[list]):
    text_tapes = []
    for tape_num, tape_group, tape_name in teacher_schedule:
        num = tape_num if str(tape_num) != "nan" else ">"
        group = f"<b>{tape_group}</b>" if (
                tape_group not in (chat_schedule_groups or [])
        ) else f"<u><b>{tape_group}</b></u>"
        tape = html.quote(tape_name or "—")

        string = f"<b>{num}</b> – [{group}] {tape}"
        text_tapes.append(string)

    return "\n".join(text_tapes)


async def find_schedule(bot: Bot, session_pool: sessionmaker, redis: Redis, fluent: FluentService):
    session: AsyncSession = session_pool()

    hulls = await redis.get("hulls")
    if not hulls:
        await session.close()
        return
    hulls = json.loads(hulls)

    for hull_num, hull in hulls.items():
        count_chat_schedules = await get_count_chat_schedules(
            session,
            ChatSchedule.hull == hull["name"],
            ChatSchedule.active == true()
        )
        if not count_chat_schedules:
            continue

        resource = await get_public_resource(Config.KKRIT_DISK, hull["path"], "-created", 6)

        chat_schedules = await get_some_chat_schedules(
            session,
            ChatSchedule.hull == hull["name"],
            ChatSchedule.active == true()
        )

        success = {}
        fails = {}

        schedules = {}
        for chat_schedule in chat_schedules:
            item, modified_schedule = await get_item_schedule(resource, chat_schedule.id, redis)
            if not item:
                continue

            await redis.set(
                f"modified_schedule-{chat_schedule.id}-{item['resource_id']}",
                item["modified"],
                ex=timedelta(days=7)
            )

            if schedule_the := schedules.get(item["resource_id"]):
                date = schedule_the["date"]
                schedule_date = schedule_the["schedule_date"]

                schedule = schedule_the["schedule"]
                numbers = schedule_the["numbers"]

                reply_markup = schedule_the["reply_markup"]
            else:
                date, schedule_date = get_natural_day_schedule(item["name"])

                schedule, numbers = await get_schedule(item["name"], item["file"])

                reply_markup = ScheduleUrl().get(
                    text=" ".join(item["name"].replace(".pdf", "").split()[3:]) or "Расписание",
                    url=f"{Config.KKRIT_DISK}{item['path']}".replace(" ", "%20")
                )

                schedules[item["resource_id"]] = {
                    "date": date,
                    "schedule_date": schedule_date,
                    "schedule": schedule,
                    "numbers": numbers,
                    "reply_markup": reply_markup
                }

            teacher_schedule = get_teacher_schedule(schedule, numbers, chat_schedule.name, chat_schedule.groups)

            old_teacher_schedule = await redis.get(f"teacher_schedule-{chat_schedule.id}-{item['resource_id']}")
            old_teacher_schedule = json.loads(old_teacher_schedule) if old_teacher_schedule else None

            global_schedule_edit = False
            if modified_schedule and modified_schedule != item["modified"]:
                global_schedule_edit = True

            global_teacher_schedule = get_teacher_schedule(
                schedules[item["resource_id"]]["schedule"], numbers, chat_schedule.name, chat_schedule.groups
            )

            schedule_edit = old_teacher_schedule != global_teacher_schedule if (
                    global_schedule_edit and old_teacher_schedule is not None
            ) else False

            if not schedule_edit and global_schedule_edit:
                continue

            await redis.set(
                f"teacher_schedule-{chat_schedule.id}-{item['resource_id']}",
                json.dumps(teacher_schedule),
                ex=timedelta(days=7)
            )

            tape_availability = True if teacher_schedule else False
            text_tapes = get_text_tapes(teacher_schedule, chat_schedule.groups) or "None"

            tg_id = chat_schedule.tg_id
            chat_type = chat_schedule.chat_type

            if chat_schedule.chat_type == "user":
                model = await get_one_user(session, tg_id=tg_id)
                lang = model.real_language
            else:
                model = await get_one_chat(session, tg_id=tg_id)
                lang = model.language

            i18n = fluent.get_translator_by_locale(lang or "ru")

            text = i18n.schedule(
                date=date,
                tapes=text_tapes,
                edit=int(schedule_edit),
                bot_username=(await bot.me()).username
            )

            try:
                msg = await bot.send_message(tg_id, text, reply_markup=reply_markup, disable_web_page_preview=True)
                if chat_schedule.pin_msg_func and tape_availability:
                    await pin_message_in_chat(
                        bot,
                        tg_id,
                        chat_schedule,
                        session,
                        msg.message_id,
                        schedule_edit,
                        item["resource_id"],
                        schedule_date
                    )
            except TelegramForbiddenError:
                await update_chat_schedule(
                    session,
                    ChatSchedule.id == chat_schedule.id,
                    active=False
                )
                await session.commit()
                fails[chat_type] = fails.get(chat_type, 0) + 1
            except TelegramAPIError as err:
                logging.warning(f"Failed to send schedule {tg_id} - {err}")
                fails[chat_type] = fails.get(chat_type, 0) + 1
            else:
                success[chat_type] = success.get(chat_type, 0) + 1
                await asyncio.sleep(0.035)

        if success or fails:
            success_user, success_chat = success.get("user", 0), success.get("chat", 0)
            fails_user, fails_chat = fails.get("user", 0), fails.get("chat", 0)

            logging.info(
                f'Send schedule - [success/fails] Users: {success_user}/{fails_user}, Chats: {success_chat}/{fails_chat}'
            )

    await session.close()
