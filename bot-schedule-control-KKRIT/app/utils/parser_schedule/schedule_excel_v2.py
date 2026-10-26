from pprint import pprint
from typing import Tuple, List, Union

import openpyxl
from openpyxl.cell import Cell, MergedCell
from openpyxl.cell.read_only import EmptyCell
from openpyxl.workbook import Workbook

from app.utils.parser_schedule.types import Tape, normal_text
from app.utils.parser_schedule.utils import get_group_name


def parse_schedule(file_path: str):
    wb: Workbook = openpyxl.load_workbook(file_path, read_only=True)

    tables = []
    for ws in wb.worksheets:
        rows: List[Tuple[Union[Cell, MergedCell]]] = ws.iter_rows()

        row_start = 0
        raw_table = []
        for row_index, row in enumerate(rows):
            row = row[row_start:]

            if row_index == 0:
                values = [Tape.from_cell(cell) for cell in row]
                raw_table.append(values)

                for value in values.copy():
                    if get_group_name(value.text):
                        break

                    row_start += 1
                    values.pop(0)

                continue

            if not row or isinstance(row[0], EmptyCell):
                continue

            if row[0].border.top.style and row[0].border.bottom.style:
                values = [Tape.from_cell(cell) for cell in row]
                raw_table.append(values)

            if row[0].border.top.style and not row[0].border.bottom.style:
                values = [Tape.from_cell(cell) for cell in row]
                raw_table.append(values)

            if not row[0].border.top.style:
                values = []
                for cell_index, cell in enumerate(row):
                    pre_cell: Tape = raw_table[-1][cell_index]

                    if cell.value is None:
                        values.append(pre_cell)
                        continue

                    if pre_cell.text is not None:
                        text = pre_cell.text + " " + normal_text(cell.value)
                        cell = Tape(text=text, fill=pre_cell.fill)
                    else:
                        text = normal_text(cell.value)
                        cell = Tape(text=text, fill=pre_cell.fill)

                    values.append(cell)
                raw_table[-1] = values

        if raw_table != [[]]:
            tables.append(raw_table)

    wb.close()

    return tables


if __name__ == "__main__":
    # _colors = []
    _tables = parse_schedule("26.11_изм.9АБД-3.24К (2).xlsx")
    pprint(_tables)
    # for _table in _tables:
    #     for _row in _table:
    #         for _cell in _row:
    #             if _cell.fill not in _colors:
    #                 print(_cell, _cell.fill)
    #                 _colors.append(_cell.fill)
    # print(_colors)
    # pprint(_tables)
