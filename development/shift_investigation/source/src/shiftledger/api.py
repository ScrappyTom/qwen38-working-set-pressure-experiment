"""Public entry point for text input and an explicitly located report day."""
from .importing import read_shifts
from .reporting.daily import report_minutes
from .windows import day_window


def daily_minutes(csv_text: str, day: str, offset: str = "+00:00") -> dict[str, float]:
    shifts = read_shifts(csv_text)
    window = day_window(day, offset)
    return report_minutes(shifts, window)
