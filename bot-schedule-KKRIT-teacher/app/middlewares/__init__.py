from aiogram import Dispatcher

from .acl import ACLMiddleware
from .clocks import ClocksMiddleware
from .i18n import I18nMiddleware
from .throttling import ThrottlingMiddleware
from .db_pool import DBPoolMiddleware


def setup(dp: Dispatcher, session_pool):
    dp.message.middleware(ThrottlingMiddleware())
    # dp.callback_query.middlewares(ThrottlingMiddleware())

    dp.message.outer_middleware(ClocksMiddleware())
    dp.callback_query.outer_middleware(ClocksMiddleware())

    dp.update.outer_middleware(DBPoolMiddleware(session_pool))

    dp.message.outer_middleware(ACLMiddleware())
    dp.callback_query.outer_middleware(ACLMiddleware())
    dp.errors.outer_middleware(ACLMiddleware())

    dp.message.outer_middleware.register(I18nMiddleware())
    dp.callback_query.outer_middleware.register(I18nMiddleware())
    dp.my_chat_member.outer_middleware.register(I18nMiddleware())
    dp.errors.outer_middleware.register(I18nMiddleware())
