"""Public entry points for an imported receipt sequence."""
from .ingest.csv_rows import read_receipts
from .reporting.totals import Totals
from .state.registry import Registry


def summarize_csv(text: str) -> list[dict]:
    registry = Registry()
    totals = Totals()
    for receipt in read_receipts(text):
        change = registry.accept(receipt)
        if change is not None:
            totals.apply(change)
    return totals.rows()


def latest_receipts(text: str):
    registry = Registry()
    for receipt in read_receipts(text):
        registry.accept(receipt)
    return registry.latest()
