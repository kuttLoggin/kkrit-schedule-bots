import json
from contextlib import suppress
from datetime import timedelta

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, User, Chat
from aioredis import Redis
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Config
from app.constants.bot_rights import BOT_RIGHTS
from app.infrastructure.database.functions.chat_schedules import (
    get_one_chat_schedule, add_chat_schedule, update_chat_schedule
)
from app.infrastructure.database.models import ChatSchedule
from app.keyboards.private.inline import SelectHull, SelectGroup, SettingSchedule
from app.utils.lock_factory import LockFactory
from app.utils.schedule.api import get_hulls, get_groups


async def check_admin(bot: Bot, user: User, chat: Chat, redis: Redis):
    if str(user.id) in Config.ADMINS:
        return False

    chat_admins: bytes = await redis.get(f"chat_admins-{chat.id}")
    if not chat_admins:
        admins = await bot.get_chat_administrators(chat.id)
        chat_admins = [admin.user.id for admin in admins]

        await redis.set(f"chat_admins-{chat.id}", json.dumps(chat_admins), ex=30)
    else:
        chat_admins = json.loads(chat_admins)

    if user.id not in chat_admins:
        return True


async def get_text_settings(i18n: TranslatorRunner, chat_schedule: ChatSchedule):
    hulls = await get_hulls()

    my_hull = hulls[chat_schedule.hull]

    return i18n.settings.info(
        active=int(chat_schedule.active),
        hull=my_hull["name"],
        group=chat_schedule.group
    )


async def show_settings(
        m: Message,
        bot: Bot,
        i18n: TranslatorRunner,
        session: AsyncSession,
        redis: Redis,
        state: FSMContext
):
    # TODO: Заменить на нормальный фильтр
    if m.chat.type != "private":
        if await check_admin(bot, m.from_user, m.chat, redis):
            return

    chat_schedule = await get_one_chat_schedule(session, tg_id=m.chat.id)
    if not chat_schedule:
        hulls = await get_hulls()

        await m.answer(i18n.settings.new.hull(), reply_markup=SelectHull().get(hulls))
        return

    text = await get_text_settings(i18n, chat_schedule)

    msg = await m.answer(
        text=text,
        reply_markup=SettingSchedule().get(i18n, chat_schedule.active, chat_schedule.pin_msg_func)
    )

    data = await state.get_data()
    await state.update_data(settings_msg_id=msg.message_id)

    old_settings_msg_id = data.get("settings_msg_id")
    if old_settings_msg_id:
        with suppress(TelegramAPIError):
            await bot.edit_message_reply_markup(msg.chat.id, old_settings_msg_id)


async def select_new_hull(
        c: CallbackQuery,
        callback_data: SelectHull.CD,
        bot: Bot,
        i18n: TranslatorRunner,
        state: FSMContext,
        redis: Redis
):
    if c.message.chat.type != "private":
        if await check_admin(bot, c.from_user, c.message.chat, redis):
            await c.answer(i18n.err.not_admin(), cache_time=15)
            return

    await c.answer()

    hull_num = callback_data.num

    await state.update_data(hull=hull_num)

    all_groups = await get_groups()
    groups = all_groups[hull_num]

    with suppress(TelegramAPIError):
        await c.message.edit_text(i18n.settings.new.group(), reply_markup=SelectGroup().get(groups))


async def select_new_group(
        c: CallbackQuery,
        callback_data: SelectGroup.CD,
        i18n: TranslatorRunner,
        bot: Bot,
        state: FSMContext,
        session: AsyncSession,
        redis: Redis
):
    if c.message.chat.type != "private":
        if await check_admin(bot, c.from_user, c.message.chat, redis):
            await c.answer(i18n.err.not_admin(), cache_time=15)
            return

    await c.answer()

    data = await state.get_data()
    await state.clear()

    hull = data["hull"]
    group = callback_data.group

    chat_schedule = await get_one_chat_schedule(session, tg_id=c.message.chat.id)

    if chat_schedule:
        await update_chat_schedule(
            session,
            ChatSchedule.id == chat_schedule.id,
            hull=hull,
            group=group,
            sent_schedules={}
        )
    else:
        await add_chat_schedule(
            session,
            tg_id=c.message.chat.id,
            chat_type="user" if c.message.chat.type == "private" else "chat",
            hull=hull,
            group=group
        )
    await session.commit()

    with suppress(TelegramAPIError):
        await c.message.edit_text(i18n.settings.success())


