from datetime import datetime, timedelta, date as _date

from aiogram import html


def splitting_lists(list_: list, count: int) -> list:
    """
        Example:
            splitting_lists([1, 2, 3], 2) -> [[1, 2], [3]]
    """

    return [list_[i:i + count] for i in range(0, len(list_), count)]


def text_(*args) -> str:
    """
        Example:
            text_("Test", "string") -> "Test\\\\nstring"
    """

    return "\n".join(args)


def get_mention(user_id: int, full_name: str):
    return f"<a href='tg://user?id={user_id}'>{html.quote(full_name)}</a>"


WEEKDAYS_FUTURE = {
    0: "понедельник",
    1: "вторник",
    2: "среду",
    3: "четверг",
    4: "пятницу",
    5: "субботу",
    6: "воскресенье"
}


def natural_future_day(dt: datetime):
    if not isinstance(dt, _date):
        dt = dt.date()

    weekday = WEEKDAYS_FUTURE[dt.weekday()]
    string = f"{weekday} ({dt:%d.%m})"

    return string


def string_timedelta(td: timedelta, lang: str = "ru"):
    if lang == "ru":
        info_tuple = ('{} д.', '{} час.', '{} мин.', '{} сек.')
    elif lang == "en":
        info_tuple = ('{} d.', '{} h.', '{} m.', '{} s.')
    else:
        raise AttributeError(f"Language '{lang}' is not found")

    return ' '.join([
        pattern.format(value) for value, pattern in zip(
            (td.days, td.seconds // 3600, (td.seconds // 60) % 60, td.seconds % 60),
            info_tuple,
        )
        if value
    ])
