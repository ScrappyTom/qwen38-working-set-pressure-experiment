"""Maintain the report while accepted revisions arrive."""
from ..records import Change
from .entries import bucket, contributions


class Totals:
    def __init__(self):
        self._units: dict[tuple[str, str], int] = {}

    def apply(self, change: Change) -> None:
        destination = bucket(change.after)
        for receipt, units in contributions(change):
            self._units[destination] = self._units.get(destination, 0) + units
            if self._units[destination] == 0:
                del self._units[destination]

    def rows(self) -> list[dict]:
        return [{"depot": depot, "item": item, "units": units}
                for (depot, item), units in sorted(self._units.items())]
