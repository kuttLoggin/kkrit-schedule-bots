from aiogram import Dispatcher

from app.handlers import admins, general, private, errors, updates


def setup_all_handlers(dp: Dispatcher):
    for module in (admins, general, private, errors, updates):
        module.setup(dp)
