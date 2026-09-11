"""Select the current revision of each independent ticket."""
from ..records import Change, Receipt


class Registry:
    def __init__(self):
        self._receipts: dict[str, Receipt] = {}

    def accept(self, receipt: Receipt) -> Change | None:
        before = self._receipts.get(receipt.ticket)
        if before is not None:
            if receipt.revision < before.revision:
                return None
            if receipt.revision == before.revision:
                if receipt != before:
                    raise ValueError("conflicting current revision")
                return None
        self._receipts[receipt.ticket] = receipt
        return Change(before, receipt)

    def latest(self) -> list[Receipt]:
        return [self._receipts[ticket] for ticket in sorted(self._receipts)]
