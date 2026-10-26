import asyncio
import logging
import math
from datetime import datetime
from typing import List, Dict, Union

from aiogram import html, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from arrow import Arrow
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.functions.chat_schedules import get_pagination_chat_schedules, update_chat_schedule
from app.infrastructure.database.models import ChatSchedule


async def old_function_pin_message(
        bot: Bot,
        chat_schedule: ChatSchedule,
        session: AsyncSession,
        msg_pin_id: int,
        schedule: dict,
        tape_availability: bool,
        schedule_edit: bool
):
    now = Arrow.now().date()

    tg_id = chat_schedule.tg_id
    pin_msgs = chat_schedule.pin_msgs or {}
    for date, pin_msg_id in pin_msgs.copy().items():
        if Arrow.strptime(date, "%Y-%m-%d").date() < now or (schedule_edit and date == schedule["date"].isoformat()):
            del pin_msgs[date]

            try:
                await bot.unpin_chat_message(tg_id, int(pin_msg_id))
            except TelegramBadRequest:
                continue
            except TelegramAPIError as err:
                logging.warning(f"Failed unpin schedule {tg_id} - {err}")
            else:
                await asyncio.sleep(0.035)

    if schedule["date"] >= now and tape_availability:
        try:
            await bot.pin_chat_message(tg_id, msg_pin_id, False)
        except TelegramAPIError as err:
            logging.warning(f"Failed pin schedule {tg_id} - {err}")
        else:
            pin_msgs[schedule["date"].isoformat()] = msg_pin_id
            await asyncio.sleep(0.035)

    await update_chat_schedule(
        session,
        ChatSchedule.id == chat_schedule.id,
        pin_msgs=pin_msgs
    )
    await session.commit()


def get_text_tapes(student_schedule: dict[str, Dict[str, Union[str, bool]]]):
    text_tapes = []
    for number, tape in student_schedule.items():
        try:
            int(number)
        except ValueError:
            if not tape["title"]:
                continue
            num = ">"
        else:
            num = number

        text = html.quote(tape["title"] or "—")

        if tape["remoted"]:
            num = f"{num} [ДО]"

        string = f"<b>{num}</b> – {text}"
        if tape["class_rooms"]:
            class_rooms = []
            for class_room in tape["class_rooms"]:
                if isinstance(class_room, int):
                    class_rooms += [f"Каб. {class_room}"]
                else:
                    class_rooms += [class_room]

            string += f" | {', '.join(class_rooms)}"

        text_tapes.append(string)

    for tape in reversed(student_schedule.values()):
        if tape["original_text"]:
            break

        text_tapes.pop()

    return "\n".join(text_tapes)


# TODO: В будущем добавить классы что бы легче было читать код
def validation_schedules(schedules: List[Dict]):
    result = []
    for schedule in schedules:
        schedule = schedule.copy()

        schedule["date"] = datetime.fromisoformat(schedule["date"]).date()
        schedule["created"] = datetime.fromisoformat(schedule["created"])
        schedule["modified"] = datetime.fromisoformat(schedule["modified"])

        result.append(schedule)

    return result


async def chat_schedules_pagination(session: AsyncSession, query: list, count_chat_schedules: int, limit: int = 500):
    for num in range(1, math.ceil(count_chat_schedules / limit) + 1):
        offset = (num * limit) - limit

        chat_schedules = await get_pagination_chat_schedules(session, offset, limit, *query)

        for chat_schedule in chat_schedules:
            yield chat_schedule


def get_my_schedule(schedules: List[Dict], sent_schedules: dict):
    for schedule in schedules:
        if (
                sent_schedules.get(schedule["date"].isoformat())
        ) and (
                sent_schedules[schedule["date"].isoformat()] == schedule["modified"].isoformat()
        ):
            continue

        return schedule


def check_schedule_edit(group: str, schedule: Dict, student_schedule: Dict):
    old_tapes = schedule["old_tapes"]

    check = list(old_tapes[group].items()) != list(student_schedule.items()) if (
            (schedule["modified"] != schedule["created"]) and old_tapes and group in old_tapes
    ) else None

    return check
