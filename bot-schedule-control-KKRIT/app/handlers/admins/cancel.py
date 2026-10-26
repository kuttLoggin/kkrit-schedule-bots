from typing import Union

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.keyboards.admin.inline import CancelKb


async def cancel_handler(obj: Union[Message, CallbackQuery], state: FSMContext):
    await state.clear()

    if isinstance(obj, Message):
        await obj.answer("❌ Вы отменили")
    else:
        await obj.message.edit_text("❌ Вы отменили")


def setup(router: Router):
    router.message.register(cancel_handler, F.text == "/cancel")
    router.callback_query.register(cancel_handler, F.data == CancelKb.cb)
