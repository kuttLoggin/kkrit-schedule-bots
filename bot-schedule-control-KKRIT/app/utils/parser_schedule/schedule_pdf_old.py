import re
import os
from pprint import pprint
from typing import Tuple, List, Dict

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
    if fill:
        fill = str(fill).lower()
        if fill in (GROUP_COLOR, REMOTED_COLOR):
            return fill

    text_fill = get_shd_cell_text(tc)
    return str(text_fill).lower() if text_fill else None


def get_group_name(string: str):
    if not isinstance(string, str):
        return None

    match = re.search(
        r"^(\d?[А-яЕЁ]+-\d.\d\dК?)$",
        string.upper().strip(),
        re.RegexFlag.IGNORECASE
    )

    if match:
        return match.group()


def get_groups(cells: Tuple[_Cell]):
    groups = {}
    for index, cell in enumerate(cells):
        tc: CT_Tc = cell._tc

        text = get_cell_text(cell)
        shd = get_shd(tc)

        if not text or shd != GROUP_COLOR:
            continue

        group_name = get_group_name(text)
        if not group_name:
            continue

        groups.update({index: group_name})

    return groups


def check_empty_text(string: str):
    return not re.search(
        r"[А-яЕЁ\d]",
        string,
        re.RegexFlag.MULTILINE | re.RegexFlag.IGNORECASE
    )


def get_data_groups(data: List[Tuple]):
    data_groups = {}
    for row_index, cells in enumerate(data):
        groups = get_groups(cells)
        if not groups:
            continue

        data_groups[row_index] = {
            "groups": list(groups.values()),
            "indexes": list(groups.keys()),
            "start_cell_index": list(groups.keys())[0]
        }

    return data_groups


def get_indexes_groups(data_groups: dict):
    name_groups = []
    for value in data_groups.values():
        name_groups = [*name_groups, *value["groups"]]

    return {
        str(index): name for index, name in enumerate(name_groups)
    }


def get_numbers(data: List[Tuple], data_groups: dict):
    data_group = None
    numbers = []
    for row_index, cells in enumerate(data):
        if data_groups.get(row_index):
            data_group = data_groups[row_index]
            continue

        cell_index = data_group["start_cell_index"] - 1
        numbers.append(cells[cell_index].text)

    return numbers


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

    return " ".join(text)


def get_raw_schedule(data: List[Tuple], data_groups: dict):
    data_group = None
    raw_schedule = {}
    for row_index, cells in enumerate(data):
        if data_groups.get(row_index):
            data_group = data_groups[row_index]
            continue

        groups = data_group["groups"]
        indexes = data_group["indexes"]

        for index, group in zip(indexes, groups):
            cell: _Cell = cells[index]

            row_text = get_cell_text(cell)
            text = row_text if not check_empty_text(row_text) else None

            shd = get_shd(cell._tc)

            remoted = shd == REMOTED_COLOR

            # TODO: Найти когда нибудь нормальный способ что бы определять серый фон (до), а то сейчас хуй определить
            if text:
                split_text = text.lower().split()
                try:
                    remoted_index = split_text.index("до")
                except ValueError:
                    pass
                else:
                    remoted = True

                    text = text.split()
                    del text[remoted_index]

                    text = " ".join(text)

            group_schedule = raw_schedule.get(group, [])
            group_schedule.append({"text": text, "remoted": remoted})

            raw_schedule[group] = group_schedule

    for group, schedule in raw_schedule.items():
        group_schedule = schedule.copy()

        for tape in reversed(schedule):
            if not tape["text"]:
                group_schedule.pop()
            else:
                break

        raw_schedule[group] = group_schedule

    return raw_schedule


def get_data_schedule(rows: _Rows):
    result = {
        "groups": {},
        "schedule": {},
        "numbers": {}
    }

    data = [row.cells for row in rows]

    data_groups = get_data_groups(data)

    result["groups"] = get_indexes_groups(data_groups)
    result["numbers"] = get_numbers(data, data_groups)

    raw_schedule = get_raw_schedule(data, data_groups)

    result["schedule"] = {
        str(index): tapes for index, tapes in
        zip(result["groups"], raw_schedule.values())
    }

    return result


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


def get_groups_new(rows: _Rows):
    groups = {}
    for index_row, row in enumerate(rows):
        if get_cell_text(row.cells[0]) != "№":
            continue

        for index_cell, cell in enumerate(row.cells):
            text = get_cell_text(cell)
            if not text or text.lower() in ("№", "время"):
                continue

            group_name = get_group_name(text)
            if not group_name:
                continue

            tc: CT_Tc = cell._tc
            shd = get_shd(tc)
            print(shd)

            groups[group_name] = (index_row, index_cell)

    return groups


