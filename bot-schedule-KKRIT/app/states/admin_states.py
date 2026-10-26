from aiogram.filters.state import StatesGroup, State


class AnswerAdmin(StatesGroup):
    ANSWER = State()


class BroadcastAdmin(StatesGroup):
    SEND_MESSAGE = State()
    START = State()
