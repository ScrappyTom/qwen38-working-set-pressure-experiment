# Correct saved work and full ledger delivery; recovery obligation still missed

The fresh, uncoached run002 closed with a checked submission after10 requests and
17 operations. Both requested code changes are correct, all904 required ledger
lines reached model inputs, and all128 other files remain unchanged. The original
task is nevertheless incomplete: after releasing the marker body atC02, the actor
edited the footer atC04 without recovering the required exact evidence.

The run is preserved under response seal
`9a0250225334ed26b2ad695ae01c3640774851229f110ce8c522732dde9af121`.
Its final candidate is
`750433f899bb30ed198f5f786ba25ac90edc18e9e9a71e79cc998f6d5431bfd0`.
There was no coaching, evaluator-selected group, forced release, retry or extension.

| Decision | Actual available support and choice | Outcome |
|---|---|---|
| C01-C02 | Directory binding identifies OBS-0002; its complete152-byte body arrives | Correct marker selected and stored in the account |
| C02-C03 | work_on requests both targets and four ledgers with results=[] | Both2-line targets arrive whole; each ledger1-50; marker body released |
| C03-C04 | Exact current targets, marker value in authored account/current label | Correct label then footer edits; required exact recovery omitted |
| C05-C08 | Actual returned extents and cumulative account | Four groups advance51-102,103-154,155-206,207-226, completing every ledger |
| C09-C10 | Saved current work, coverage account, actual current public pass | Check then consumed pass and accepted submission |

The C02 reply does not discuss its release of the marker. Its account copies the
value while dropping the task's conditional recovery obligation. C04 contains the
fresh label diff, not an exact reacquisition of an externalized payload. There are
no alternate recovered historical pages requiring a separate semantic judgment.
Correctly remembering the marker is not the procedure this task asks to exercise.

The account does show useful coverage continuity: earlier ledger pages and their
recent rows leave the input, while later calls combine the cumulative range account
with newly delivered extents. This is observed use, not an isolated causal benefit
or proof that an explanatory rationale survives future changes.

Original public/hidden programs are identical; rerunning them establishes
reproducibility, not independent hidden coverage. Eight separately executed concrete
examples additionally cover empty, whitespace, mixed case and Unicode behavior.
Direct source review confirms the strip/upper and strip/casefold repairs. The
original-contract evaluator requires ledger completion by submission, not before
each edit; its result remains false solely on the missed recovery requirement.

| Cost | Run002 |
|---|---:|
| Input / generated tokens |178,208 /6,182|
| Model / task-loop seconds |756.923 /900.437|
| Peak input / input plus generation |22,684 /23,687|
| Operations |7 accounts,5 groups,2 edits,1 retrieval,1 check,1 submission|

The preceding attempt used32 requests and left three ledger tails unread. These
descriptive differences do not isolate a treatment effect. Both trials preserve
the failed original recovery procedure; run001 and its scores remain unchanged.

Exact replay verifies552 custody records,60 native inputs,19 state snapshots and
574 source bindings, including the actual check capture and every restored state.
All10 full responses and actual inputs/effects received direct review as specified
in RUN002-READING_NOTES.md. The owned runtime is closed. Preparation and review are
additional costs; no independent reviewer-time measurement is claimed.

Next: a small nonexecuting consultation on the exact C02 input and public proposal,
before any clarification. Test whether the actor predicts replacement effects and
the remaining evidence obligation. Do not repeat this task unchanged or infer that
another warning, sticky selection or task-specific gate is already justified.
