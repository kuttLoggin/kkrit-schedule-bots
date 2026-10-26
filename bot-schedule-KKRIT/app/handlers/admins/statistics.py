from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import true
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.functions.chat_schedules import get_count_chat_schedules
from app.infrastructure.database.functions.chats import get_count_chats
from app.infrastructure.database.models import User, Chat, ChatSchedule
from app.infrastructure.database.functions.users import get_count_users


async def general_stats(m: Message, session: AsyncSession):
    all_users = await get_count_users(session)
    active_users = await get_count_users(session, User.active == true())

    all_chats = await get_count_chats(session)
    active_chats = await get_count_chats(session, Chat.active == true())

    all_chat_schedule = await get_count_chat_schedules(session)
    active_chat_schedule = await get_count_chat_schedules(session, ChatSchedule.active == true())

    users_chat_schedule = await get_count_chat_schedules(session, ChatSchedule.chat_type == "user")
    chats_chat_schedule = await get_count_chat_schedules(session, ChatSchedule.chat_type == "chat")

    active_users_chat_schedule = await get_count_chat_schedules(
        session,
        ChatSchedule.chat_type == "user",
        ChatSchedule.active == true()
    )
    active_chats_chat_schedule = await get_count_chat_schedules(
        session,
        ChatSchedule.chat_type == "chat",
        ChatSchedule.active == true()
    )

    text = (
        "🌐 <b><i>Общая статистика</i></b>",
        f"👤 <b>Юзеры</b> [всего | актив]: {all_users} | {active_users}",
        f"👥 <b>Чаты</b> [всего | актив]: {all_chats} | {active_chats}",
        "",
        f"📝 <b>Получают расписание</b> [всего | актив]: {all_chat_schedule} | {active_chat_schedule}",
        f"┣ из них <b>юзеры</b> [всего | актив]: {users_chat_schedule} | {active_users_chat_schedule}",
        f"┗ из них <b>чаты</b> [всего | актив]: {chats_chat_schedule} | {active_chats_chat_schedule}"
    )
    await m.answer("\n".join(text))


def setup(router: Router):
    router.message.register(general_stats, Command(commands="statistics"))
