from aiogram import Dispatcher, Router

from . import settings


def setup(dp: Dispatcher):
    router = Router()
    dp.include_router(router)

    for module in (settings, ):
        module.setup(router)
