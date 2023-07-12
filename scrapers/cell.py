from __future__ import annotations

from typing import TypeVar, List

import re

ASCII_TRANSLATION = 65
MAX_COL = 25


class Cell:

    def __init__(self, col: chr | str | int, row: int):
        """
        Represents a cell in a Google Sheets. This offers two things over just using (int, int):
         1: Overloading operators (to make things smoother / "clearer" (subjective) when translating from a cell)
         2: Ease of swapping between (int, int) and A1 notation.

        Columns can be accepted as either integers or chars (e.g.: 0 = 'A').

        OPERATIONS:

        - "(cell) + / - (int) -> (cell)" (addition / subtraction): Translate up / down (rows).
                                                                   Examples: E18 + 1 = E19, D4 - 2 = D2

        - "(cell) << / >> (int) -> (cell)" (bitshift): Translate left / right (cols).
                                                       Examples: E18 >> 1 = F18, D4 << 2 = B2

        - "(cell) * (cell) -> (list[list[cell]])" (multiplication):  Selection of cells, grouped by rows.
                                             Examples: E18 * E20 = [E18, E19, E20], D4 * E5 = [[D4, E4], [D5, E5]]

        - "(cell) * (int) -> (list[cell])" (multiplication): Selection of cells, going downwards by rows.
                                            Examples: E18 * 1 = [E18, E19], D4 * 2 = [D4, D5, D6]
        """

        if type(col) == str or type(col) == chr:
            col = max(ASCII_TRANSLATION, min(ASCII_TRANSLATION + MAX_COL, ord(col))) - ASCII_TRANSLATION

        self.col = col
        self.row = row

    @staticmethod
    def from_a1(a1_notation: str) -> Cell:
        return Cell(col=a1_notation[0], row=int(''.join(a1_notation[1:])))

    def __add__(self, other: int) -> Cell:
        return Cell(col=self.col, row=max(self.row + other, 1))

    def __sub__(self, other: int) -> Cell:
        return Cell(col=self.col, row=max(self.row - other, 1))

    def __rshift__(self, other: int) -> Cell:
        return Cell(col=max(0, min(self.col + other, MAX_COL)), row=self.row)

    def __lshift__(self, other: int) -> Cell:
        return Cell(col=max(0, min(self.col - other, MAX_COL)), row=self.row)

    def __mul__(self, other: int | Cell) -> List[Cell] | List[List[Cell]]:
        if type(other) == int:
            return [Cell(col=self.col, row=i) for i in range(self.row, self.row + max(0, other) + 1)]

        elif type(other) == Cell:
            return []

        else:
            raise TypeError("type must either be int or Cell!")

    def __lt__(self, other):
        """
        Implemented this one because sorted() uses it; the others aren't really relevant here
        """
        if self.col < other.col:
            return True

        if self.row < other.row:
            return True

        return False

    def __eq__(self, other):
        return self.col == other.col and self.row == other.row

    def __hash__(self):
        return hash((self.col, self.row))

    def __str__(self) -> str:
        # return f"{self.col}, {self.row}"
        return f"{chr(self.col + ASCII_TRANSLATION)}{self.row}"

    def __repr__(self) -> str:
        return self.__str__()

    def range(self, other: int | Cell, skip=1) -> List[Cell] | List[List[Cell]]:
        if type(other) == int:
            return [Cell(col=self.col, row=i) for i in range(self.row, self.row + max(0, other) + 1)
                    if (i - self.row) % skip == 0]

        elif type(other) == Cell:
            return [[Cell(col=i, row=j) for i in range(self.col, max(self.col, other.col) + 1)]
                    for j in range(self.row, max(self.row, other.row) + 1)]

        else:
            raise TypeError("other must either be int or Cell!")


if __name__ == "__main__":
    cell1 = Cell('B', 2)
    cell2 = Cell('C', 2)

    cells = [cell2, cell1, cell1, cell2]
    print(cells)
    print(sorted(cells))
