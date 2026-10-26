from aiogram import Router, Dispatcher

from app.filters.admin import AdminFilter

from . import cancel, statistics, broadcast, power


def setup(dp: Dispatcher):
    router = Router()
    dp.include_router(router)

    router.message.filter(AdminFilter())
    router.callback_query.filter(AdminFilter())

    for module in (cancel, statistics, broadcast, power):
        module.setup(router)
