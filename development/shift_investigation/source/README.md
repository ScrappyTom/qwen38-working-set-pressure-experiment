# Shift Ledger

A small library for daily staffing reports. It accepts CSV shifts and returns
minutes worked per employee for one local calendar date at a fixed UTC offset.
It uses only the Python standard library. Add `src` to the import path.

```python
from shiftledger.api import daily_minutes
totals = daily_minutes(csv_text, "2026-07-15", "+02:00")
```

CSV fields are `employee,start,end,status`. Timestamps include explicit UTC
offsets; `status` is `confirmed` or `void`. Naive timestamps, reversed or empty
intervals, empty employee identifiers and unknown statuses are rejected.
Each valid row represents a separate shift; overlapping rows are additive.

Report dates use the supplied fixed offset, not the computer's timezone. A day
runs from midnight inclusive to the next midnight exclusive. Only time within
that day contributes, including fractional minutes. Void rows never contribute.
Employees with no contributing time are omitted from the returned mapping.

`examples/overnight.csv` is a small input suitable for the public API. The public
check also exercises decoding and report behavior on separate concrete cases.
