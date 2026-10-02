# Imported capture acquisition and usable comparison evidence

This is a read-only development audit of the frozen compiler run-002 package at
f647d6d7. It was written while the attempt was still active, from completed C06
through C10 records. It does not classify the final run outcome. No frozen
implementation, model input, setting, allowance or operation was changed; no
inference, checker or qualification test was run for this audit. The root operator
subsequently requested normal draining through the already-active request. Any
successor policy must be separately qualified and frozen after closure.

## Direct evidence examined

The reviewer read the actual C08 system message, the C08–C10 user-state objects,
all three complete thinking outputs, and the exact public replies. C06–C07 public
replies establish the beginning of the acquisition sequence. The review also read
`capture_bridge.py`, the common current-source and saved-result acquisition paths,
and the task adapter that produces the reference and new request.

Each actually presented capture body was compared with the imported custody file
using its complete UTF-8 byte count and SHA-256. C08 contains the exact 9,168-byte
OBS-0002; C09 the exact 9,180-byte OBS-0003; C10 the exact 9,228-byte OBS-0001.
All retain the original observed candidate
`28441db41e7ca5385feb03c96574fed32acfc4d67e7e608c93572fe06ed8033d`.
This comparison checks the actual sent text, not only inventory flags or receipt
identity. Formal replay and the complete closed-run audit remain separate work.

| Input | Full capture actually present | Other capture bodies | Selected saved results | Sent input tokens | Public next operation |
| --- | --- | --- | --- | ---: | --- |
| C08 | OBS-0002, RES-0011 | OBS-0001 absent; OBS-0003 not yet acquired | Empty | 12,037 | Acquire OBS-0003 |
| C09 | OBS-0003, RES-0012 | OBS-0001 and OBS-0002 absent | Empty | 12,071 | Acquire OBS-0001 |
| C10 | OBS-0001, RES-0013 | OBS-0002 and OBS-0003 absent | Empty | 12,094 | Acquire OBS-0002 |

The preceding public operations acquire OBS-0001 in C06 and OBS-0002 in C07.
Thus the completed sequence is OBS1, OBS2, OBS3, OBS1, OBS2. All three audited
inputs are ordinary presentation, with no obstacle and
`selected_bodies_omitted=false`. README.md, compiler/api.py and compiler/unary.py
remain visible. The candidate is unchanged. This is not capacity eviction, a
clipped capture, a failed exact store, or an input containing earlier dialogue.

The C08–C10 reasoning identifies the currently absent counterparts and develops
useful comparison and repair analysis. C09 explicitly needs the original and
BUILD-A after seeing BUILD-B. C10 explicitly needs the emitted trees after seeing
the original. None of these three complete responses requests `work_on` to form
a capture group. Reacquiring a genuinely absent body should not be described as
forgetting a resident body. This does not establish that all subsequent reasoning
or every chosen read was necessary.

## The host imposes an asymmetric acquisition lifetime

Three implemented paths have different presentation effects:

* `read` adds the returned current-source range to the designated selection.
  Later ordinary operations retain it until an explicit selection replacement.
* `reopen_result` adds its returned saved-byte page to the designated saved
  results. A later page of the same saved handle replaces that page.
* The task-local `reopen_observation` produces an exact ordinary receipt and RES
  custody, but does not add it to the designated saved selection. Its body is
  latest feedback only. The next operation replaces that feedback even when
  there is ample input space and the source selection has not changed.

The inventory accurately changes `shown_complete` to false when a prior capture
leaves the input. It exposes the latest acquired RES identity. It does not promise
that all acquired captures remain visible. Custody and the current flags are
correct on this path.

The reference accurately offers `work_on` or `work_on_exact` to retain complete
acquired RES receipts together. It also says there is no prior conversation in the
input, and identifies `latest_feedback` as the last receipt. However, it never
states the ordinary imported acquisition's transient lifetime explicitly, while
the current-source `read` contract explicitly promises persistence. A comparison
task consequently requires the model to discover and execute a separate retention
step for one read interface that other read interfaces perform automatically.

