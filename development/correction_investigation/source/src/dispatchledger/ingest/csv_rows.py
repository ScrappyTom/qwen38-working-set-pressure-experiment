"""Decode a complete receipt stream using the documented six-column format."""
import csv
from io import StringIO

from ..records import Receipt
from .fields import identifier, label, number, status

HEADER = ["ticket", "revision", "depot", "item", "units", "status"]


def read_receipts(text: str) -> list[Receipt]:
    rows = csv.reader(StringIO(text, newline=""))
    if next(rows, None) != HEADER:
        raise ValueError("receipt header differs")
    result = []
    for row in rows:
        if len(row) != len(HEADER):
            raise ValueError("receipt row width differs")
        result.append(Receipt(identifier(row[0]), number(row[1], 1),
                              label(row[2]), label(row[3]), number(row[4], 0), status(row[5])))
    return result
