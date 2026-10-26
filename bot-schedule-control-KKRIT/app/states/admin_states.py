from aiogram.filters.state import StatesGroup, State


class BroadcastAdmin(StatesGroup):
    SEND_MESSAGE = State()
    START = State()


class UpdateCollectDataGroupsAdmin(StatesGroup):
    SEND_JSON = State()


class UpdateCollectDataHullsAdmin(StatesGroup):
    SEND_JSON = State()


class GetGroupsOnSchedule(StatesGroup):
    SEND_FILE = State()
    SELECT_PARSER = State()
