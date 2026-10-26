from typing import Callable, Any, Awaitable, Optional, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Chat, User, Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import models
from app.infrastructure.database.functions.users import get_one_user, update_user, create_user


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
