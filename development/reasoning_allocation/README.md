# Reasoning effort on completed work

The bounded xhigh/medium comparison is prepared and qualified. Read the
[specification](SPEC.md) and [preparation review](PREPARATION_REVIEW.md).
The preceding [uncoached contribution](../uncoached_contribution/review/RESULTS.md)
motivates this work; it is not included as a matched control.

The driver retains the existing host and coverage task and changes only the
declared effort instruction within each seed. The four fresh attempts run in
xhigh/medium then medium/xhigh order. Each starts with an empty source group and
the same saved work. Qwen receives no coaching or prior comparison results.

Run from the repository:

```powershell
$env:PYTHONPATH = 'src;tests;scripts;development/reasoning_allocation'
py -3.12 -B -X utf8 -m unittest discover -s development/reasoning_allocation -p test_compare.py -v
py -3.12 -B -X utf8 development/reasoning_allocation/compare.py execute
```

The execution entry point verifies the frozen package and refuses an existing
run-001. Do not rerun it as a retry. Preparation-001 is a preserved verifier
failure; preparation-002 is the successful native qualification. Nine selected
checks pass. No model generation occurred during preparation. Assess the completed
artifacts, all input/thinking/output and actual feedback before deciding whether
the tested effort policy earns further use.
