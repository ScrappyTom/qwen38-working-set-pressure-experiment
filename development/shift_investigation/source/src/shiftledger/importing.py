"""CSV decoding and validation, independent of report dates."""
import csv
import io
from datetime import datetime, timezone

from .model import Shift

FIELDS = ["employee", "start", "end", "status"]


def parse_instant(text: str) -> datetime:
    instant = datetime.fromisoformat(text.strip())
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("shift timestamps require a UTC offset")
    return instant.astimezone(timezone.utc)


def read_shifts(text: str) -> list[Shift]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != FIELDS:
        raise ValueError("unexpected CSV fields")
    shifts = []
    for row in reader:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("incomplete CSV row")
        employee, status = row["employee"].strip(), row["status"].strip()
        if not employee or status not in {"confirmed", "void"}:
            raise ValueError("invalid employee or status")
        start, end = parse_instant(row["start"]), parse_instant(row["end"])
        if end <= start:
            raise ValueError("shift end must be later than start")
        shifts.append(Shift(employee, start, end, status))
    return shifts
