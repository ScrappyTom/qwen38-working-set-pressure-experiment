"""Validated domain records; instants are normalized at import."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Shift:
    employee: str
    start: datetime
    end: datetime
    status: str

    @property
    def duration_minutes(self) -> float:
        return (self.end - self.start).total_seconds() / 60.0
