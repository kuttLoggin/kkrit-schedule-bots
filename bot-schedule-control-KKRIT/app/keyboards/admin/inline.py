from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup

from app.utils.markup_constructor import InlineMarkupConstructor
from app.utils.parser_schedule import CREATORS_SCHEDULE, SCHEDULE_RULES
from app.utils.tools import splitting_lists


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
    cb = "H_cancel_L"

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
            {"text": "👤 Юзеры", "cb": self.CD(group="user")}
        ]
        schema = [1, 2]
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


class IgnoreFile(InlineMarkupConstructor):
    class CD(CallbackData, prefix="ignore_file"):
        record_id: str

    def get(self, record_id: int, solution: bool):
        actions = [
            {"text": "✅ Перестать игнорировать", "cb": self.CD(record_id=record_id)}
            if solution else
            {"text": "✖ Игнорировать", "cb": self.CD(record_id=record_id)}
        ]
        schema = [1]
        return self.markup(actions, schema)


class ConvertFilePDFToXLSX(InlineMarkupConstructor):
    class CD(CallbackData, prefix="convert_file_pdf_to_xlsx"):
        record_id: str

    def get(self, record_id: int):
        actions = [
            {"text": "📁 Конвертировать", "cb": self.CD(record_id=record_id)}
        ]
        schema = [1]
        return self.markup(actions, schema)


class SelectParserGroupsOnSchedule(InlineMarkupConstructor):
    class CD(CallbackData, prefix="st_parser_groups_on_sc"):
        parser: str

    def get(self):
        actions = [
            {"text": name, "cb": self.CD(parser=name)}
            for name in CREATORS_SCHEDULE
        ]
        schema = list(map(len, splitting_lists(list(CREATORS_SCHEDULE), 2)))
        return self.markup(actions, schema)

    def selected(self, parser: str):
        actions = [{"text": parser, "cb": " "}]
        schema = [1]
        return self.markup(actions, schema)


class ScheduleCatcher:
    class Cancel(InlineMarkupConstructor):
        class CD(CallbackData, prefix="sc_cat_cancel"): ...

        def get(self):
            actions = [{"text": "❌ Отмена", "cb": self.CD()}]
            schema = [1]
            return self.markup(actions, schema)

        def click(self):
            actions = [{"text": "❌ Отменено", "cb": " "}]
            schema = [1]
            return self.markup(actions, schema)

    class Question(InlineMarkupConstructor):
        class CD(CallbackData, prefix="sc_cat_main"): ...

        def get(self):
            actions = [{"text": "❔ Это расписание", "cb": self.CD()}]
            schema = [1]
            return self.markup(actions, schema)

    class SelectHull(InlineMarkupConstructor):
        class CD(CallbackData, prefix="sc_cat_select_hull"):
            hull: str

        def get(self, hulls: dict):
            actions = [
                {"text": hull["name"], "cb": self.CD(hull=num)}
                for num, hull in hulls.items()
            ]
            schema = [1] * len(hulls) + [1]
            actions.append({"text": "❌", "cb": ScheduleCatcher.Cancel.CD()})
            return self.markup(actions, schema)

    class SelectParser(InlineMarkupConstructor):
        class CD(CallbackData, prefix="sc_cat_select_parser"):
            parser: str

        def get(self):
            actions = [
                {"text": name, "cb": self.CD(parser=name)}
                for name in CREATORS_SCHEDULE
            ]
            schema = list(map(len, splitting_lists(list(CREATORS_SCHEDULE), 2))) + [1]
            actions.append({"text": "❌", "cb": ScheduleCatcher.Cancel.CD()})
            return self.markup(actions, schema)

    class SelectRule(InlineMarkupConstructor):
        class CD(CallbackData, prefix="sc_cat_select_rule"):
            rule: str

        def get(self, parser: str):
            actions = [
                {"text": name, "cb": self.CD(rule=name)}
                for name in SCHEDULE_RULES[parser]
            ]
            schema = list(map(len, splitting_lists(list(SCHEDULE_RULES[parser]), 2))) + [2]
            actions.append({"text": "❎", "cb": self.CD(rule="-")})
            actions.append({"text": "❌", "cb": ScheduleCatcher.Cancel.CD()})
            return self.markup(actions, schema)

    class LetsGo(InlineMarkupConstructor):
        class CD(CallbackData, prefix="sc_cat_lets_go"): ...

        def get(self):
            actions = [
                {"text": "✅", "cb": self.CD()},
                {"text": "❌", "cb": ScheduleCatcher.Cancel.CD()}
            ]
            schema = [2]
            return self.markup(actions, schema)

        def click(self):
            actions = [{"text": "✅", "cb": " "}]
            schema = [1]
            return self.markup(actions, schema)
