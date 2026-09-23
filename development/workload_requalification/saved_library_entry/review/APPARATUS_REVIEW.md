# Recorded apparatus intervals

The completed saved-library run reports3498.609 seconds for the task loop and
2842.890 seconds for model requests, leaving655.719 seconds outside those requests.
That difference is not all tool execution: recorded reply processing totals282.095
seconds and includes admission/verification. Do not add overlapping categories.

apparatus_intervals.py reproduces APPARATUS_INTERVALS.json from the sealed records
without inference, tokenization, checker execution or a running server. Across54
native template/tokenizer requests the recorded round trips total1.428 seconds.
The17 intervals from response extraction to post-response validation/health record
total179.871 seconds. The27 pre-native input-construction intervals are also listed
with their actual preceding record. These are wall intervals, not CPU profiles.

Static inspection places full source verification plus health/recording inside
these intervals. The source checker uses four workers and verifies the complete
closure rather than trusting a cache. Repeated approximately ten-second intervals
justify isolating apparatus costs, but do not establish hashing as their sole cause.

Next offline qualification should separately time source verification, health,
input construction and custody using the exact completed package. No second GPU
workload or heavy profiling runs alongside the active prose follow-up. Preserve all
checks until a measured alternative can show the same mutation detection and source
closure guarantee. A faster loop must not silently weaken evidence integrity.

No production source, active request, inference settings or evidence was changed
by this review. These measurements are apparatus evidence, not model behavior.