This is a host usability and transition issue, rather than a proven storage
exception or a claim that the model cannot understand retrieval. The common
acquisition-versus-selection distinction is coherent in isolation. The concrete
task-facing division makes sequential comparison acquisition rotate its operands
unless the model notices and uses the separate grouping operation. Correct flags
do not by themselves make that acquisition sequence useful.

There is a smaller consistency issue: the imported operation is appended as an
exact example and explanation after the main generated required-forms collection,
rather than appearing in that collection like the other supported operations.
The actual extended schema and grammar accept it. This is not missing enforcement
or proof of the repeated acquisitions' cause, but the advertised operation list
should match the actual extended contract.

## What is earned, and what is not

There is an implemented path to simultaneous captures: select their complete RES
receipts through `work_on`. Preparation002 demonstrates a researcher-selected
three-capture source group and meaningful checked work within the input ceiling.
That establishes feasibility; it does not establish autonomous selection or the
result Qwen would produce with a different lifetime policy.

The possible decision to retain the current acquisition-only behavior is therefore
not logically excluded. It would keep explicit selection as a separate operation.
Its cost is now observable: on this task, several completed reads supply actual
missing evidence while displacing another needed operand. This audit supports
addressing that burden, without attributing the entire trajectory or deliberation
cost to it and without claiming a new policy must improve performance.

The root's proposed successor is a narrow, declared retention policy package:

1. An imported capture acquisition also designates that requested immutable
   capture for subsequent ordinary decisions, as a current-source read designates
   its requested range. It should not require an additional turn merely to retain
   what was opened for this comparison.
2. Repeated acquisition of the same OBS identity replaces its selected
   representation; it must not accumulate duplicate selected copies. Every actual
   acquisition still receives its own exact RES custody and remains in history.
3. Retain the original observed candidate, body bytes and digest. Imported
   evidence never becomes current-source editing authority or a current pass.
4. Measure the complete next selected group, feedback and surrounding state.
   Do not silently discard a comparison partner or claim whole delivery after
   partial paging. An unfit transition must leave truthful recovery control and
   preserve the previous selection under the declared rejection policy.
5. `work_on`/`work_on_exact` remain the explicit way to replace or release selected
   evidence. Normal lifetime and release behavior must be visible in the reference.
6. Generate or render the imported required form alongside the other actual action
   forms. Qualify the same operational and literal reply channels with the pinned
   native grammar; do not merely validate a Python-side schema.

This does not imply automatic retention of every check, directory page, search
result or historical action. Those operations have different purposes and costs.
It does not authorize blanket permanent retention, semantic summaries, a new
memory store, or in-run coaching.

## Qualification needed before another exposure

Use the actual closed checkpoint and fresh original entry as distinct paths. Verify
sequential OBS1/OBS2/OBS3 acquisition leaves all requested bodies exactly present
until explicit replacement, with truthful inventory and unchanged incident
bindings. Repeat an OBS and verify one selected identity but two archived
acquisitions. Verify release through both selection forms, capture custody after
source edits and reconstruction, unknown/corrupt rejection, whole-group capacity
rejection, and an operable recovery replacement from a crowded designation.

Check actual complete admitted input bytes as well as returned receipts. Include
accounts, preceding receipts, deduplication and native rendering. A scripted route
must identify which actual input supports each semantic next decision; do not
supply the report or repair through evaluator knowledge. Existing exact-source
guards and public checker remain unchanged.

Only a separately declared uncoached continuation or new attempt can establish
whether the policy turns acquired comparison evidence into saved, checked work.
Preserve the stopped attempt, consumed opportunities and cost. Evaluate useful
contribution, correction, termination and full inference cost; do not present
fewer reacquisitions or faster individual calls alone as a causal performance win.
