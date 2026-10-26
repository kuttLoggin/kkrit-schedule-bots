from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, Chat
from fluentogram import TranslatorRunner

from app.utils.markup_constructor import InlineMarkupConstructor
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


class SelectHull(InlineMarkupConstructor):
    class CD(CallbackData, prefix="select_hull"):
        num: str

    def get(self, hulls: dict):
        actions = [
            {"text": hull["name"], "cd": self.CD(num=num)}
            for num, hull in sorted(list(hulls.items()), key=lambda item: item[1]["name"])
        ]
        schema = [1] * len(actions)
        return self.markup(actions, schema)


class SelectGroup(InlineMarkupConstructor):
    class CD(CallbackData, prefix="select_group"):
        group: str

    done_cb = "select_group_done"

    def get(self, i18n: TranslatorRunner, hull_num: str, groups: dict, selected: list):
        actions = [
            {
                "text": f"☑ {group}" if group in selected else group,
                "cd": self.CD(group=group)
            }
            for group in sorted(groups[hull_num])
        ]
        schema = list(map(len, splitting_lists(actions, 3)))
        if selected:
            actions.append({"text": i18n.settings.new.group.done_kb(), "cb": self.done_cb})
        else:
            actions.append({"text": i18n.settings.new.group.not_group(), "cb": self.done_cb})
        schema.append(1)
        return self.markup(actions, schema)


class SettingSchedule(InlineMarkupConstructor):
    class CD(CallbackData, prefix="setting_schedule"):
        act: str

    def get(self, i18n: TranslatorRunner, active: bool, pin_msg_func: bool):
        actions = [
            {"text": i18n.settings.change_btn(), "cb": self.CD(act="change_data")},
            {"text": i18n.settings.pin_msg_btn(active=int(pin_msg_func)), "cb": self.CD(act="change_pin_msg_func")},
            {"text": i18n.settings.active_btn(active=int(active)), "cb": self.CD(act="change_active")}
        ]
        schema = [1] * len(actions)
        return self.markup(actions, schema)


class Start(InlineMarkupConstructor):

    def get(self, i18n: TranslatorRunner, bot_me: Chat):
        actions = [
            {
                "text": i18n.welcome.btn.invite_in_chat(),
                "url": f"https://t.me/{bot_me.username}?startgroup=group"
            }
        ]
        schema = [1]
        return self.markup(actions, schema)


class ScheduleUrl(InlineMarkupConstructor):

    def get(self, text: str, url: str):
        actions = [{"text": text, "url": url}]
        schema = [1]
        return self.markup(actions, schema)


class CancelSendReport(InlineMarkupConstructor):
    cb = "cancel_send_report"

    def get(self, i18n: TranslatorRunner):
        actions = [{"text": i18n.report.cancel_send_report(), "cb": self.cb}]
        schema = [1]
        return self.markup(actions, schema)
