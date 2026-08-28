# Development rehearsal attempt 3 finding

The fourth development-only lifecycle completed 14 real calls with no
transport, schema, tokenizer, capacity, custody, or server-lifecycle failure.
Qwen read all three required large audit/policy files, inspected
`staging/readiness.py`, produced the exact intended readiness patch, and ended
on a passing prefork check. It did not reach `fork_ready` within the call
budget, so no C50/T25 branch ran and no measured fixture was loaded or exposed.

Direct transcript inspection found that the host rejected a valid early
`fork_ready` attempt as missing `policy/channel.py` even after Qwen had read
lines 1–230 and then 231–232 through the exact continuation. The host marked a
required file complete only when one read began at line 1 and reached EOF; it
did not union exact page coverage. Qwen then reread the complete 232-line file
in one call, proving the bytes were available but spending scarce calls on an
apparatus workaround. Subsequent premature gate attempts and a late mutation
left no call for the final boundary action.

The earned correction tracks and merges exact line intervals per file and
marks a required read complete when their union covers line 1 through EOF.
This does not summarize or infer that content was understood. It only records
which exact current bytes the actor actually acquired. A regression test binds
the two-page completion behavior. The immutable lifecycle is preserved under
`development_live_rehearsal_attempt3_page_coverage_failure/`.
