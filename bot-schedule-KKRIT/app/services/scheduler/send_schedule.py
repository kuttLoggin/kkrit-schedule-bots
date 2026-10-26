import asyncio
import logging
from datetime import datetime
from typing import Dict, Union

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramAPIError
from sqlalchemy import true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.infrastructure.database.functions.chat_schedules import update_chat_schedule, get_count_chat_schedules
from app.infrastructure.database.functions.chats import get_one_chat
from app.infrastructure.database.functions.users import get_one_user
from app.infrastructure.database.models import ChatSchedule
from app.services.fluent import FluentService
from app.services.scheduler.utils.send_schedule import chat_schedules_pagination, get_my_schedule, validation_schedules, \
    check_schedule_edit, get_text_tapes, old_function_pin_message
from app.utils.schedule.api import get_hulls, get_schedules
from app.utils.tools import natural_future_day, string_timedelta


async def send_schedule(bot: Bot, session_pool: sessionmaker, fluent: FluentService):
    session: AsyncSession = session_pool()

    hulls = await get_hulls()

    start_time = datetime.now()
    non_active_chat_schedules = []
    for hull_num, hull in hulls.items():
        query = [ChatSchedule.hull == hull_num, ChatSchedule.active == true()]

        count_chat_schedules = await get_count_chat_schedules(session, *query)
        if not count_chat_schedules:
            continue

        schedules = await get_schedules(hull_num, start_time.date().isoformat(), limit=5)
        schedules = validation_schedules(schedules)
        if not schedules:
            continue

        success, fails = {}, {}
        async for chat_schedule in chat_schedules_pagination(session, query, count_chat_schedules):
            sent_schedules = chat_schedule.sent_schedules.copy()

            schedule = get_my_schedule(schedules, sent_schedules)
            if not schedule:
                continue

            student_schedule: dict[str, Dict[str, Union[str, bool]]] = schedule["tapes"].get(chat_schedule.group)
            if not student_schedule:
                continue

            schedule_edit = check_schedule_edit(chat_schedule.group, schedule, student_schedule)

            chat_schedule.sent_schedules[schedule["date"].isoformat()] = schedule["modified"].isoformat()
            await update_chat_schedule(
                session,
                ChatSchedule.id == chat_schedule.id,
                sent_schedules=chat_schedule.sent_schedules
            )
            await session.commit()

            if schedule_edit is False and sent_schedules.get(schedule["date"].isoformat()):
                continue

            tape_availability = bool(student_schedule)
            text_tapes = (get_text_tapes(student_schedule) or "None") if tape_availability else "None"

            reply_markup = None  # ScheduleUrl().get(schedule)

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
                date=natural_future_day(schedule["date"]),
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
                    await old_function_pin_message(
                        bot, chat_schedule, session, msg.message_id, schedule, tape_availability, schedule_edit
                    )

                success[chat_type] = success.get(chat_type, 0) + 1
                await asyncio.sleep(0.035)

        success_user, success_chat = success.get("user", 0), success.get("chat", 0)
        fails_user, fails_chat = fails.get("user", 0), fails.get("chat", 0)

        if (success_user + success_chat + fails_user + fails_chat) > 10:
            time_string = string_timedelta(datetime.now() - start_time, "en")

            logging.info(
                f"Send schedule on {time_string} - "
                f"[success/fails] Users: {success_user}/{fails_user}, Chats: {success_chat}/{fails_chat}"
            )

    if non_active_chat_schedules:
        await update_chat_schedule(
            session,
            ChatSchedule.id.in_(non_active_chat_schedules),
            active=False
        )
        await session.commit()
    await session.close()
