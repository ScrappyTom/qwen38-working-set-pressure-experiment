"""Signed contributions for a receipt revision transition."""
from ..records import Change, Receipt


def bucket(receipt: Receipt) -> tuple[str, str]:
    return receipt.depot, receipt.item


def contributions(change: Change) -> list[tuple[Receipt, int]]:
    entries = []
    if change.before is not None and change.before.status == "active":
        entries.append((change.before, -change.before.units))
    if change.after.status == "active":
        entries.append((change.after, change.after.units))
    return entries
