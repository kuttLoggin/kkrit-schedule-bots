from aiogram import Dispatcher, Router

from . import settings, call_empty_answer


def setup(dp: Dispatcher):
    router = Router()
    dp.include_router(router)

    for module in (settings, call_empty_answer):
        module.setup(router)
