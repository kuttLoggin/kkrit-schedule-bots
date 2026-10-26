from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.functions.check_schedules import get_one_check_schedule, update_check_schedule
from app.infrastructure.database.models import CheckSchedule
from app.keyboards.admin.inline import IgnoreFile


async def ignore_file(c: CallbackQuery, callback_data: IgnoreFile.CD, session: AsyncSession):
    record_id = int(callback_data.record_id)
    check_schedule = await get_one_check_schedule(session, id=record_id)

    ignore = not check_schedule.ignore

    await update_check_schedule(session, CheckSchedule.id == record_id, ignore=ignore)
    await session.commit()

    await c.answer()
    await c.message.edit_reply_markup(IgnoreFile().get(record_id, ignore))


def setup(router: Router):
    router.callback_query.register(ignore_file, IgnoreFile.CD.filter())
