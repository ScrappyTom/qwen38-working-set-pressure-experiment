# Reasoning effort on completed work

The four-attempt xhigh/medium comparison is closed. Read the [results](RESULTS.md),
[full transcript audit](DIRECT_TRANSCRIPT_AUDIT.md), and [host audit](HOST_PATH_AUDIT.md).
Neither effort finishes the first seed. Both finish the second; medium takes
27.710 loop minutes versus 55.378 for xhigh, with more operations and input.
The 44 requests / 46 operations are uncoached, fully reviewed and exactly replayed.
The unused allowance is closed; no global setting change or extra run is adopted.

The [specification](SPEC.md), [preparation review](PREPARATION_REVIEW.md) and
execution manifest retain the consumed package. Preparation-001 is a preserved
verifier failure; preparation-002 is the successful native qualification. Nine
selected preparation checks passed with zero generation. The preceding
[uncoached contribution](../uncoached_contribution/review/RESULTS.md) motivated
this work; it is not included as a matched control.

At the published comparison revision, verify without requesting model inference:

```powershell
$env:PYTHONPATH = 'src;tests;scripts;development/reasoning_allocation'
py -3.12 -B -X utf8 development/reasoning_allocation/compare.py verify
py -3.12 -B -X utf8 development/reasoning_allocation/review/summarize.py
```

The verifier deliberately rejects drift in bound host/checker sources. Use the
published comparison checkout if a later maintenance revision changes those files.
The execution entry point refuses an existing run-001; do not remove evidence to
retry it. Private runtime logs remain local, with their hashes in the public seals.
