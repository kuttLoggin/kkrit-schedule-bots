import asyncio
import json
import logging
import math
from contextlib import suppress
from datetime import datetime

from aiogram import F, Router, Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter, TelegramForbiddenError
from aiogram.filters import Command, StateFilter, ContentTypesFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ContentType
from aioredis import Redis
from arrow import Arrow
from sqlalchemy import true
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.functions.models import get_count_models, get_pagination_models, update_model
from app.infrastructure.database.models import User, Chat, ChatSchedule
from app.keyboards.admin.inline import CancelBroadcast, SelectBroadcastGroup, CancelKb, StartBroadcast
from app.states.admin_states import BroadcastAdmin
from app.utils.broadcast import MemoryBroadcastBotLocker, BroadcastLockException, BroadcastCancel, send_copy
from app.utils.tools import get_mention, string_timedelta


GROUP_MODELS = {
    "user": {
        "model": User,
        "clauses": [User.active == true()]
    },
    "chat": {
        "model": Chat,
        "clauses": [Chat.active == true()]
    },
    "sd_user": {
        "model": ChatSchedule,
        "clauses": [ChatSchedule.active == true(), ChatSchedule.chat_type == "user"]
    },
    "sd_chat": {
        "model": ChatSchedule,
        "clauses": [ChatSchedule.active == true(), ChatSchedule.chat_type == "chat"]
    }
}
TITLE_NAMES_GROUPS = {
    "user,chat": "Все",
    "user": "Юзеры",
    "chat": "Чаты",
    "sd_user,sd_chat": "Все кто получает расписание",
    "sd_user": "Юзеры получающих расписание",
    "sd_chat": "Чаты получающих расписание"
}
NAME_GROUPS = {
    "user,chat": "всех",
    "user": "юзеров",
    "chat": "чатов",
    "sd_user,sd_chat": "всех кто получает расписание",
    "sd_user": "юзеров получающих расписание",
    "sd_chat": "чатов получающих расписание"
}


async def command_broadcast(
        m: Message,
        bot: Bot,
        broadcast_locker: MemoryBroadcastBotLocker,
        redis: Redis
):
    if broadcast_locker.is_exist(bot.id):
        info = await redis.get("broadcast")
        if not info:
            await m.answer(
                "❗ <b>Рассылка уже запущена</b>, но нет данных о ней...\n"
                "❓ Похоже на баг, сообщите об этом разработчику.",
                reply_markup=CancelBroadcast().get()
            )
            return

        info = json.loads(info)

        group = info["group"]
        pos_start = info["pos_start"]
        pos_end = info["pos_end"]
        admin_mention = get_mention(info["user_id"], info["full_name"])
        date_start = Arrow.fromdatetime(datetime.fromisoformat(info["date_start"]))

        await m.answer(
            f"⛔ <b>Рассылка уже запущена админом</b> {admin_mention}.\n"
            f"✉ Рассылается для <b>{NAME_GROUPS[group]}</b>\n\n\m"
            f"✏ <b>Прогресс</b>: {pos_start}/{pos_end}\n"
            f"⏳ Начало: {date_start:DD.MM HH:mm:SS}\n\n"
            f"🏃 Идёт: {string_timedelta(Arrow.now() - date_start)}",
            reply_markup=CancelBroadcast().get()
        )
        return

    await m.answer(
        "✉ Выберите <b>группу</b> для рассылки",
        reply_markup=SelectBroadcastGroup().get(),
    )


async def select_group(
        c: CallbackQuery,
        callback_data: SelectBroadcastGroup.CD,
        state: FSMContext,
        session: AsyncSession
):
    await c.answer()

    groups = callback_data.group

    await state.set_state(BroadcastAdmin.SEND_MESSAGE)
    await state.update_data(group=callback_data.group)

    count = 0
    for the_group in [GROUP_MODELS[group] for group in groups.split(",")]:
        count += await get_count_models(
            session,
            the_group["model"],
            *the_group["clauses"]
        )

    with suppress(TelegramAPIError):
        await c.message.delete_reply_markup()
    await c.message.answer(
        f"✉ <b>Группа для рассылки</b>: {TITLE_NAMES_GROUPS[groups]}\n"
        f"🔎 <b>Количество</b>: {count}\n"
        f"✏ Отправьте мне <b>сообщение</b> (альбомы не поддерживаются), которое вы хотите разослать.",
        reply_markup=CancelKb().get()
    )


