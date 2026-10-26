from dataclasses import dataclass
from typing import Union, Optional

from openpyxl.cell import Cell, MergedCell


@dataclass
class Tape:
    text: Optional[str]
    fill: str

    @staticmethod
    def from_cell(cell: Union[Cell, MergedCell]):
        text = cell.value
        if cell.fill:
            fill = cell.fill.fgColor.rgb
        else:
            fill = "00000000"
        return Tape(text=normal_text(text), fill=fill)

    def __repr__(self):
        text = f'"{self.text}"' if isinstance(self.text, str) else self.text
        return f"Tape({text})"


def normal_text(text: Optional[str]):
    if isinstance(text, (int, float)):
        text = str(text)

    return " ".join(text.replace("\n", " ").split()) if isinstance(text, str) else text