async def pg_new_group(
        c: CallbackQuery,
        callback_data: SelectGroup.PG,
        state: FSMContext,
        i18n: TranslatorRunner
):
    await c.answer()

    offset = int(callback_data.offset)

    data = await state.get_data()

    try:
        hull_num = data["hull"]
    except KeyError:
        hulls = await get_hulls()

        await c.message.edit_text(i18n.settings.new.hull(), reply_markup=SelectHull().get(hulls))
        return

    all_groups = await get_groups()
    groups = all_groups[hull_num]

    with suppress(TelegramAPIError):
        await c.message.edit_reply_markup(SelectGroup().get(groups, offset))


async def change_data(c: CallbackQuery, i18n: TranslatorRunner, bot: Bot, redis: Redis):
    if c.message.chat.type != "private":
        if await check_admin(bot, c.from_user, c.message.chat, redis):
            await c.answer(i18n.err.not_admin(), cache_time=15)
            return

    await c.answer()

    hulls = await get_hulls()

    with suppress(TelegramAPIError):
        await c.message.edit_text(i18n.settings.new.hull(), reply_markup=SelectHull().get(hulls))


async def change_active(c: CallbackQuery, i18n: TranslatorRunner, bot: Bot, session: AsyncSession, redis: Redis):
    if c.message.chat.type != "private":
        if await check_admin(bot, c.from_user, c.message.chat, redis):
            await c.answer(i18n.err.not_admin(), cache_time=15)
            return

    await c.answer()

    chat_schedule = await get_one_chat_schedule(session, tg_id=c.message.chat.id)

    await update_chat_schedule(
        session,
        ChatSchedule.id == chat_schedule.id,
        active=not chat_schedule.active
    )
    await session.commit()

    text = await get_text_settings(i18n, chat_schedule)

    with suppress(TelegramAPIError):
        await c.message.edit_text(
            text=text,
            reply_markup=SettingSchedule().get(i18n, chat_schedule.active, chat_schedule.pin_msg_func)
        )


async def change_pin_msg_func(
        c: CallbackQuery,
        i18n: TranslatorRunner,
        bot: Bot,
        session: AsyncSession,
        redis: Redis,
        lock_factory: LockFactory
):
    if c.message.chat.type != "private":
        if await check_admin(bot, c.from_user, c.message.chat, redis):
            await c.answer(i18n.err.not_admin(), cache_time=15)
            return

    chat_id = c.message.chat.id

    chat_schedule = await get_one_chat_schedule(session, tg_id=chat_id)

    if c.message.chat.type != "private" and chat_schedule.pin_msg_func is False:
        async with lock_factory.get_lock(f"check_bot_admin:{chat_id}"):
            check_bot_admin = await redis.get(f"check_bot_admin:{chat_id}")
            if check_bot_admin is not None and not check_bot_admin:
                await c.answer(i18n.settings.change.pin_msg.err(), show_alert=True)
                return

            admins = await bot.get_chat_administrators(chat_id)

            bot_admin = False
            for admin in admins:
                if admin.user.id == (await bot.me()).id:
                    bot_rights = [getattr(admin, right) for right in BOT_RIGHTS]
                    bot_admin = all(bot_rights)
                    break

            await redis.set(f"check_bot_admin:{chat_id}", int(bot_admin), ex=timedelta(seconds=7))

            if not bot_admin:
                await c.answer(i18n.settings.change.pin_msg.err(), show_alert=True)
                return

    await c.answer()

    await update_chat_schedule(
        session,
        ChatSchedule.id == chat_schedule.id,
        pin_msg_func=not chat_schedule.pin_msg_func
    )
    await session.commit()

    text = await get_text_settings(i18n, chat_schedule)

    with suppress(TelegramAPIError):
        await c.message.edit_text(
            text=text,
            reply_markup=SettingSchedule().get(i18n, chat_schedule.active, chat_schedule.pin_msg_func)
        )


def setup(router: Router):
    router.message.register(show_settings, Command(commands="settings"))
    router.callback_query.register(select_new_hull, SelectHull.CD.filter())
    router.callback_query.register(select_new_group, SelectGroup.CD.filter())
    router.callback_query.register(pg_new_group, SelectGroup.PG.filter())
    router.callback_query.register(change_data, SettingSchedule.CD.filter(F.act == "change_data"))
    router.callback_query.register(change_active, SettingSchedule.CD.filter(F.act == "change_active"))
    router.callback_query.register(change_pin_msg_func, SettingSchedule.CD.filter(F.act == "change_pin_msg_func"))
