# E19 run002 saved-data replay and accounting

Both unchanged, source-bound helpers passed their first post-seal attempt:
`VERIFY-002-001.log` / `VERIFICATION-002.json` and
`METRICS-002-001.log` / `METRICS-002.json`. No checker, hidden evaluator,
model, tokenization or native request was executed for this audit.

The response seal is
`bd3c00eccdda15050dc52e1e1dc71be423694dfa8e5b307307f22ed114a0c331`.
Its disposition is checked submission. Exact replay checks 9 replies, 9
requests, 12 operations, 13 native input measurements, 14 restored state
checkpoints, 200 custody records and 436 source bindings. Both reused replay
cores agree. The exact original fresh candidate is preserved in the starting
state; the final candidate is
`5c7eba4fbad9c51325a9abc4f4b27c5b8d9eedb5b344558b5921915ed854a49f`.

The single executed public observation, CHK-0011, binds that candidate and the
original public checker SHA256
`2bcb87dc5d40656dfd1e4a13439e222ba4071dcbb993b877f911f6bcedd32ea5`.
It passed with completed capture: 15 stdout bytes, zero stderr bytes. Replay
verifies the preserved observation without subprocess execution. The observation
and applicable result appear in the actual C09 input before submission; the final
submission receipt has no following model request and is not counted as delivered.

Direct inspection of the actual C06 wire, before its first accepted mutation,
finds all four original source bodies together. Their `content` bytes compare
exactly with the frozen original files: artifact_units.py lines 1–459 / 17,470
bytes; reopen.py 1–83 / 3,130; records.py 1–460 / 12,218; hashing.py 1–39 /
1,172. The source bodies were first delivered in C03, C04, C05 and C06
respectively. Earlier accepted acquisition alone is not used to establish this
exposure. C07/C08 show refreshed exact source after the two accepted edits.
This is mechanical delivery evidence; substantive interpretation remains a
separate direct transcript review.

The 12 actual operations comprise one directory acquisition, four source reads,
three model-account records, two accepted patches, one explicit public check and
submission. There is no rejected operation, failed live task check, imported
capture acquisition, working-set replacement or recovery presentation in this
attempt. The three account records establish use of the channel, not its causal
benefit or semantic correctness.

The sealed saved-record accounting totals 121,479 sent input tokens, 7,210
generated tokens, 668.360 model-request seconds (11.14 minutes) and 710.172
task-loop seconds (11.84 minutes). Peak sent input is 18,110 tokens; peak
input-plus-generation is 18,729. All nine responses have qualified token usage
and recorded receipt duration. This is a single functional trajectory, not a
controlled efficiency comparison or context-pressure result.

Owned runtime shutdown and the free dedicated port are verified. The recorded
minimum free GPU memory is 242 MiB, with no CUDA failure or truncation observed.
Artifact preservation, all task clauses and unchanged hidden acceptance remain
separate post-seal reviews; neither exact replay nor the public pass establishes
them by itself.

An optional metadata-inspection snippet initially assumed source extent keys
`start_line`/`end_line`, which the actual view names
`returned_start_line`/`returned_end_line`. It failed inertly with KeyError before
writing an audit artifact. Reading the actual keys corrected that reviewer-side
inspection; no helper, source, candidate or sealed record changed.
