import asyncio
import json
import logging
import math
from datetime import datetime
from typing import List

from aiogram import Bot, html
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramBadRequest
from aioredis import Redis
from arrow import Arrow
from sqlalchemy import true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.infrastructure.database.functions.chat_schedules import (
    get_count_chat_schedules, update_chat_schedule, get_pagination_chat_schedules
)
from app.infrastructure.database.functions.chats import get_one_chat
from app.infrastructure.database.functions.schedules import get_some_schedules
from app.infrastructure.database.functions.users import get_one_user
from app.infrastructure.database.models import ChatSchedule, Schedule
from app.keyboards.private.inline import ScheduleUrl
from app.services.fluent import FluentService
from app.utils.lock_factory import LockFactory
from app.utils.tools import natural_future_day, string_timedelta


async def pin_message_in_chat(
        bot: Bot,
        tg_id: int,
        pin_msgs: dict,
        msg_pin_id: int,
        schedule: Schedule
):
    if schedule.date < Arrow.now().date():
        return pin_msgs

    try:
        await bot.pin_chat_message(tg_id, msg_pin_id, False)
    except TelegramBadRequest:
        pass
    except TelegramAPIError as err:
        logging.warning(f"Failed pin schedule {tg_id} - {err}")
    else:
        pin_msgs[str(msg_pin_id)] = {
            "date": f"{schedule.date:%Y-%m-%d}",
            "schedule_id": schedule.id
        }
        await asyncio.sleep(0.035)

    return pin_msgs


async def unpin_messages_in_chat(
        bot: Bot,
        tg_id: int,
        pin_msgs: dict,
        schedule: Schedule
):
    now = Arrow.now().date()
    for pin_msg_id, data in pin_msgs.copy().items():
        if (
                Arrow.strptime(data["date"], "%Y-%m-%d").date() < now
        ) or schedule.id == data["schedule_id"]:

            try:
                await bot.unpin_chat_message(tg_id, int(pin_msg_id))
            except TelegramBadRequest:
                pass
            except TelegramAPIError as err:
                logging.warning(f"Failed unpin schedule {tg_id} - {err}")
            else:
                del pin_msgs[pin_msg_id]
                await asyncio.sleep(0.035)

    return pin_msgs


async def function_pin_message(
        bot: Bot,
        session: AsyncSession,
        chat_schedule: ChatSchedule,
        schedule: Schedule,
        msg_pin_id: int,
        tape_availability: bool
):
    pin_msgs = chat_schedule.pin_msgs or {}
    tg_id = chat_schedule.tg_id

    pin_msgs = await unpin_messages_in_chat(bot, tg_id, pin_msgs, schedule)

    if tape_availability:
        pin_msgs = await pin_message_in_chat(bot, tg_id, pin_msgs, msg_pin_id, schedule)

    await update_chat_schedule(
        session,
        ChatSchedule.id == chat_schedule.id,
        pin_msgs=pin_msgs
    )
    await session.commit()


async def old_function_pin_message(
        bot: Bot,
        chat_schedule: ChatSchedule,
        session: AsyncSession,
        msg_pin_id: int,
        schedule: Schedule,
        tape_availability: bool
):
    now = Arrow.now().date()
    tg_id = chat_schedule.tg_id
    pin_msgs = chat_schedule.pin_msgs or {}

    for pin_msg_id, data in pin_msgs.copy().items():
        if (
                Arrow.strptime(data["date"], "%Y-%m-%d").date() < now
        ) or schedule.id == data["schedule_id"]:
            del pin_msgs[pin_msg_id]

            try:
                await bot.unpin_chat_message(tg_id, int(pin_msg_id))
            except TelegramBadRequest:
                continue
            except TelegramAPIError as err:
                logging.warning(f"Failed unpin schedule {tg_id} - {err}")
            else:
                await asyncio.sleep(0.035)

    if schedule.date >= now and tape_availability:
        try:
            await bot.pin_chat_message(tg_id, msg_pin_id, False)
        except TelegramAPIError as err:
            logging.warning(f"Failed pin schedule {tg_id} - {err}")
        else:
            pin_msgs[str(msg_pin_id)] = {
                "date": f"{schedule.date:%Y-%m-%d}",
                "schedule_id": schedule.id
            }
            await asyncio.sleep(0.035)

    await update_chat_schedule(
        session,
        ChatSchedule.id == chat_schedule.id,
        pin_msgs=pin_msgs
    )
    await session.commit()


def get_text_tapes(schedule: list[dict], numbers: list):
    text_tapes = []
    for index, tape in enumerate(schedule):
        num = numbers[index] or ">"

        row_text = html.quote(tape["text"] or "—")
        text = " ".join(row_text.split())

        if tape["remoted"]:
            num = f"{num} [ДО]"

        string = f"<b>{num}</b> – {text}"
        text_tapes.append(string)

    return "\n".join(text_tapes)


