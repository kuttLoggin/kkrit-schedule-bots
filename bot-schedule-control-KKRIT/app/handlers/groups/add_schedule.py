import json
import logging
from datetime import datetime
from typing import Callable, Union

from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery
from aioredis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.functions.schedules import get_one_schedule, add_schedule, update_schedule
from app.infrastructure.database.models import Schedule
from app.keyboards.admin.inline import ScheduleCatcher
from app.utils.lock_factory import LockFactory
from app.utils.parser_schedule import CREATORS_SCHEDULE, SCHEDULE_RULES
from app.utils.parser_schedule.schedule_excel_v2 import parse_schedule
from app.utils.temp_document import temporary_document
from app.utils.tools import text_, get_date_on_name, get_date_string


async def schedule_catcher(obj: Union[Message, CallbackQuery], redis: Redis):
    m = obj.message if isinstance(obj, CallbackQuery) else obj

    file_id = m.document.file_id
    file_name = m.document.file_name

    data = {"file_id": file_id, "file_name": file_name}

    date = get_date_on_name(file_name)

    text = text_(
        f"✏ <b>Расписание</b> {data['file_name']}",
        "",
        f"🗓 На <b>{date:%d.%m.%Y} ({get_date_string(date)})</b>",
        "",
        "🏫 <b>Выберите корпус</b>"
    )

    hulls = await redis.get("hulls")
    hulls = json.loads(hulls.decode()) if hulls else {}

    if isinstance(obj, CallbackQuery):
        await obj.answer()
        await obj.message.delete_reply_markup()

    msg = await m.answer(text, reply_markup=ScheduleCatcher.SelectHull().get(hulls))

    await redis.set(f"add_schedule:{msg.message_id}", json.dumps(data, ensure_ascii=False))


async def select_hull(c: CallbackQuery, callback_data: ScheduleCatcher.SelectHull.CD, redis: Redis):
    data = await redis.get(f"add_schedule:{c.message.message_id}")
    data = json.loads(data.decode())

    hull_num = callback_data.hull
    data["hull_num"] = hull_num

    await redis.set(f"add_schedule:{c.message.message_id}", json.dumps(data, ensure_ascii=False))

    hulls = await redis.get("hulls")
    hulls = json.loads(hulls.decode())

    date = get_date_on_name(data["file_name"])

    text = text_(
        f"✏ <b>Расписание</b> {data['file_name']}",
        "",
        f"🗓 На <b>{date:%d.%m.%Y} ({get_date_string(date)})</b>",
        f"🏫 {hulls[hull_num]['name']}",
        "",
        "⚙ <b>Выберите парсер</b>"
    )

    await c.answer()
    await c.message.edit_text(text, reply_markup=ScheduleCatcher.SelectParser().get())


async def select_parser(c: CallbackQuery, callback_data: ScheduleCatcher.SelectParser.CD, redis: Redis):
    data = await redis.get(f"add_schedule:{c.message.message_id}")
    data = json.loads(data.decode())

    parser = callback_data.parser
    data["parser"] = parser

    await redis.set(f"add_schedule:{c.message.message_id}", json.dumps(data, ensure_ascii=False))

    hulls = await redis.get("hulls")
    hulls = json.loads(hulls.decode())

    date = get_date_on_name(data["file_name"])

    text = text_(
        f"✏ <b>Расписание</b> {data['file_name']}",
        "",
        f"🗓 На <b>{date:%d.%m.%Y} ({get_date_string(date)})</b>",
        f"🏫 {hulls[data['hull_num']]['name']}",
        "",
        f"⚙ <b>Парсер</b>: {parser}",
        "",
        "🔧 <b>Выберите правило для парсера</b>"
    )

    await c.answer()
    await c.message.edit_text(text, reply_markup=ScheduleCatcher.SelectRule().get(parser))


