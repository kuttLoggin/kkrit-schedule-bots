import logging

from aiogram import Dispatcher, F, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import (
    ContentTypesFilter, ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER, or_f, LEAVE_TRANSITION,
    MEMBER, ADMINISTRATOR
)
from aiogram.types import ChatMemberUpdated, Message, ContentType, ChatMemberMember, ChatMemberOwner
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.bot_rights import BOT_RIGHTS
from app.infrastructure.database import models
from app.infrastructure.database.functions.chats import get_one_chat, create_chat, update_chat
from app.infrastructure.database.functions.local_chat_users import (
    get_one_local_chat_user, create_local_chat_user, update_local_chat_user
)
from app.infrastructure.database.functions.users import get_one_user, update_user, create_user
from app.infrastructure.database.models import LocalChatUser, Chat


async def get_chat_owner(session, bot: Bot, chat: Chat, admins: list = None):
    try:
        admins = admins or await bot.get_chat_administrators(chat.id)
        owner = [admin for admin in admins if isinstance(admin, ChatMemberOwner)][0]

        user_db = await get_one_user(session, tg_id=owner.user.id)
        if not user_db:
            user_db = await create_user(session, owner.user, chat.type)
            await session.commit()

        owner = user_db
    except TelegramAPIError as err:
        logging.info(err)
        owner = None

    return owner


async def set_user_active(my_chat_member: ChatMemberUpdated, session: AsyncSession):
    user = await get_one_user(session, tg_id=my_chat_member.from_user.id)

    if user:
        await update_user(
            session,
            models.User.id == user.id, active=my_chat_member.new_chat_member.status == "member"
        )
        await session.commit()


async def set_local_chat_user_active(message: Message, session: AsyncSession):
    chat_members = message.new_chat_members or [message.left_chat_member]

    for chat_member in chat_members:
        if chat_member.is_bot:
            continue

        user_db = await get_one_user(session, tg_id=chat_member.id)
        chat_db = await get_one_chat(session, tg_id=message.chat.id)

        if not user_db:
            user_db = await create_user(session, chat_member, message.chat.type)
            await session.commit()
        if not chat_db:
            chat_db = await create_chat(session, chat_member.chat)
            await session.commit()

        local_chat_user = await get_one_local_chat_user(session, chat_id=chat_db.id, user_id=user_db.id)
        if not local_chat_user:
            local_chat_user = await create_local_chat_user(session, chat_db, user_db)
            await session.commit()

        active = message.content_type == ContentType.NEW_CHAT_MEMBERS

        await update_local_chat_user(
            session,
            LocalChatUser.id == local_chat_user.id,
            active=active
        )
        await session.commit()


async def set_local_chat_user_active_2(chat_member: ChatMemberUpdated, session: AsyncSession):
    user_db = await get_one_user(session, tg_id=chat_member.new_chat_member.user.id)
    chat_db = await get_one_chat(session, tg_id=chat_member.chat.id)

    if not user_db:
        user_db = await create_user(session, chat_member.new_chat_member.user, chat_member.chat.type)
        await session.commit()
    if not chat_db:
        chat_db = await create_chat(session, chat_member.chat)
        await session.commit()

    local_chat_user = await get_one_local_chat_user(session, chat_id=chat_db.id, user_id=user_db.id)
    if not local_chat_user:
        local_chat_user = await create_local_chat_user(session, chat_db, user_db)
        await session.commit()

    active = isinstance(chat_member.new_chat_member, ChatMemberMember)

    await update_local_chat_user(
        session,
        LocalChatUser.id == local_chat_user.id,
        active=active
    )
    await session.commit()


async def addition_bot(
        chat_member: ChatMemberUpdated,
        bot: Bot,
        i18n: TranslatorRunner,
        session: AsyncSession
):
    chat_db = await get_one_chat(session, tg_id=chat_member.chat.id)
    if not chat_db:
        chat_db = await create_chat(session, chat_member.chat)
        await session.commit()

    if chat_db.active is False:
        await update_chat(
            session,
            models.Chat.id == chat_db.id,
            active=True
        )
        await session.commit()

    await bot.send_message(chat_member.chat.id, i18n.welcome.group())


