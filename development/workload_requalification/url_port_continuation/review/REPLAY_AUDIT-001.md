# URL saved-failure continuation: replay and accounting

Independent saved-data audit after normal `checked_submission` closure on
2026-10-02. The committed, frozen `verify_run.py --version001` and
`measure_run.py --version001` both passed on their first execution. Their original
sources remain unchanged. Logs are `VERIFY-001-001.log` and
`METRICS-001-001.log`; results are `VERIFICATION-001.json` and
`METRICS-001.json`. No checker, model, native template/tokenizer, or GPU execution
was performed during this audit. Runtime shutdown and dedicated-port closure
were already recorded and were verified from the sealed evidence.

## Exact continuation, not a fresh entry

The inherited run002 stopped at20 consumed requests/30 operations with actual
failed tests check CHK-0030 and saved tests. This attempt retained that candidate,
history, account, source/version/effect state, observations and preceding
receipts. Only the declared request allowance changed from20 to36; consumption
was not reset. The operation cap remained60. Actual C21 input differs from the
original admitted final input only in that allowance and remaining opportunity.

The continuation made12 more requests and17 more operations, then submitted at
cumulative32/47. Final candidate is
`f0fe4cd991966428a69696729ac35eec6446b68f9d90b1dc6e26840ca7b75863`;
public CHK-0046 applies to that exact candidate and checker definition. This is
uncoached continuation with additional declared opportunity, not a successful
fresh20-request entry or an unchanged historical replication.

## Replay and actual delivery

Exact replay verified1545 bound sources,898 inherited custody records,
275 continuation custody records,18 saved native input trials,12 complete new
replies,17 new operations, and19 saved state checkpoints. Every checkpoint was
restored without changing its recorded state. Three observations, including
inherited CHK-0030 and the two new checks, were read through the replay-only
observation store; subprocess execution was forbidden. The response seal is
SHA256 `b07393cd45182f1427645006fa137f6154064f80653dfaa81bf0fdffea3e26ab`.

`DELIVERY-001.json` separately compares actual following wire bodies to each
completed host outcome. All16 outcomes of the11 nonterminal invocations are
represented in the next sent input. All five read extents are present with their
exact candidate/file bindings and bytes, all four edit-rejection receipts are
complete, and both executed-check receipts are complete. Accepted-edit receipts
carry actual successor bindings and refreshed current source; their archived
diff text is deliberately not repeated in those compact receipts. Source bodies
deduplicated into `working_set.sources` are delivered evidence, not missing
feedback. The final submission receipt was admitted but has no subsequent C33
request and is not counted as delivered to one.

This establishes presentation, not model interpretation. Throughout these new
calls the view remains the inherited recovery arrangement: parked broad bodies
are explicitly omitted, while acquired current source is presented. No new
working-set replacement or capacity rejection occurred. The admitted native
maximum and sent-input maximum are both19464 for this continuation; the original
run's larger unsent trial must not be reported as a sent continuation input.

## Completed effects and costs

New operation counts: three account revisions, six patch attempts, two checks,
five reads, and one submission. Two patches were accepted and four rejected.
C21's proposed old test text contained a literal Unicode digit where the exact
visible source contained an ASCII escape; the unchanged candidate received
`old_not_found`. C22 corrected the exact old source, added seven exact-class
assertions, and its declared tests check passed. Three documentation anchors
were rejected as ambiguous before C31's longer unique anchor saved the38-line
addition and its declared public check passed. C32 consumed that pass and
submitted. Rejected proposals are not saved contributions. Root's direct
transcript/artifact review assesses their meaning and final prose separately.

| Accounting | Original inherited attempt | New continuation | Cumulative |
|---|---:|---:|---:|
| Sent/processed model requests |20|12|32|
| Recorded operations |30|17|47|
| Sent input tokens |263924|204200|468124|
| Generated tokens, thinking and final |50169|90558|140727|
| Model-request seconds |3430.280|5814.672|9244.952|
| Response-processing seconds |131.425|83.732|215.157|
| Peak sent input |23801|19464|23801|
| Peak generated response |10678|23930|23930|
| Peak input plus generation |27724|40594|40594|

The new task loop took6016.203seconds (100.27minutes); model requests accounted
for5814.672seconds (96.91minutes). The continuation's largest response and
combined footprint are C21. Its23930 generated tokens preceded a rejected edit,
so accepted final work alone would hide a significant cost. These figures do not
classify every generated token as useful or wasted and do not isolate a host,
format, evidence, or model cause. They exclude reviewer time and preparation
cost. No usage or request-duration data is missing.

No CUDA failure, template truncation, physical-context exhaustion, or operator
stop is recorded. The new runtime's observed minimum free GPU memory was242MiB
under the previously declared monitored-margin policy. Physical delivery and
checked closure do not establish efficient sustained work or complete semantic
accuracy; those remain separate review outcomes.