async def select_rule(c: CallbackQuery, callback_data: ScheduleCatcher.SelectRule.CD, redis: Redis):
    data = await redis.get(f"add_schedule:{c.message.message_id}")
    data = json.loads(data.decode())

    rule = callback_data.rule
    data["rule"] = None if rule == "-" else rule

    await redis.set(f"add_schedule:{c.message.message_id}", json.dumps(data, ensure_ascii=False))

    hulls = await redis.get("hulls")
    hulls = json.loads(hulls.decode())

    date = get_date_on_name(data["file_name"])

    text = text_(
        f"✏ <b>Расписание</b> {data['file_name']}",
        "",
        f"🗓 На <b>{date:%d.%m.%Y} ({get_date_string(date)})</b>",
        f"🏫 {hulls[data['hull_num']]['name']}",
        "",
        f"⚙ <b>Парсер</b>: {data['parser']}",
        f"🔧 <b>Правило</b>: {'Отсутствует' if rule == '-' else rule}",
        "",
        "❔ <b>Парсим расписание и добавляем его?</b>"
    )

    await c.answer()
    await c.message.edit_text(text, reply_markup=ScheduleCatcher.LetsGo().get())


async def lets_go(c: CallbackQuery, bot: Bot, redis: Redis, session: AsyncSession, lock_factory: LockFactory):
    await c.answer("⏳ Подождите...")
    await c.message.edit_reply_markup(ScheduleCatcher.LetsGo().click())

    data = await redis.get(f"add_schedule:{c.message.message_id}")
    data = json.loads(data.decode())

    await redis.delete(f"add_schedule:{c.message.message_id}")

    with temporary_document(".xlsx") as file_path:
        try:
            await bot.download(data['file_id'], file_path)
            create_schedule: Callable = CREATORS_SCHEDULE[data["parser"]]
            tables = parse_schedule(file_path)
            schedule, groups = create_schedule(tables)

            if data["rule"]:
                enforce_rule: Callable = SCHEDULE_RULES[data["parser"]][data["rule"]]
                schedule = enforce_rule(schedule)
        except Exception as err:
            logging.exception(err)
            await c.message.answer(str(err))
            return

    date = get_date_on_name(data["file_name"])

    now = datetime.now()

    record = await get_one_schedule(session, hull=data["hull_num"], date=date)

    if record and record.tapes == schedule:
        await c.message.answer(f"🥱 Расписание идентично, изменений не требуется")
        return

    if not record:
        record = await add_schedule(
            session,
            name=data["file_name"],
            hull=data["hull_num"],
            tapes=schedule,
            date=date,
            created=now,
            modified=now
        )
    else:
        await update_schedule(
            session,
            Schedule.id == record.id,
            tapes=schedule,
            old_tapes=record.tapes,
            modified=now
        )
    await session.commit()

    if record.created == record.modified:
        await c.message.answer(f"✅ <b>Расписание</b> успешно <b>добавлено</b> [ID <code>{record.id}</code>]")
    else:
        await c.message.answer(f"✅ <b>Расписание</b> успешно <b>обновлено</b> [ID <code>{record.id}</code>]")


async def cancel(c: CallbackQuery, redis: Redis):
    await redis.delete(f"add_schedule:{c.message.message_id}")

    await c.answer()
    await c.message.edit_reply_markup(ScheduleCatcher.Cancel().click())


def setup(router: Router):
    router.message.register(
        schedule_catcher,
        F.content_type == "document",
        F.document.file_name.lower().split(".")[-1] == "xlsx"
    )
    router.callback_query.register(schedule_catcher, ScheduleCatcher.Question.CD.filter())

    router.callback_query.register(select_hull, ScheduleCatcher.SelectHull.CD.filter())
    router.callback_query.register(select_parser, ScheduleCatcher.SelectParser.CD.filter())
    router.callback_query.register(select_rule, ScheduleCatcher.SelectRule.CD.filter())
    router.callback_query.register(lets_go, ScheduleCatcher.LetsGo.CD.filter())

    router.callback_query.register(cancel, ScheduleCatcher.Cancel.CD.filter())
