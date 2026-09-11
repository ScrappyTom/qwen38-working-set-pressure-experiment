import csv
import io
import re
from decimal import Decimal


AMOUNT = re.compile(r"[+-]?[0-9]+(?:\.[0-9]{1,6})?\Z")


def decode(text):
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    if next(reader, None) != ["entry_id", "amount"]:
        raise ValueError("invalid CSV header")
    records, seen = [], set()
    for row in reader:
        if len(row) != 2:
            raise ValueError("invalid row width")
        key, raw = row
        if not key or key in seen:
            raise ValueError("invalid or duplicate entry identifier")
        if not AMOUNT.fullmatch(raw):
            raise ValueError("invalid amount")
        seen.add(key)
        records.append((key, Decimal(raw)))
    return records
