from aiogram import Dispatcher, F
from aiogram.types import ChatMemberUpdated
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import models
from app.infrastructure.database.functions.users import get_one_user, update_user


async def set_user_active(my_chat_member: ChatMemberUpdated, session: AsyncSession):
    user = await get_one_user(session, tg_id=my_chat_member.from_user.id)

    if user:
        await update_user(
            session,
            models.User.id == user.id, active=my_chat_member.new_chat_member.status == "member"
        )
        await session.commit()


def setup(dp: Dispatcher):
    dp.my_chat_member.register(set_user_active, F.chat.type == "private")
