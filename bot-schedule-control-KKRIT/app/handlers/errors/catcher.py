import logging

from aiogram import Dispatcher
from aiogram.types.error_event import ErrorEvent


async def errors_handler(event: ErrorEvent):
    error = f"Error: {type(event.exception)}: {event.exception}\n\nUpdate: {event.update}"
    logging.exception(error)


def setup(dp: Dispatcher):
    dp.errors.register(errors_handler)
