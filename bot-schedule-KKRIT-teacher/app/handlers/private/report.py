import logging

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart, ContentTypesFilter, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ContentType, CallbackQuery
from fluentogram import TranslatorRunner

from app.config import Config
from app.keyboards.admin.inline import AnswerReport
from app.keyboards.private.inline import CancelSendReport
from app.utils.tools import get_mention


async def start_report(m: Message, state: FSMContext, i18n: TranslatorRunner):
    # await state.set_state("wait_report_msg")
    # await m.answer(i18n.report.start(), reply_markup=CancelSendReport().get(i18n))

    await m.answer(i18n.report.start(admin_link=Config.REPORT_ADMIN_LINK), disable_web_page_preview=True)


async def cancel_send_report(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.delete_reply_markup()


async def send_report(m: Message, bot: Bot, state: FSMContext, i18n: TranslatorRunner):
    await state.clear()

    try:
        await bot.send_message(
            Config.REPORT_CHAT_ID,
            i18n.report.admin.info(
                user_name=get_mention(m.from_user.id, m.from_user.full_name),
                user_tg_id=str(m.from_user.id)
            ),
            reply_markup=AnswerReport().get(m.from_user.id),
            disable_web_page_preview=True
        )
        await m.send_copy(Config.REPORT_CHAT_ID)
    except TelegramAPIError as err:
        logging.error(err)

    await m.answer(i18n.report.sented())


def setup(router: Router):
    router.message.register(start_report, Command(commands="report"))
    router.message.register(start_report, CommandStart(deep_link=True, command_magic=F.args == "report"))
    # router.callback_query.register(cancel_send_report, StateFilter(state="wait_report_msg"), F.data == CancelSendReport.cb)
    # router.message.register(
    #     send_report,
    #     StateFilter(state="wait_report_msg"),
    #     ContentTypesFilter(content_types=ContentType.ANY)
    # )