def get_schedule_new(rows: _Rows, groups: dict[str, tuple[int, int]], warnings: list):
    all_cells: List[List[_Cell]] = [row.cells for row in rows]

    raw_schedule = {}
    for group_name, indexes in groups.items():
        for index_column in range(indexes[0], len(all_cells)):
            cell = all_cells[index_column][indexes[1]]
            tc: CT_Tc = cell._tc

            shd = get_shd(tc)

            if shd == GROUP_COLOR:
                break

            row_text = get_cell_text(cell)
            text = row_text if not check_empty_text(row_text) else None
            original_text = " ".join(text.split()) if text else None

            remoted = shd == REMOTED_COLOR

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

            group_schedule = raw_schedule.get(group_name, {})
            group_schedule[str(indexes[0] + 1 - index_column)] = {
                "original_text": original_text,
                "name": text,
                # "teacher": teacher,
                # "class_room": class_rooms,
                "remoted": remoted
            }

            raw_schedule[group_name] = group_schedule

    return raw_schedule


# def parse_schedule(file_path: str):
#     document = convert_schedule(file_path)
#
#     all_cells: List[List[_Cell]] = [row.cells for row in document.tables[1].rows]
#
#     print([[get_cell_text(cell) for cell in cells] for cells in all_cells])
#
#     warnings = []
#
#     all_groups = []
#     schedule = {}
#     for table in document.tables:
#         groups = get_groups_new(table.rows)
#         table_schedule = get_schedule_new(table.rows, groups, warnings)
#
#         all_groups += list(groups.keys())
#         schedule.update(**table_schedule)
#
#     if len(all_groups) != 42:
#         warnings.append(f"len_groups:{len(all_groups)}")
#
#     return all_groups, schedule, warnings
#
#
# async def go_parse_schedule(file_path: str):
#     return await run_async(parse_schedule, file_path)


# groups, schedule, _warnings = parse_schedule("28.09.2023г.pdf")
# print(groups)
# pprint(schedule)


# def pdf_parser(file_path: str):
#     from py_pdf_parser.loaders import load_file
#     from py_pdf_parser.tables import extract_table
#     from py_pdf_parser.components import PDFElement
#
#     file = load_file(file_path)
#
#     table = extract_table(file.pages[0].elements, fix_element_in_multiple_cols=True)
#
#     for cels in table:
#         row = []
#         for cel in cels:
#             cel: PDFElement
#             text = cel.text() if cel else None
#             if text:
#                 text = " ".join(text.replace("\n", " ").split())
#
#             el = None
#             if text == "№":
#                 el = cel.original_element
#
#             row.append((text, el))
#
#         print(row)


# pdf_parser("28.09.2023г.pdf")


from typing import Optional

import pdfplumber
from pdfplumber.page import Page, Table


def cmyk_to_rgb(cmyk: tuple[float, float, float]):
    while True:
        if len(cmyk) >= 3:
            break
        cmyk = (*cmyk, cmyk[-1])

    r = 255 * cmyk[0]
    g = 255 * cmyk[1]
    b = 255 * cmyk[2]
    return int(r), int(g), int(b)


def to_bbox(rect: dict) -> tuple[float, float, float, float]:
    return rect["x0"], rect["top"], rect["x1"], rect["bottom"]


def is_included(cell_box: tuple[float, float, float, float], rect_box: tuple[float, float, float, float]):
    c_left, c_top, c_right, c_bottom = cell_box
    r_left, r_top, r_right, r_bottom = rect_box
    return c_left >= r_left and c_top >= r_top and c_right <= r_right and c_bottom <= r_bottom


def find_rect_for_cell(cell: tuple[float, float, float, float], rects: list[dict]) -> Optional[dict]:
    return next((r for r in rects if is_included(cell, to_bbox(r))), None)


def get_cell_color(cell: tuple[float, float, float, float], page: Page) -> tuple[float, float, float]:
    rect = find_rect_for_cell(cell, page.rects) if cell else None
    return cmyk_to_rgb(rect["non_stroking_color"]) if rect else (255, 255, 255)


def pdf_parser_table(file_path: str):
    pdf = pdfplumber.open(file_path)
    page = pdf.pages[0]
    tables: list[Table] = page.find_tables()
    table_extract = tables[0].extract()

    raw_table = []
    for row_index, texts in enumerate(table_extract):
        list_row = []
        for cell_index, text in enumerate(texts):
            color = get_cell_color(tables[0].rows[row_index].cells[cell_index], page)
            if text is not None:
                text = " ".join(text.replace("\n", " ").split())
            # else:
            #     try:
            #         text = raw_table[row_index - 1][cell_index]
            #     except IndexError:
            #         pass

            list_row.append({"text": text, "color": color})

        raw_table.append(list_row)

    # while True:
    #     try:
    #         if raw_table[0][0]["text"] == "№":
    #             break
    #     except IndexError:
    #         break
    #
    #     raw_table.pop(0)

    return raw_table


def identification_groups(rows: List[List[Dict]]):
    groups = {}
    for row_index, row in enumerate(rows):
        if row[0]["text"] != "№":
            continue

        for cell_index, cell in enumerate(row):
            text = cell["text"]
            if not text or text.lower() in ("№", "время"):
                continue

            group_name = get_group_name(text)
            if not group_name:
                continue

            groups[group_name] = (row_index, cell_index)

    return groups


def get_schedule():
    ...


def parse_schedule(file_path: str):
    table = pdf_parser_table(file_path)

    groups = identification_groups(table)
    # schedule =
    [print([cell["text"] for cell in row]) for row in table]


parse_schedule("25.09.2023.pdf")