def get_my_schedule(schedules: List[Schedule], sent_schedules: dict):
    for record in schedules:
        if (
                sent_schedules.get(str(record.id))
        ) and (
                sent_schedules[str(record.id)] == record.modified.isoformat()
        ):
            continue

        # Заглушка, 1 год время при котором расписание будет тупо пропускаться
        # TODO: Убрать при фиксе
        if record.modified.year == 1:
            continue

        return record


async def chat_schedules_pagination(session: AsyncSession, query: list, count_chat_schedules: int, limit: int = 500):
    for num in range(1, math.ceil(count_chat_schedules / limit) + 1):
        offset = (num * limit) - limit

        chat_schedules = await get_pagination_chat_schedules(session, offset, limit, *query)

        for chat_schedule in chat_schedules:
            yield chat_schedule


async def send_schedules(bot: Bot, session_pool: sessionmaker, redis: Redis, fluent: FluentService, lock_factory: LockFactory):
    if ((
            lock := lock_factory.get_key("collect_data")
    ) and lock.locked()) or ((
            lock := lock_factory.get_key("parsing_schedule")
    ) and lock.locked()):
        return

    session: AsyncSession = session_pool()

    hulls = await redis.get("hulls")
    hulls = json.loads(hulls) if hulls else {}

    start_time = datetime.now()

    non_active_chat_schedules = []

    for hull_num, hull in hulls.items():
        query = [ChatSchedule.hull == hull_num, ChatSchedule.active == true()]

        count_chat_schedules = await get_count_chat_schedules(session, *query)
        if not count_chat_schedules:
            continue

        schedules = await get_some_schedules(
            session,
            Schedule.hull == int(hull_num),
            Schedule.date >= datetime.now().date()
        )
        if not schedules:
            continue

        success = {}
        fails = {}

        async for chat_schedule in chat_schedules_pagination(session, query, count_chat_schedules):
            sent_schedules = chat_schedule.sent_schedules.copy()

            schedule = get_my_schedule(schedules, sent_schedules)
            if not schedule:
                continue

            student_schedule = schedule.tapes[chat_schedule.group]

            schedule_edit = schedule.old_tapes[chat_schedule.group] != student_schedule if (
                    (schedule.modified != schedule.created) and schedule.old_tapes
            ) else None

            chat_schedule.sent_schedules[str(schedule.id)] = schedule.modified.isoformat()
            await update_chat_schedule(
                session,
                ChatSchedule.id == chat_schedule.id,
                sent_schedules=chat_schedule.sent_schedules
            )
            await session.commit()

            if schedule_edit is False and sent_schedules.get(str(schedule.id)):
                continue

            tape_availability = bool(student_schedule)
            text_tapes = get_text_tapes(student_schedule, schedule.numbers) if tape_availability else "None"

            reply_markup = ScheduleUrl().get(schedule)

            tg_id = chat_schedule.tg_id
            chat_type = chat_schedule.chat_type

            if chat_type == "user":
                model = await get_one_user(session, tg_id=tg_id)
                lang = model.real_language
            else:
                model = await get_one_chat(session, tg_id=tg_id)
                lang = model.language

            i18n = fluent.get_translator_by_locale(lang or "ru")

            text = i18n.schedule(
                date=natural_future_day(schedule.date),
                tapes=text_tapes,
                edit=1 if schedule_edit else 0,
                bot_username=(await bot.me()).username
            )

            try:
                msg = await bot.send_message(tg_id, text, reply_markup=reply_markup, disable_web_page_preview=True)
            except TelegramForbiddenError:
                non_active_chat_schedules.append(chat_schedule.id)
                fails[chat_type] = fails.get(chat_type, 0) + 1
            except TelegramAPIError as err:
                logging.warning(f"Failed to send schedule {tg_id} - {err}")
                fails[chat_type] = fails.get(chat_type, 0) + 1
            else:
                if chat_schedule.pin_msg_func:
                    # await function_pin_message(bot, session, chat_schedule, schedule, msg.message_id, tape_availability)
                    await old_function_pin_message(
                        bot, chat_schedule, session, msg.message_id, schedule, tape_availability
                    )

                success[chat_type] = success.get(chat_type, 0) + 1
                await asyncio.sleep(0.035)

        success_user, success_chat = success.get("user", 0), success.get("chat", 0)
        fails_user, fails_chat = fails.get("user", 0), fails.get("chat", 0)

        if (success_user + success_chat + fails_user + fails_chat) >= 100:
            time_string = string_timedelta(datetime.now() - start_time, "en")

            logging.info(
                f'Send schedule on {time_string} - '
                f'[success/fails] Users: {success_user}/{fails_user}, Chats: {success_chat}/{fails_chat}'
            )

    if non_active_chat_schedules:
        await update_chat_schedule(
            session,
            ChatSchedule.id.in_(non_active_chat_schedules),
            active=False
        )
        await session.commit()
    await session.close()
