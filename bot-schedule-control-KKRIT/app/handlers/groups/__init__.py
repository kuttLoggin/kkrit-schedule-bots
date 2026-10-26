from aiogram import Dispatcher, Router, F

from app.config import Config

from app.handlers.groups import collect_data, add_schedule, ignore_file, converter


def setup(dp: Dispatcher):
    router = Router()
    dp.include_router(router)

    router.message.filter(F.chat.type.in_({"group", "supergroup"}), F.chat.id == Config.GROUP_ID)
    router.callback_query.filter(F.message.chat.type.in_({"group", "supergroup"}), F.message.chat.id == Config.GROUP_ID)

    for module in (collect_data, add_schedule, ignore_file, converter):
        module.setup(router)
