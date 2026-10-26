from pprint import pprint
from typing import List, Dict, Optional, Any

from app.utils.parser_schedule.schedule_excel_v2 import Tape, parse_schedule
from app.utils.parser_schedule.utils import (
    get_group_name, get_teachers, check_empty_text,
    check_split_tables, split_tables, get_class_rooms
)

NOT_REMOTE_FILL_RGB = "00000000"


def get_groups(table: List[List[Tape]]):
    groups = {}
    for index, tape in enumerate(table[0]):
        if not tape.text:
            continue

        group_name = get_group_name(tape.text)
        if not group_name:
            continue

        groups[group_name] = index

    return groups


def get_groups_all_tables(tables: List[List[List[Tape]]]):
    groups = {}
    for num_table, table in enumerate(tables):
        for row_index, row in enumerate(table):
            for tape_index, tape in enumerate(row):
                if not tape.text:
                    continue

                group_name = get_group_name(tape.text)
                if not group_name:
                    continue

                groups[group_name] = (row_index, tape_index, num_table)

    return groups


def check_remote(tape: Tape, class_room: Optional[Tape]):
    if class_room:
        if class_room.text and "до" in class_room.text.lower().split():
            return True

        if class_room.fill != NOT_REMOTE_FILL_RGB:
            return True

    if tape.fill != NOT_REMOTE_FILL_RGB:
        return True

    if tape.text:
        text = tape.text.lower().split()
        if "до" in text:
            return True

    return False


def delete_remoted_text(text: str):
    split_text = text.lower().split()
    result_text = text.split()

    try:
        remoted_index = split_text.index("до")
    except ValueError:
        pass
    else:
        # Удаляем "ДО - ", который по сути находится в начале текста
        del result_text[remoted_index]
        if result_text[0] in ("-", "–", "—"):
            del result_text[0]
    finally:
        text = " ".join(result_text)

    return text


def get_schedule(table: List[List[Tape]], groups: Dict[str, int]):
    schedule = {}
    for group_name, group_index in groups.items():
        for index_row in range(1, len(table)):
            tape = table[index_row][group_index]

            text = tape.text if tape.text and not check_empty_text(tape.text) else None

            try:
                class_room_tape = table[index_row][group_index + 1]
            except IndexError:
                class_room_tape = None

            remoted = check_remote(tape, class_room_tape)
            if remoted and text:
                text = delete_remoted_text(text)

            teachers, teachers_original = get_teachers(text)

            # for teacher_orig in teacher_originals or []:
            #     teacher_orig = "".join(teacher_orig)
            #     text = text.replace(teacher_orig, "").strip(". ")

            class_rooms = None
            if class_room_tape and class_room_tape.text:
                class_rooms = get_class_rooms(class_room_tape.text)

            group_schedule = schedule.get(group_name, {})
            group_schedule[str(index_row)] = {
                "original_text": tape.text,
                "title": text,
                "teachers": teachers,
                "class_rooms": class_rooms,
                "remoted": remoted
            }
            schedule[group_name] = group_schedule

    return schedule


def create_schedule(tables: List[List[List[Tape]]]):
    # Проверка на то что в таблицах есть таблицы(ы) которые были соединены
    groups_all_tables = get_groups_all_tables(tables)
    if unique_indexes := check_split_tables(groups_all_tables):
        tables = split_tables(tables, unique_indexes)

    groups = []
    schedule = {}

    for table in tables:
        table_groups = get_groups(table)
        table_schedule = get_schedule(table, table_groups)

        groups.extend(table_groups.keys())
        schedule.update(table_schedule)

    return schedule, groups


def enforce_rule_monday(schedule: Dict[str, Dict[str, Dict[str, Any]]]):
    correct_schedule = {group: {} for group in schedule.keys()}
    for group, tapes in schedule.items():
        correct_schedule[group]["-"] = tapes["1"]
        correct_schedule[group]["-"] = tapes["2"]

        for num, tape in tapes.items():
            if num in ("1", "2"):
                continue

            correct_schedule[group][str(int(num) - 2)] = tape

    return correct_schedule


def enforce_rule_thursday(schedule: Dict[str, Dict[str, Dict[str, Any]]]):
    correct_schedule = {group: {} for group in schedule.keys()}
    for group, tapes in schedule.items():
        correct_schedule[group]["-"] = tapes["1"]

        for num, tape in tapes.items():
            if num == "1":
                continue

            correct_schedule[group][str(int(num) - 1)] = tape

    return correct_schedule


if __name__ == "__main__":
    _tables = parse_schedule("02.10.2023г.xlsx")
    _schedule, _groups = create_schedule(_tables)
    print(_groups)
    pprint(_schedule)
