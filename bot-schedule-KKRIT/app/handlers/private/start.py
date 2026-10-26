from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message
from fluentogram import TranslatorRunner

from app.keyboards.private.inline import Start
from app.utils.tools import get_mention


async def get_start_message(m: Message, bot: Bot, i18n: TranslatorRunner):
    await m.answer(
        i18n.welcome(
            user_name=get_mention(m.from_user.id, m.from_user.full_name)
        ),
        reply_markup=Start().get(i18n, await bot.me())
    )


def setup(router: Router):
    router.message.register(get_start_message, CommandStart())
