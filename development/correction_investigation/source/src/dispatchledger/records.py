"""Validated receipt values passed between import, selection and reporting."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Receipt:
    ticket: str
    revision: int
    depot: str
    item: str
    units: int
    status: str


@dataclass(frozen=True)
class Change:
    before: Receipt | None
    after: Receipt
