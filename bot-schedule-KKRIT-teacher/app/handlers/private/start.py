from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from fluentogram import TranslatorRunner

from app.utils.tools import get_mention


async def get_start_message(m: Message, i18n: TranslatorRunner):
    await m.answer(
        i18n.welcome(
            user_name=get_mention(m.from_user.id, m.from_user.full_name)
        )
    )


def setup(router: Router):
    router.message.register(get_start_message, CommandStart())
