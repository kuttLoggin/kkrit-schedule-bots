import re
import os
from pprint import pprint
from typing import Tuple, List

from docx import Document
from docx.document import Document as FileDocument
from docx.oxml import CT_Tc, CT_TcPr, CT_Tbl, CT_Row, CT_P, CT_R, CT_Text
from docx.table import _Cell, _Rows
from lxml.etree import _Element

from app.utils.sync import run_async

STANDARD_COLOR = "ffffff"
GROUP_COLOR = "ffff00"
REMOTED_COLOR = "e0e0e0"

FILL_KEY = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fill"


def get_shd_cell(tc: CT_Tc):
    for tcPr in tc:
        if not isinstance(tcPr, CT_TcPr):
            continue

        for element in tcPr:
            if not isinstance(element, _Element) or element.tag[-3:] != "shd":
                continue

            return element.attrib[FILL_KEY]


def get_shd_cell_text(tc: CT_Tc):
    # <w:tbl> -> <w:tr> -> <w:tc> -> <w:tcPr> -> <w:shd>

    for tcPr in tc:
        if not isinstance(tcPr, CT_Tbl):
            continue

        for elements_tr_pr in tcPr:
            if not isinstance(elements_tr_pr, CT_Row) and elements_tr_pr.tag[-3:] != "tr":
                continue
            for elements_tc in elements_tr_pr:
                if not isinstance(elements_tc, CT_Tc):
                    continue
                for elements_tr_pr_tbl in elements_tc:
                    if not isinstance(elements_tr_pr_tbl, CT_TcPr):
                        continue

                    for element in elements_tr_pr_tbl:
                        if not isinstance(element, _Element) or element.tag[-3:] != "shd":
                            continue

                        return element.attrib[FILL_KEY]


def get_shd(tc: CT_Tc):
    fill = get_shd_cell(tc)
    # print(fill)
    if fill:
        fill = str(fill).lower()
        # if fill in (GROUP_COLOR, REMOTED_COLOR):
        return fill

    text_fill = get_shd_cell_text(tc)
    return str(text_fill).lower() if text_fill else None


def get_group_name(string: str):
    if not isinstance(string, str):
        return None

    match = re.search(
        r"(\d?[А-яЕЁ]+-\d.\d\dК?)",
        string.upper().strip(),
        re.RegexFlag.MULTILINE | re.RegexFlag.IGNORECASE
    )

    if match:
        return match.group()


def check_empty_text(string: str):
    return not re.search(
        r"[А-яЕЁ\d]",
        string,
        re.RegexFlag.MULTILINE | re.RegexFlag.IGNORECASE
    )


def get_cell_text(cell: _Cell):
    ps = []
    tbls = []
    for element in cell._tc:
        if isinstance(element, CT_P):
            ps.append(element)
        if isinstance(element, CT_Tbl):
            tbls.append(element)

    text = []
    for p in ps:
        for r in p:
            if not isinstance(r, CT_R):
                continue
            for t in r:
                if not isinstance(t, CT_Text):
                    continue

                text.append(t.text)

    for tbl in tbls:
        for tr in tbl:
            if not isinstance(tr, CT_Row) and tr.tag[-3:] != "tr":
                continue
            for tc in tr:
                if not isinstance(tc, CT_Tc):
                    continue
                for p in tc:
                    if not isinstance(p, CT_P):
                        continue
                    for r in p:
                        if not isinstance(r, CT_R):
                            continue
                        for t in r:
                            if not isinstance(t, CT_Text):
                                continue

                            text.append(t.text)

    row_text = " ".join(text)

    return row_text


def get_groups_new(cells: Tuple[_Cell]):
    groups = {}
    for index, cell in enumerate(cells):
        text = get_cell_text(cell)
        if not text or text.lower() in ("дата", "лента", "время", "ауд."):
            continue

        group_name = get_group_name(text)
        if not group_name:
            continue

        groups[group_name] = index

    return groups


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


