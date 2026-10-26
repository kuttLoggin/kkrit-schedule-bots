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


def get_text_tapes(teacher_schedule: Dict[str, Dict[str, Union[str, bool]]], teacher_groups: list):
    text_tapes = []
    for number, tape in teacher_schedule.items():
        try:
            int(number)
        except ValueError:
            num = ">"
        else:
            num = number

        text = html.quote(tape["title"] or "—")

        group = f"<b>{tape['group']}</b>" if (
                tape["group"] not in (teacher_groups if teacher_groups else [])
        ) else f"<u><b>{tape['group']}</b></u>"

        if tape["remoted"]:
            num = f"{num} [ДО]"

        string = f"<b>{num}</b> – [{group}] {text}"
        if tape["class_rooms"]:
            class_rooms = []
            for class_room in tape["class_rooms"]:
                if isinstance(class_room, int):
                    class_rooms += [f"Каб. {class_room}"]
                else:
                    class_rooms += [class_room]

            string += f" | {', '.join(class_rooms)}"

        text_tapes.append(string)

    for tape in reversed(teacher_schedule.values()):
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


def create_teacher_schedule(schedule: Dict, teacher_name: str):
    if schedule is None:
        return None

    teacher_tapes = []
    for group_name, tapes in schedule.copy().items():
        for num, tape in tapes.items():
            if not tape["teachers"]:
                continue
            for teacher in tape["teachers"]:
                if teacher_name.lower() == teacher.lower():
                    break
            else:
                continue

            tape["group"] = group_name

            teacher_tapes.append((num, tape))

    teacher_tapes = sorted(teacher_tapes, key=lambda item: item[0])

    teacher_schedule = {}
    current_num, current_num_count = None, 1
    for num, tape in teacher_tapes:
        if current_num == num:
            num = "-" * current_num_count
            current_num_count += 1

        current_num = num
        teacher_schedule[num] = tape

    return teacher_schedule


def get_my_schedule(schedules: List[Dict], sent_schedules: dict, teacher_name: str):
    for schedule in schedules:
        if (
                sent_schedules.get(schedule["date"].isoformat())
        ) and (
                sent_schedules[schedule["date"].isoformat()] == schedule["modified"].isoformat()
        ):
            continue

        schedule = schedule.copy()
        schedule["tapes"] = create_teacher_schedule(schedule["tapes"], teacher_name)
        schedule["old_tapes"] = create_teacher_schedule(schedule["old_tapes"], teacher_name)

        return schedule


def check_schedule_edit(schedule: Dict):
    tapes = schedule["tapes"]
    old_tapes = schedule["old_tapes"]

    check = list(old_tapes.items()) != list(tapes.items()) if (
            (schedule["modified"] != schedule["created"]) and tapes and old_tapes
    ) else None

    return check
