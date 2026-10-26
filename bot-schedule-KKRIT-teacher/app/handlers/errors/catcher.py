import logging

from aiogram import Dispatcher
from aiogram.types import Update, Message


async def errors_handler(update: Update, exception):
    error = f"Error: {type(exception)}: {exception}\n\nUpdate: {update}"
    logging.exception(error)

    if update.callback_query or update.message:
        obj = update.message or update.callback_query

        # await obj.answer(i18n.err.unknown())


def setup(dp: Dispatcher):
    dp.errors.register(errors_handler)
