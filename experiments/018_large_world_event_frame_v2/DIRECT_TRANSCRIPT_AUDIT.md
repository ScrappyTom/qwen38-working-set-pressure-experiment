# Experiment 018 Direct Transcript Audit

## Audit identity and coverage

- reviewer: Codex primary project agent
- mode: condition-aware, post-seal direct behavioral and host-path review
- actor: Qwen3.8-27B AD-IQ2_S
- reasoning: server-capped at 512 tokens, separately custodied, omitted from
  later history
- coverage: every saved coding request, rendered prompt, endpoint response,
  private-reasoning record, strict action, and tool result for all 87 live
  completions

`TRANSCRIPT_INDEX.json` binds each reviewed call to its artifact hashes and
records the signal-bearing event fields that were visible before the action.
This audit is based on those exact inputs and outputs, not summaries alone.

## What Qwen actually saw

Every request contained:

- the full exact task and active user-authored step;
- the current candidate ID and remaining call/reasoning budget;
- one monotonically sequenced active-phase event frame;
- readable action targets, ranges, completion/pass status, and exact
  candidate/file/check bindings for every event;
- result/action payload field names, size, hash, residency, and exact access
  handle;
- a task-independent hierarchical P0 root;
- a candidate-bound observation identity directory where applicable;
- the compact action contract and legal public check ID.

It was explicitly told that handles are addresses rather than evidence and
that event occurrence is not semantic sufficiency.

At the authentic fork, paired R50 and X25 branches inherited the same events
and candidate. R50 kept all payload bodies resident. X25 removed only the
oldest bodies required by the exact tokenizer guard; the action type, readable
target, ranges/status, bindings, and payload identity remained present.

## Paired transcript paths

| Cell | Condition | What Qwen saw and did | Terminal interpretation |
|---|---|---|---|
| source / 173205 | R50 | completed `required_00`, completed `required_01`, completed `required_02`, then opened the first page of `required_03` | next exact fully resident request was denied at 55,139 prompt tokens; no mutation opportunity |
| source / 173205 | X25 | completed all ledgers; expanded `policy`; read policy and primary; patched primary dynamically; changed policy; reacquired it; read/patched secondary; ran check; read primary after diagnosing the failed invariant | controller preserved enough progress to reach check; actor misread snapshot semantics and lacked calls to repair/close |
| source / 223607 | R50 | same coherent sequential ledger acquisition | same physical stop before mutation |
| source / 223607 | X25 | completed ledgers but later falsely classified completed `required_00` as incomplete and reread its terminal page; patched primary dynamically; changed/reacquired policy; patched secondary | one no-new-information action plus semantic misinterpretation consumed the budget before check |
| observation / 173205 | R50 | selected current `OBS-0002`, obtained `HARBOR-K9`, then acquired required ledgers sequentially | physical stop before source mutation |
| observation / 173205 | X25 | marker absent at fork; reopened exact result, completed ledgers, reopened the reopen after it aged out, read label/footer, patched both with `HARBOR-K9`, checked, submitted | hidden-correct recurrent exact-body use; two extra reopen actions and one duplicate ledger page |
| observation / 223607 | R50 | independently selected current `OBS-0002`, obtained marker, and acquired ledgers | physical stop before mutation |
| observation / 223607 | X25 | marker absent at fork; reopened exact result, later reopened canonical observation again after the body aged out, read and patched label/footer, checked, submitted | hidden-correct replication; cleaner than nested result reopening but still two post-selection acquisitions |

## Source family: exact qualitative path

Both seeds tracked the four 226-line ledgers accurately through most of the
trajectory. The maximal exact paging contract made each ledger a predictable
210/16-line pair. R50 simply accumulated the bodies until the next request
could no longer fit. It never got a model opportunity to inspect or modify the
policy/API files.

X25 preserved the structural event records while progressively externalizing
large ledger bodies. Both seeds could still enumerate the required files,
continue from the exact `next_start_line`, locate `policy/current.py` through
P0, and bind patches to current candidates and file hashes.

The substantive mistake was shared. Qwen implemented:

```python
from policy.current import active_prefix

def normalize_primary(value: str) -> str:
    return active_prefix() + value.strip().casefold()
```