def get_teacher(string: str):
    if not isinstance(string, str):
        return None

    match: list[tuple[str, str, str], tuple[str, str, str]] = re.findall(
        r"([А-Я][а-я]+\.*)(?=(\s+[А-Я][.\s]+[А-Я]\.?\b)|(\s+[А-Я]\.?\b))",
        string.strip(),
        re.RegexFlag.MULTILINE
    )

    result: list[str] = []

    for text in match:
        name, initials = text[0], text[1] + text[2]
        initials = initials.strip()
        if len(initials.replace(" ", "").replace(".", "")) > 1:
            initials = f"{initials[0]}. {initials[1:].replace(' ', '').replace('.', '')}"
        if initials[-1] != ".":
            initials += "."

        result.append(" ".join([name.strip(". "), initials]))

    return result or None, match or None


def get_class_rooms(string: str):
    if not isinstance(string, str):
        return None

    match = re.findall(
        r"(\d\d\d)",
        string.upper().strip(),
        re.RegexFlag.MULTILINE
    )
    if not match:
        match = [string.strip()]

    return match or None


def get_schedule_new(rows: _Rows, groups: dict[str, int], warnings: list):
    all_cells: List[List[_Cell]] = [row.cells for row in rows]

    raw_schedule = {}
    for group_name, group_index in groups.items():
        for index_column in range(1, len(all_cells)):
            cell = all_cells[index_column][group_index]

            row_text = get_cell_text(cell)
            text = row_text if not check_empty_text(row_text) else None
            original_text = " ".join(text.split()) if text else None

            shd = get_shd(cell._tc)

            remoted = shd not in ("ffffff", None)

            if text:
                split_text = text.lower().split()
                top_text = text.split()

                try:
                    remoted_index = split_text.index("до")
                except ValueError:
                    pass
                else:
                    remoted = True

                    # Удаляем "ДО - ", который по сути находится в начале текста
                    del top_text[remoted_index]
                    if check_empty_text(top_text[0]):
                        del top_text[0]
                finally:
                    text = " ".join(top_text)

            cell_class_room = all_cells[index_column][group_index + 1]

            class_room = get_cell_text(cell_class_room)
            class_room = class_room if not check_empty_text(class_room) else None

            class_rooms = get_class_rooms(class_room)

            teacher, original = get_teacher(row_text)

            for teacher_orig in original or []:
                teacher_orig = "".join(teacher_orig)
                text = text.replace(teacher_orig, "").strip(". ")

            subgroups = get_subgroups(text)
            if subgroups:
                text = text.replace(subgroups, "").strip(". ")

            group_schedule = raw_schedule.get(group_name, {})
            group_schedule[str(index_column)] = {
                "original_text": original_text,
                "name": text,
                "teacher": teacher,
                "class_room": class_rooms,
                "remoted": remoted
            }
            if text and not teacher:
                warnings.append(f"not_teacher:{group_name}:{index_column}")
            if text and remoted is False and not class_rooms:
                warnings.append(f"not_class_rooms:{group_name}:{index_column}")

            raw_schedule[group_name] = group_schedule

    return raw_schedule


def convert_schedule(file_path: str):
    from pdf2docx import Converter

    converted_file_path = f"{file_path}.docx"

    if not os.path.isfile(converted_file_path):
        cv = Converter(file_path)
        cv.convert(converted_file_path)
        cv.close()

    with open(converted_file_path, "rb") as file:
        document: FileDocument = Document(file)
    return document


def parse_schedule_new(file_path: str):
    document = convert_schedule(file_path)

    warnings = []

    all_groups = []
    schedule = {}
    for table in document.tables:
        groups = get_groups_new([row.cells for row in table.rows][0])
        table_schedule = get_schedule_new(table.rows, groups, warnings)

        all_groups += list(groups.keys())
        schedule.update(**table_schedule)

    if len(all_groups) != 42:
        warnings.append(f"len_groups:{len(all_groups)}")

    return all_groups, schedule, warnings


async def go_parse_schedule(file_path: str):
    return await run_async(parse_schedule_new, file_path)


groups, schedule, _warnings = parse_schedule_new("27.09.2023.pdf")
print(groups)
pprint(schedule)