async def addendum_admin_bot(
        chat_member: ChatMemberUpdated,
        bot: Bot,
        i18n: TranslatorRunner,
        session: AsyncSession
):
    chat_db = await get_one_chat(session, tg_id=chat_member.chat.id)
    if not chat_db:
        chat_db = await create_chat(session, chat_member.chat)
        await session.commit()

    if not isinstance(chat_member.old_chat_member, ChatMemberMember):
        await bot.send_message(chat_member.chat.id, i18n.welcome.group())

    admins = await bot.get_chat_administrators(chat_member.chat.id)
    owner = await get_chat_owner(session, bot, chat_member.chat, admins)

    update_kwargs = {}

    for admin in admins:
        if admin.user.id == (await bot.me()).id:
            bot_rights = [getattr(admin, right) for right in BOT_RIGHTS]
            if all(bot_rights):
                update_kwargs["bot_admin"] = True
            break

    if chat_db.active is False:
        update_kwargs["active"] = True

    if owner:
        update_kwargs["owner"] = owner.id

        local_chat_user = await get_one_local_chat_user(session, chat_id=chat_db.id, user_id=owner.id)
        if not local_chat_user:
            await create_local_chat_user(session, chat_db, owner)

    await update_chat(
        session,
        models.Chat.id == chat_db.id,
        **update_kwargs
    )
    await session.commit()


async def deletion_admin_bot(chat_member: ChatMemberUpdated, bot: Bot, i18n: TranslatorRunner, session: AsyncSession):
    chat_db = await get_one_chat(session, tg_id=chat_member.chat.id)
    if not chat_db:
        chat_db = await create_chat(session, chat_member.chat)
        await session.commit()

    admins = await bot.get_chat_administrators(chat_member.chat.id)

    bot_admin = False
    for admin in admins:
        if admin.user.id == (await bot.me()).id:
            bot_rights = [getattr(admin, right) for right in BOT_RIGHTS]
            bot_admin = all(bot_rights)
            break

    if chat_db.bot_admin and bot_admin:
        return

    await update_chat(
        session,
        models.Chat.id == chat_db.id,
        bot_admin=bot_admin
    )
    await session.commit()


async def remove_bot_chat(chat_member: ChatMemberUpdated, session: AsyncSession):
    chat_db = await get_one_chat(session, tg_id=chat_member.chat.id)
    if not chat_db:
        chat_db = await create_chat(session, chat_member.chat)
        await session.commit()

    await update_chat(
        session,
        models.Chat.id == chat_db.id,
        active=False
    )
    await session.commit()


def setup(dp: Dispatcher):
    dp.my_chat_member.register(set_user_active, F.chat.type == "private")
    dp.message.register(
        set_local_chat_user_active,
        ContentTypesFilter(content_types=[ContentType.NEW_CHAT_MEMBERS, ContentType.LEFT_CHAT_MEMBER])
    )
    dp.chat_member.register(
        set_local_chat_user_active_2,
        or_f(
            ChatMemberUpdatedFilter(
                member_status_changed=IS_NOT_MEMBER >> IS_MEMBER
            ), ChatMemberUpdatedFilter(
                member_status_changed=IS_MEMBER >> IS_NOT_MEMBER
            )
        ),
        F.chat.type.in_({"group", "supergroup"}),
        F.new_chat_member.user.is_bot.is_(False)
    )
    dp.my_chat_member.register(
        addition_bot,
        ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> MEMBER),
        F.chat.type.in_({"group", "supergroup"})
    )
    dp.my_chat_member.register(
        addendum_admin_bot,
        ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> ADMINISTRATOR),
        F.chat.type.in_({"group", "supergroup"})
    )
    dp.my_chat_member.register(
        addendum_admin_bot,
        ChatMemberUpdatedFilter(member_status_changed=MEMBER >> ADMINISTRATOR),
        F.chat.type.in_({"group", "supergroup"})
    )
    dp.my_chat_member.register(
        deletion_admin_bot,
        ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR >> MEMBER),
        F.chat.type.in_({"group", "supergroup"})
    )
    dp.my_chat_member.register(
        deletion_admin_bot,
        ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR >> ADMINISTRATOR),
        F.chat.type.in_({"group", "supergroup"})
    )
    dp.my_chat_member.register(
        remove_bot_chat,
        ChatMemberUpdatedFilter(member_status_changed=LEAVE_TRANSITION),
        F.chat.type.in_({"group", "supergroup"})
    )