It then changed the policy to `quartz-`. The public check correctly exposed
that primary had not *preserved* the earlier `ember-` value. Cell 01's private
reasoning then said, in substance, that the original value needed to be frozen
rather than dynamically read. This diagnosis occurred after the check, showing
that current task, current candidate, and exact failure evidence were coherent.
The actor had only one action left.

Cell 02 did not reach the check. Its most important lapse occurred earlier.
The exact request visibly contained complete terminal events for
`required_00.py` and `required_01.py`; nevertheless its reasoning called them
incomplete and it reread `required_00.py:211`. This was not an opaque-handle
problem. The readable completion signal was present but not integrated.

## Observation family: exact qualitative path

The initial directory listed an older marker observation bound to a predecessor
candidate and `OBS-0002` bound to the current candidate. Both seeds selected
`OBS-0002` on their first shared call and obtained `HARBOR-K9`. No host field
said “current” or previewed the marker body; Qwen compared candidate IDs.

At the X25 fork, the literal marker was absent from both first branch coding
requests. The event frame still said that sequence 1 was an accepted
`reopen_observation` of `OBS-0002`, provided its exact body hash/size, and named
`RES-0001` as the exact body address. Both seeds used that lead.

Cell 03 reopened `RES-0001` immediately. By the time it needed the marker for
mutation, that reopen's result body had itself aged out, so it followed the
newer `RES-0005` address. It also reread the terminal page of
`required_01.py` despite visible completion. Even with those costs, it patched
both files, passed, and submitted on its eighteenth and final action.

Cell 04 delayed differently. It reopened `RES-0001`, continued acquisition,
then invoked the original `OBS-0002` again once the body was absent. It patched
both files, passed, and submitted in seventeen actions. This is the cleaner
behavioral demonstration: readable observation identity led to exact body
reacquisition without stale selection.

Both terminal candidates used the exact recovered marker:

```python
return "HARBOR-K9::" + value.strip().upper()
return "HARBOR-K9::" + value.strip().casefold()
```

The current exact fact therefore crossed pressure, was reacquired by the model,
and materially determined the hidden-correct mutation.

## Reasoning/action alignment

Private reasoning generally mirrored observable state:

- it tracked exact ledger continuation lines;
- it compared observation candidate bindings;
- it counted remaining actions and reserved check/submit in several paths;
- it named `HARBOR-K9` only after exact body access;
- it updated candidate IDs after each accepted patch;
- it recognized public-check success before submission;
- after the source check failure, it identified the dynamic-versus-snapshot
  semantic error.

The deviations are equally informative:

- one source branch and one observation branch reconstructed already-complete
  ledger pages incorrectly despite resident signals;
- both observation branches reacquired the same exact marker twice because
  they acquired it too early for later use under continued externalization;
- one branch treated the newer address created by reopening as the next thing
  to reopen, producing an address-of-address chain;
- both source branches budgeted an ideal path tightly but did not reserve room
  for semantic correction after a failed check.

These are local information-policy and closure-economics failures, not evidence
that the model lacked the task, candidate, or readable event signal.

## What the event frame contributed

The causal mechanism supported by the observation paths is:

```text
readable current observation identity and binding
        ↓
model chooses exact address
        ↓
host returns exact body
        ↓
model interprets marker
        ↓
candidate-bound patch → check → submit
```

The marker was not resident at the X25 fork. A handle alone would not have told
Qwen which observation was relevant. The readable action/type/target and exact
candidate binding provided the signal; the handle supplied custody access.

The source paths support a different conclusion. Structural progress signal
usually worked, but one seed failed to fold a long event list into completed
file state. Presence of exact fields is necessary but does not guarantee that
the model will integrate them reliably.

## Qualitative hypotheses carried forward

1. A single exact event plane can support large-world continuation without a
   resident transcript or model-authored summary.
2. Candidate-bound readable identities are sufficient leads for exact dynamic
   evidence selection in the tested geometry.
3. Canonical exact-body addresses should remain stable across repeated access;
   generated handles for reopen results create avoidable acquisition chains.
4. Long event lists can preserve truth yet still impose tracking burden. This
   study does not earn semantic summarization, but it does motivate treating
   exact mechanically derived current state separately from bulky payload
   custody in an ecological implementation.
5. Check-and-correct headroom is part of capability. A path that only fits the
   ideal action sequence is not robust even when grounding is preserved.

