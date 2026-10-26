from aiogram import Dispatcher

from app.handlers import admins, private, groups, updates, errors


def setup_all_handlers(dp: Dispatcher):
    for module in (admins, private, groups, updates, errors):
        module.setup(dp)
