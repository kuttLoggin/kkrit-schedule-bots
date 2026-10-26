from aiogram import Router
from aiogram.filters import Text
from aiogram.types import CallbackQuery


async def call_empty_answer(c: CallbackQuery):
    await c.answer(cache_time=30)


def setup(router: Router):
    router.callback_query.register(call_empty_answer, Text(text=" "))
