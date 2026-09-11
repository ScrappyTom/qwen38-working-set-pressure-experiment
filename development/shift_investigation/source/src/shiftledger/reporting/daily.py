"""Aggregate confirmed staffing time for a daily report."""
from collections.abc import Iterable

from ..model import Shift
from ..windows import DayWindow


def report_minutes(shifts: Iterable[Shift], window: DayWindow) -> dict[str, float]:
    totals: dict[str, float] = {}
    for shift in shifts:
        if shift.status != "confirmed":
            continue
        if not window.contains(shift):
            continue
        minutes = shift.duration_minutes
        totals[shift.employee] = totals.get(shift.employee, 0.0) + minutes
    return dict(sorted(totals.items()))
