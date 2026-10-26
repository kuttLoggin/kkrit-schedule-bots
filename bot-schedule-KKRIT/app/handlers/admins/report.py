import logging
from contextlib import suppress

from aiogram import Router, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.keyboards.admin.inline import AnswerReport, CancelKb


async def pre_answer_report(c: CallbackQuery, callback_data: AnswerReport.CD, state: FSMContext):
    user_id = int(callback_data.user_id)

    await state.set_state("answer_report")
    await state.update_data(user_id=user_id)

    await c.answer()
    msg = await c.message.reply("✉ Напишите ответ на репорт.", reply_markup=CancelKb().get())

    await state.update_data(cancel_msg_id=msg.message_id)


async def answer_report(m: Message, bot: Bot, state: FSMContext):
    data = await state.get_data()

    try:
        user_id = data["user_id"]

        await bot.send_message(user_id, "📍 Сообщение от администратора")
        await m.send_copy(user_id)
    except TelegramAPIError as err:
        logging.warning(f"Fail send answer report - {err}")

        await m.answer(
            "❗ С сообщением что-то не так\n"
            "❓ Попробуйте ещё раз отправить сообщение."
        )
    except Exception as err:
        logging.warning(f"Error send answer report - {err}")

        await m.answer(
            "❗ Не известная ошибка\n"
            "❓ Попробуйте ещё раз отправить сообщение."
        )
    else:
        with suppress(TelegramAPIError):
            await bot.edit_message_reply_markup(m.chat.id, data["cancel_msg_id"])

        await state.clear()
        await m.answer("✅ Ответ на репорт, отправлен!")


def setup(router: Router):
    router.callback_query.register(pre_answer_report, AnswerReport.CD.filter())
    router.message.register(answer_report, StateFilter(state="answer_report"))
