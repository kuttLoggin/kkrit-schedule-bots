from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.keyboards.admin.inline import CancelKb


async def cancel_handler(c: CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await c.message.edit_text("❌ Вы отменили")


def setup(router: Router):
    router.callback_query.register(cancel_handler, F.data == CancelKb.cb)
