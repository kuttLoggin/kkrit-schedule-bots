import re
from typing import List, Tuple, Dict

from app.config import Config
from app.utils.cloud_api_yandex import get_public_resource
from app.utils.parser_schedule.types import Tape


def get_group_name(string: str):
    if not isinstance(string, str):
        return None

    match = re.match(
        r"(\d?[А-яЕЁ]+-\d.\d\dК?)",
        string.upper().strip(),
        re.RegexFlag.IGNORECASE
    )

    if match:
        return match.group()


def check_empty_text(string: str):
    return not re.search(
        r"[А-яЕЁ\d]",
        string,
        re.RegexFlag.MULTILINE | re.RegexFlag.IGNORECASE
    )


def get_subgroups(string: str):
    if not isinstance(string, str):
        return None

    match = re.search(
        r"(1 П/ГР.+2 П/ГР)",
        string.strip(),
        re.RegexFlag.MULTILINE | re.RegexFlag.IGNORECASE
    )
    if not match:
        match = re.search(
            r"(2 П/ГР.+1 П/ГР)",
            string.strip(),
            re.RegexFlag.MULTILINE | re.RegexFlag.IGNORECASE
        )

    return match.group() if match else None


def get_teachers(string: str):
    if not isinstance(string, str):
        return None, None

    match: list[tuple[str, str, str], tuple[str, str, str]] = re.findall(
        r"([А-Я][а-я]+\.*)(?=(\s+[А-Я][.\s]+[А-Я]\.?\b)|(\s+[А-Я]\.?\b))",
        string.strip(),
        re.RegexFlag.MULTILINE
    )

    result: list[str] = []

    for text in match:
        name, initials = text[0].capitalize(), text[1] + text[2]
        initials = initials.strip()
        if len(initials.replace(" ", "").replace(".", "")) > 1:
            initials = f"{initials[0]}.{initials[1:].replace(' ', '').replace('.', '')}"
        if initials[-1] != ".":
            initials += "."

        result.append(" ".join([name.strip(". "), initials]))

    return result or None, match or None


def get_class_rooms(string: str):
    if not isinstance(string, str):
        return None

    match = re.findall(
        r"(\d\d\d)",
        string.strip(),
        re.RegexFlag.MULTILINE
    )

    if match and sum(map(len, match)) < len(string.strip()) / 2:
        match = None

    if match:
        match = [int(kb) for kb in match]
    else:
        string = string.strip()
        if string.lower() != "до":
            match = [string]

    return match or None


def check_split_tables(groups_all_tables: Dict[str, Tuple[int, int, int]]):
    unique_row_indexes = {}
    for indexes in groups_all_tables.values():
        if indexes[0] != 0:
            unique_row_indexes[indexes[0]] = unique_row_indexes.get(indexes[0], 0) + 1

    splitting_tables = False
    for count in unique_row_indexes.values():
        if count >= 5:
            splitting_tables = True
            break

    if splitting_tables is False:
        return

    unique_indexes = []
    for indexes in groups_all_tables.values():
        unique = (indexes[2], indexes[0])
        if indexes[0] != 0 and unique not in unique_indexes:
            unique_indexes.append(unique)

    return unique_indexes


def split_tables(tables: List[List[List[Tape]]], unique_indexes: List[Tuple[int, int]]):
    new_tables = []

    for table_index, table in enumerate(tables):
        current_table = []
        for row_index, row in enumerate(table):
            if (table_index, row_index) in unique_indexes:
                new_tables.append(current_table)
                current_table = []

            current_table.append(row)

        new_tables.append(current_table)

    return new_tables


async def collect_hulls():
    resource = await get_public_resource(Config.KKRIT_DISK, sort="created")
    hulls = {}
    for i, item in enumerate(resource["_embedded"]["items"]):
        if item["type"] != "dir":
            continue

        hull = {"name": item["name"], "path": item["path"]}
        hulls[str(i)] = hull

    return hulls