async def pre_start_broadcasting(m: Message, state: FSMContext, bot: Bot):
    await state.set_state(BroadcastAdmin.START)
    await state.update_data(message=m.json())

    try:
        await bot(send_copy(m, m.chat.id, disable_web_page_preview=True))
    except TelegramAPIError as err:
        logging.warning(f"Fail check message on broadcast - {err}")

        await m.answer("❌ С сообщением что-то не так.")
    else:
        await m.answer(
            "🧘 <b>Всё готово</b>",
            reply_markup=StartBroadcast().get()
        )


async def cancel_broadcast(c: CallbackQuery, redis: Redis):
    data = {"user_id": c.from_user.id, "full_name": c.from_user.full_name}

    await redis.set("broadcast_cancel", json.dumps(data))

    with suppress(TelegramAPIError):
        await c.message.delete_reply_markup()
    await c.message.answer("⛔ <b>Рассылка принудительно завершена</b>.")


async def start_broadcasting(
        c: CallbackQuery,
        bot: Bot,
        state: FSMContext,
        session: AsyncSession,
        broadcast_locker: MemoryBroadcastBotLocker,
        redis: Redis
):
    # TODO: Всё это не очень выглядит, переписать бы потом

    data = await state.get_data()
    await state.clear()

    msg = Message(**json.loads(data["message"]))
    groups = data["group"]

    with suppress(TelegramAPIError):
        await c.message.delete_reply_markup()

    date_start = Arrow.now()

    info_text = f"✉ Рассылается для <b>{NAME_GROUPS[groups]}</b>\n\n" \
                "✏ <b>Прогресс</b>: {pos_start}/{pos_end}\n\n" \
                f"⏳ Начало: {date_start:DD.MM HH:mm:SS}\n" \
                "🏃 Идёт: {date_process}"

    pos_start = 0
    pos_end = 0
    success = 0

    try:
        await c.message.answer(
            "✅ <b>Рассылка запущена</b>",
            reply_markup=CancelBroadcast().get()
        )

        if await redis.get("broadcast_cancel"):
            await redis.delete("broadcast_cancel")

        for the_group in [GROUP_MODELS[group] for group in groups.split(",")]:
            pos_end += await get_count_models(
                session,
                the_group["model"],
                *the_group["clauses"]
            )

        dict_info = {
            "pos_start": pos_start,
            "pos_end": pos_end,
            "group": groups,
            "user_id": c.from_user.id,
            "full_name": c.from_user.full_name,
            "date_start": date_start.isoformat()
        }

        await redis.set("broadcast", json.dumps(dict_info))

        info_msg = await c.message.answer(
            info_text.format(pos_start=pos_start, pos_end=pos_end, date_process="~")
        )

        limit = 500
        date = Arrow.now().shift(seconds=3)

        async with broadcast_locker.lock(bot.id):
            for the_group in [GROUP_MODELS[group] for group in groups.split(",")]:
                count_records = await get_count_models(session, the_group["model"], *the_group["clauses"])

                for num in range(1, math.ceil(count_records / limit) + 1):
                    offset = (num * limit) - limit

                    records = await get_pagination_models(session, the_group["model"], offset, limit, *the_group["clauses"])

                    for record in records:
                        try:
                            await bot(send_copy(msg, chat_id=record.tg_id, disable_web_page_preview=True))
                        except TelegramRetryAfter as err:
                            logging.error(
                                f"Target [ID:{record.tg_id}]: Flood limit is exceeded. "
                                f"Sleep {err.retry_after} seconds."
                            )
                            await asyncio.sleep(err.retry_after)
                        except TelegramForbiddenError:
                            await update_model(
                                session, the_group["model"],
                                the_group["model"].tg_id == record.tg_id,
                                active=False
                            )
                            await session.commit()
                        except TelegramAPIError as err:
                            logging.exception(err)
                        else:
                            success += 1

                        pos_start += 1

                        if date < Arrow.now():
                            date = Arrow.now().shift(seconds=3)

                            if await redis.get("broadcast_cancel"):
                                raise BroadcastCancel

                            dict_info.update(pos_start=pos_start, pos_end=pos_end)

                            await redis.set("broadcast", json.dumps(dict_info))

                            with suppress(TelegramAPIError):
                                await info_msg.edit_text(
                                    info_text.format(
                                        pos_start=f"{pos_start:_}".replace("_", " "),
                                        pos_end=f"{pos_end:_}".replace("_", " "),
                                        date_process=string_timedelta(Arrow.now() - date_start)
                                    )
                                )

                        await asyncio.sleep(0.035)
    except BroadcastLockException:
        info = await redis.get("broadcast")
        if not info:
            await c.message.answer(
                "❗ <b>Рассылка уже запущена</b>, но нет данных о ней...\n"
                "❓ Похоже на баг, сообщите об этом разработчику.",
                reply_markup=CancelBroadcast().get()
            )
            return

        info = json.loads(info)

        groups = info["group"]
        pos_start = info["pos_start"]
        pos_end = info["pos_end"]
        date_start = Arrow.fromdatetime(datetime.fromisoformat(info["date_start"]))

        admin_mention = get_mention(info["user_id"], info["full_name"])

        await c.message.answer(
            f"⛔ <b>Рассылка уже запущена админом</b> {admin_mention}\n"
            f"✉ Рассылается для <b>{NAME_GROUPS[groups]}</b>\n\n"
            f"✏ <b>Прогресс</b>: {pos_start}/{pos_end}\n\n"
            f"⏳ Начало: {date_start:DD.MM HH:mm:SS}\n"
            f"🏃 Идёт: {string_timedelta(Arrow.now() - date_start)}",
        )
        return
    except BroadcastCancel:
        pass

    await redis.delete("broadcast")
    cancel = await redis.get("broadcast_cancel")
    if cancel:
        await redis.delete("broadcast_cancel")
        cancel = json.loads(cancel)

        admin_mention = get_mention(cancel["user_id"], cancel["full_name"])
        title = f"❗ <b>Рассылка завершена преждевременно админом</b> {admin_mention}"
    else:
        title = "✅ <b>Рассылка завершена</b>"

    progress = f"{pos_start:_}/{pos_end:_}".replace("_", " ")
    success_full = f"{success:_} ({success / pos_end * 100:.2f}%)".replace("_", " ")

    await c.message.answer(
        f"{title}\n"
        f"✉ Рассылалось для <b>{NAME_GROUPS[groups]}</b>\n\n"
        f"✏ <b>Результат</b>: {progress}\n"
        f"📍 <b>Успешно отправлено сообщений</b>: {success_full}\n\n"
        f"⏳ <b>Начало/Конец</b>: {date_start:DD.MM HH:mm:SS} - {Arrow.now():DD.MM HH:mm:SS}\n"
        f"🚶 <b>Шло</b>: {string_timedelta(Arrow.now() - date_start)}"
    )


def setup(router: Router):
    router.message.register(command_broadcast, Command(commands="broadcast"))
    router.callback_query.register(select_group, SelectBroadcastGroup.CD.filter())
    router.message.register(
        pre_start_broadcasting,
        StateFilter(state=BroadcastAdmin.SEND_MESSAGE),
        ContentTypesFilter(content_types=ContentType.ANY)
    )
    router.callback_query.register(cancel_broadcast, F.data == CancelBroadcast.cb)
    router.callback_query.register(start_broadcasting, F.data == StartBroadcast.cb)
