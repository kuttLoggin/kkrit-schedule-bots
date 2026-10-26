from typing import Callable, Any, Awaitable, Optional, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Chat, User, Message, CallbackQuery, ContentType
from asyncpg import UniqueViolationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import models
from app.infrastructure.database.functions.chat_schedules import update_chat_schedule
from app.infrastructure.database.functions.chats import get_one_chat, update_chat, create_chat, delete_chat
from app.infrastructure.database.functions.local_chat_users import get_one_local_chat_user, create_local_chat_user
from app.infrastructure.database.functions.users import get_one_user, update_user, create_user
from app.infrastructure.database.models import LocalChatUser


def check_new_info(checked_instance, instance, checked_attributes: list, attributes: list):
    new_attrs = {}

    for check_attr, attr in zip(checked_attributes, attributes):
        test_attr = getattr(checked_instance, check_attr)
        if test_attr != getattr(instance, attr):
            new_attrs[attr] = test_attr

    return new_attrs


class ACLMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        user: Optional[User] = data.get("event_from_user")
        chat: Optional[Chat] = data.get("event_chat")

        if user.username in ("GroupAnonymousBot", "Channel_Bot"):
            return

        if user and not user.is_bot:
            user_db = await self.get_user(data)
            data.update(user_db=user_db)

        if chat and chat.type in ("group", "supergroup"):
            chat_db = await self.get_chat(event, data)
            data.update(chat_db=chat_db)

        if data.get("user_db") and data.get("chat_db"):
            local_chat_user = await self.get_local_chat_user(data)
            data.update(local_chat_user=local_chat_user)

        return await handler(event, data)

    @staticmethod
    async def get_user(data: Dict[str, Any]) -> Optional[User]:
        session: AsyncSession = data["session"]
        user: User = data.get("event_from_user")
        chat: Optional[Chat] = data.get("event_chat")

        if not (user_db := await get_one_user(session, tg_id=user.id)):
            await create_user(session, user, chat.type)
            await session.commit()
            return await get_one_user(session, tg_id=user.id)

        check = check_new_info(
            user, user_db,
            ["first_name", "last_name", "username", "language_code"],
            ["first_name", "last_name", "username", "language"]
        )

        if chat and chat.type == "private" and user_db.active is False:
            check["active"] = True

        if check:
            await update_user(session, models.User.tg_id == user.id, **check)
            await session.commit()

        return user_db

    @staticmethod
    async def get_chat(event: Union[Message, CallbackQuery], data: Dict[str, Any]) -> Optional[Chat]:
        session: AsyncSession = data["session"]
        chat: Chat = data.get("event_chat")

        if isinstance(event, Message) and event.content_type == ContentType.MIGRATE_TO_CHAT_ID:
            new_chat_id = event.migrate_to_chat_id

            try:
                await update_chat(
                    session,
                    models.Chat.tg_id == chat.id,
                    tg_id=new_chat_id, group_type=chat.type
                )
            except UniqueViolationError:
                await delete_chat(session, models.Chat.tg_id == new_chat_id)

                await update_chat(
                    session,
                    models.Chat.tg_id == chat.id,
                    tg_id=new_chat_id, group_type=chat.type
                )

            await update_chat_schedule(
                session,
                models.ChatSchedule.tg_id == chat.id,
                tg_id=new_chat_id
            )
            await session.commit()

            chat.id = new_chat_id

        if not (chat_db := await get_one_chat(session, tg_id=chat.id)):
            await create_chat(session, chat)
            await session.commit()
            return await get_one_chat(session, tg_id=chat.id)

        check = check_new_info(
            chat, chat_db,
            ["title", "username"], ["title", "username"]
        )

        if check:
            await update_chat(session, models.Chat.tg_id == chat.id, **check)
            await session.commit()

        return chat_db

    @staticmethod
    async def get_local_chat_user(data: Dict[str, Any]) -> Optional[LocalChatUser]:
        session: AsyncSession = data["session"]
        chat_db: models.Chat = data.get("chat_db")
        user_db: models.User = data.get("user_db")

        local_chat_user = await get_one_local_chat_user(session, chat_id=chat_db.id, user_id=user_db.id)
        if not local_chat_user:
            await create_local_chat_user(session, chat_db, user_db)
            await session.commit()

            return await get_one_local_chat_user(session, chat_id=chat_db.id, user_id=user_db.id)

        return local_chat_user
