from typing import Union

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup

from app.utils.markup_constructor import InlineMarkupConstructor


class ExampleMarkup(InlineMarkupConstructor):
    class CD(CallbackData, prefix="test"):
        number: str

    def get(self) -> InlineKeyboardMarkup:
        schema = [3, 2]
        actions = [
            {"text": "1", "callback_data": self.CD(number="1")},
            {"text": "2", "callback_data": self.CD(number="2").pack()},
            {"text": "3", "callback_data": "3"},
            {"text": "4", "callback_data": self.CD(number="4").pack()},
            {"text": "6", "callback_data": "6"},
        ]
        return self.markup(actions, schema)


class CancelKb(InlineMarkupConstructor):
    cb = "adm_cancel"

    def get(self) -> InlineKeyboardMarkup:
        schema = [1]
        actions = [
            {"text": "❌ Отмена", "cb": self.cb},
        ]
        return self.markup(actions, schema)


class SelectBroadcastGroup(InlineMarkupConstructor):
    class CD(CallbackData, prefix="select_bc_group"):
        group: str

    def get(self):
        actions = [
            {"text": "🌐 Все", "cb": self.CD(group="user,chat")},
            {"text": "👤 Юзеры", "cb": self.CD(group="user")},
            {"text": "💭 Чаты", "cb": self.CD(group="chat")},
            {"text": "📅🌐 Расписание: Все", "cb": self.CD(group="sd_user,sd_chat")},
            {"text": "📅👤 Юзеры", "cb": self.CD(group="sd_user")},
            {"text": "📅💭 Чаты", "cb": self.CD(group="sd_chat")},
        ]
        schema = [1, 2, 1, 2]
        return self.markup(actions, schema)


class StartBroadcast(InlineMarkupConstructor):
    cb = "start_broadcast"

    def get(self):
        actions = [
            {"text": "✅ Начать рассылку", "cb": self.cb},
            {"text": "❌ Отмена", "cb": CancelKb.cb}
        ]
        schema = [1, 1]
        return self.markup(actions, schema)


class CancelBroadcast(InlineMarkupConstructor):
    cb = "cancel_broadcast"

    def get(self):
        actions = [{"text": "❌ Закончить рассылку", "cb": self.cb}]
        schema = [1]
        return self.markup(actions, schema)


class AnswerReport(InlineMarkupConstructor):
    class CD(CallbackData, prefix="answer_report"):
        user_id: str

    def get(self, user_id: Union[int, str]):
        actions = [
            {"text": "💭 Ответить", "cb": self.CD(user_id=user_id)}
        ]
        schema = [1]
        return self.markup(actions, schema)
