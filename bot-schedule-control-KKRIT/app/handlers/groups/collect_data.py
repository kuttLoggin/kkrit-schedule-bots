import json
import logging
from typing import Callable

from aiogram import F, Router, html, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aioredis import Redis

from app.keyboards.admin.inline import SelectParserGroupsOnSchedule, CancelKb
from app.states.admin_states import UpdateCollectDataGroupsAdmin, UpdateCollectDataHullsAdmin, GetGroupsOnSchedule
from app.utils.parser_schedule import CREATORS_SCHEDULE
from app.utils.parser_schedule.schedule_excel_v2 import parse_schedule
from app.utils.parser_schedule.utils import collect_hulls
from app.utils.temp_document import temporary_document
from app.utils.tools import text_

from collections import OrderedDict


async def show_info(m: Message, redis: Redis):
    hulls = await redis.get("hulls")
    groups = await redis.get("groups")

    if hulls:
        hulls = hulls.decode() if hulls else None
        hulls = html.quote(json.dumps(json.loads(hulls, object_pairs_hook=OrderedDict), indent=4, ensure_ascii=False))

    if groups:
        groups = groups.decode() if groups else None
        groups = html.quote(json.dumps(json.loads(groups, object_pairs_hook=OrderedDict), indent=2, ensure_ascii=False))

    await m.answer(
        text_(
            "<b>Collect data</b>:",
            "",
            "<b>Hulls</b>:",
            html.code(hulls),
            "",
            "<b>Groups</b>:",
            html.code(groups)
        )
    )


async def update_groups_on_json(m: Message, state: FSMContext):
    await state.set_state(UpdateCollectDataGroupsAdmin.SEND_JSON)
    await m.answer("Пришлите новый JSON для обновления данных о группах", reply_markup=CancelKb().get())


async def take_update_groups_on_json(m: Message, state: FSMContext, redis: Redis):
    await state.clear()

    try:
        json_data = json.dumps(json.loads(m.text, object_pairs_hook=OrderedDict))

        await redis.set("groups", json_data)
    except Exception as err:
        logging.exception(err)
        await m.answer(str(err))
    else:
        await m.answer("Данные о группах обновлены")


async def update_hulls_on_json(m: Message, state: FSMContext):
    await state.set_state(UpdateCollectDataHullsAdmin.SEND_JSON)
    await m.answer("Пришлите новый JSON для обновления данных о корпусах", reply_markup=CancelKb().get())


async def take_update_hulls_on_json(m: Message, state: FSMContext, redis: Redis):
    await state.clear()

    try:
        json_data = json.dumps(json.loads(m.text, object_pairs_hook=OrderedDict))

        await redis.set("hulls", json_data)
    except Exception as err:
        logging.exception(err)
        await m.answer(str(err))
    else:
        await m.answer("Данные о корпусах обновлены")


async def get_online_hulls(m: Message, redis: Redis):
    hulls = await collect_hulls()

    hulls = html.quote(json.dumps(hulls, indent=4, ensure_ascii=False))

    await m.answer(html.code(hulls))


async def get_groups_on_schedule(m: Message, redis: Redis, state: FSMContext):
    await state.set_state(GetGroupsOnSchedule.SEND_FILE)
    await m.answer("Отправьте XLSX файл с расписанием", reply_markup=CancelKb().get())


async def select_parser_groups_on_schedule(m: Message, bot: Bot, redis: Redis, state: FSMContext):
    if m.document.file_name.lower().split(".")[-1] != "xlsx":
        await m.answer("Вы отправили не XLSX файл")
        return

    await state.set_state(GetGroupsOnSchedule.SELECT_PARSER)
    await state.update_data(file_name=m.document.file_name, file_id=m.document.file_id)
    await m.answer("Выберите парсер", reply_markup=SelectParserGroupsOnSchedule().get())


async def parsing_groups_on_schedule(
        c: CallbackQuery,
        callback_data: SelectParserGroupsOnSchedule.CD,
        bot: Bot,
        state: FSMContext
):
    await c.answer()
    await c.message.edit_reply_markup(SelectParserGroupsOnSchedule().selected(callback_data.parser))

    data = await state.get_data()
    await state.clear()

    file_id = data["file_id"]

    with temporary_document(".xlsx") as file_path:
        try:
            await bot.download(file_id, file_path)
            create_schedule: Callable = CREATORS_SCHEDULE[callback_data.parser]
            tables = parse_schedule(file_path)
            schedule, groups = create_schedule(tables)
        except Exception as err:
            logging.exception(err)
            await c.message.answer(str(err))
            return

    if isinstance(groups, list):
        groups = html.quote(json.dumps(groups, indent=2, ensure_ascii=False))
    else:
        groups = str(groups)

    await c.message.answer(html.code(groups))


def setup(router: Router):
    router.message.register(show_info, Command("show_collect_data"))

    router.message.register(update_groups_on_json, Command("update_collect_data_groups"))
    router.message.register(take_update_groups_on_json, StateFilter(UpdateCollectDataGroupsAdmin.SEND_JSON))

    router.message.register(update_hulls_on_json, Command("update_collect_data_hulls"))
    router.message.register(take_update_hulls_on_json, StateFilter(UpdateCollectDataHullsAdmin.SEND_JSON))

    router.message.register(get_online_hulls, Command("get_online_hulls"))

    router.message.register(get_groups_on_schedule, Command("get_groups_on_schedule"))
    router.message.register(
        select_parser_groups_on_schedule,
        F.content_type == "document",
        StateFilter(GetGroupsOnSchedule.SEND_FILE)
    )
    router.callback_query.register(
        parsing_groups_on_schedule,
        SelectParserGroupsOnSchedule.CD.filter(),
        StateFilter(GetGroupsOnSchedule.SELECT_PARSER)
    )
