"""Calendar-day windows at explicit fixed UTC offsets."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import re

from .model import Shift


def fixed_offset(text: str) -> timezone:
    if re.fullmatch(r"[+-](?:0\d|1\d|2[0-3]):[0-5]\d", text) is None:
        raise ValueError("invalid fixed UTC offset")
    sign = 1 if text[0] == "+" else -1
    return timezone(sign * timedelta(hours=int(text[1:3]), minutes=int(text[4:])))


@dataclass(frozen=True)
class DayWindow:
    start: datetime
    end: datetime

    def contains(self, shift: Shift) -> bool:
        """Whether the entire shift interval is inside this window."""
        return self.start <= shift.start and shift.end <= self.end


def day_window(day: str, offset: str) -> DayWindow:
    local_date = date.fromisoformat(day)
    start = datetime.combine(local_date, datetime.min.time(), fixed_offset(offset))
    return DayWindow(start, start + timedelta(days=1))
