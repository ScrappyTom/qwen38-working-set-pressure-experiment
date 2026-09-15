# Shared decision-state explanation implemented and qualified

The architecture and plan were committed and pushed first at **3c143bae**. The
implementation adds the reviewed distinction to the common operating reference,
which is included by both ordinary and contribution request builders. No task
SYSTEM.txt, stored model input/output, operation schema, selection policy, edit
guard, checker, or allowance changes. This tranche sends zero Qwen completion
requests. Historical verifiers continue to require their pinned source revisions.

## What changed and why

The actual C05 input puts selected source and saved rejection results in
`latest_feedback` while the separate `working_set` lists are empty. Qwen's first
consultation response repeatedly treats that arrangement as contradictory states,
then ultimately uses the visible content. Its earlier C04 action also selects RES
rejection reasons while its discussion seeks proposed patch code. These are direct
input/output observations, not deductions from action acceptance or token counts.

The shared reference now says:

> The complete working set is all information presented in this call. Selected
> current source and saved-record objects already displayed in latest_feedback
> are omitted from the separate working_set lists, which contain the remaining
> selected material. A saved capacity rejection describes the complete proposed
> next input at that earlier attempt, not a fresh measurement after selection or
> other input changes.

This is the selection consultation's candidate plus the architecture's complete-input
definition. The capacity explanation develops Qwen's suggestion after source checking;
the selection explanation is reviewer-authored from its observed confusion. It does
not declare arbitrary feedback selected, automatically retain a wanted proposal,
refresh old guards, choose supporting source, or establish assertion correctness.

The single implementation is `INPUT_INTERPRETATION` in
[`working_view.py`](../../../src/working_set_exp/working_view.py). It is placed in
the shared reference, rather than copied into another task-specific prompt. Existing
`workspace` and `working_set` keys keep their compatibility meanings. The
[architecture map](../../../ARCHITECTURE.md) distinguishes these fields from the
complete model input and records the unresolved semantic-selection/account policies.

## Input cost and the adverse boundary

The native offline tokenizer verifies the original recorded counts before measuring
the added text. Five baseline/revised pairs preserve exact request/native bytes:

| Input | Original | Revised | Added | Revised fits 23,808 |
|---|---:|---:|---:|---|
| Pending-contribution C01 | 22,847 | 22,914 | 67 | Yes |
| Pending-contribution C02 | 23,039 | 23,106 | 67 | Yes |
| Pending-contribution C05 | 4,765 | 4,832 | 67 | Yes |
| Earlier source-page boundary | 23,762 | 23,829 | 67 | No: 21 over |
| Constructed empty selection from C05 | 3,406 | 3,473 | 67 | Yes |

The boundary case retains its older tool contract and adds only this explanation.
It is a textual cost projection, not a replay of that old action under all current
host changes. The empty-selection case is constructed, not an observed model call.
The three pending-contribution cases are exact saved inputs with only the declared
system-reference addition. No padding, budget increase, or automatic source removal
is used to hide the cost. A near-limit historical input no longer fits with this
addition; future preparation must use the actual revised native input.

Physical context remains 56,576 and the prospective generation reserve 32,768.
These measurements concern input capacity, not generation completion, GPU capacity
under inference, or whether clearer wording saves model time. The cost screen uses
ten offline vocabulary tokenizations and launches no server.

## Actual contribution route with revised native admission

The route reuses the earlier researcher-scripted assembled C04 checkpoint and
EVT-0071 proposal. It does not rescue or replay the latest pending-contribution C05
as a model outcome. Its source selection, exact patch, documentation and action
order are supplied by the existing offline qualification.

| Scripted request | Operation and outcome | Next input tokens |
|---|---|---:|
| Q1 | Select the exact proposal with its implementation, test and documentation support | 12,691 |
| Q2 | Save that exact test proposal | 15,443 |
| Q3 | Save documentation and execute the requested check on the actual successor | 17,949 |
| Q4 | Submit the checked current candidate | 15,722 |

The initial broad input is 22,899 tokens. Four scripted requests execute five
operations within the original remaining four requests/eight operations. Every
operation succeeds; proposal and base formatter remain visible, the saved tests
survive the documentation edit, and the final candidate is byte-identical to the
preceding qualified artifact:
`5b7b3b06f55935d950317fedce9add1d481c56e15d29158e2a38ddeda369131d`.

Direct review covers the actual proposed tests, documentation, operation results,
check report, and runtime/custody records. The current check passes: the original
359-test suite and edited 377-test suite each have five skips and no failures or
errors; prior work is preserved. The documentation explains real failing lookups,
raw retrieval and supplying the missing value, with executable examples. This is
repeated offline artifact qualification, not a new model score or proof of an
optimal selection. The route has no generated model response.

Six complete inputs are rendered and tokenized by the actual runtime through only
`/apply-template` and `/tokenize`. Exact replay verifies all four replies, five
operations, state transitions, final artifact, wire inputs, 61 custody records and
276 source identities. The owned runtime closes normally; sampled free GPU memory
reaches 315 MiB under the accepted advisory policy. No decoder inference workload
is qualified by that memory observation.

## Tests, evidence, and decision

**88 selected tests pass**, including four focused tests for shared-request isolation,
selection/feedback transitions, visible-but-unselected feedback, and historical
rejection preservation after later success. Existing checks cover partial retrieval,
stale bindings, edit eligibility, capacity, grouped action access, actual successor
checks and runner behavior. This is not the full repository suite. The mock endpoint
messages in the unit-test output are simulated responses, not Qwen requests.

Evidence: [input cost](input-cost-001/RESULTS.json),
[route](contribution-001/QUALIFICATION.json),
[exact route verification](CONTRIBUTION_VERIFICATION.json),
[selected tests](selected-tests-001.txt). Reproduce with the commands in
[`qualify.py`](qualify.py); its `verify` mode replays saved evidence without new
native or completion calls. Creation paths are write-once.

Retain this as a prospective documentation clarification in the development host.
Its truth and bounded contribution feasibility are qualified; behavioral benefit
is untested. The demonstrated selection problem remains open. Next prepare a
completed-contribution evaluation in which Qwen must recover intended work and
obtain its support through the declared tools, preserve the work through changing
selection, consume actual verification, and finish without coaching. Judge that
whole loop and its cost. Do not start another wording-only comparison or silently
add semantic selection, a working account, or an automatic retry.
