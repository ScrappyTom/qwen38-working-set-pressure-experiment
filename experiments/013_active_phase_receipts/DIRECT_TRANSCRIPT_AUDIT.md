# Experiment 013 direct transcript audit

## Review scope

The primary project agent directly reviewed all 134 saved Qwen coding requests,
rendered prompts, private reasoning outputs, strict JSON actions, and tool
results, plus all fourteen prospective requests denied before HTTP. The exact
per-call identities, hashes, model-visible history, receipt state, reasoning
excerpts, actions, results, and runtime usage are indexed in
`TRANSCRIPT_INDEX.json`.

This is a condition-aware post-seal review. Hidden grading was not available to
the actor and was opened only after the response seal.

## What Qwen saw

At every reconstructed Phase-B turn, Qwen received:

- the exact full two-phase task;
- the exact active user-authored Phase-B text;
- completed phase ID `A`;
- the exact current candidate ID;
- remaining Phase-B calls and the 25,000-token ceiling;
- a small hierarchical P0 root;
- candidate-bound observation identities;
- the exact latest boundary binding;
- the compact tool contract;
- up to 512 private reasoning tokens, omitted from subsequent history.

`T25-LATEST` additionally saw only the latest retained exact action/result pair
after each in-phase capacity reset.

`T25-RECEIPTS` saw a bounded receipt ledger for every action externalized at the
last reset. Each receipt gave action/target identity, acceptance, relevant
candidate/file/range/pass fields, result hash and size, and an exact `RES-####`
reopen handle. New post-reset action/result pairs remained in ordinary history.

## Shared prefixes

The four shared Phase-A prefixes used 30 completion calls. In every prefix Qwen:

- began the task;
- read both large Phase-A records completely;
- read and repaired `workflow/progress.py`;
- passed `prefork`;
- produced the required probe where present;
- called `fork_ready`.

The shared prefixes were coherent and supplied identical branch ancestry. Their
442,510 prompt tokens are not attributed to either paired treatment because
each prefix was executed once and then forked.

## Pair 1 — source continuity, seed 173205

### T25-LATEST

Before the first in-phase reset, Qwen used readable orientation, read
`policies/current.py`, extracted `lumen-`, read `api/name.py`, made the correct
candidate-bound repair, and read both required records completely.

After that work left active history, Qwen could still see the correct patched
candidate but no compact fact that the governing source and both large reads
had already been completed. It reacquired the policy, target, and one record.
After the next reset it did the same again and read the other record. Fourteen
calls ended without a public check or submission. The final candidate was
hidden-correct.

### T25-RECEIPTS

Qwen performed the same governing-source acquisition, correct patch, and two
complete reads. At the reset it saw seven compact receipts. Its private
reasoning explicitly enumerated the completed search/P0/read/patch/read/read
sequence and concluded that only check and submission remained.

It passed `public`, unnecessarily ran the same passing check once more, then
recognized both passing results in ordinary history and submitted. It used ten
calls and produced the same hidden-correct candidate.

## Pair 2 — source continuity, seed 223607

### T25-LATEST

The second seed again found `lumen-`, made the correct repair, and completed
both large reads before reconstructing. It then repeated policy, target, and
record acquisition across two more resets and exhausted fourteen calls without
checking or submitting. Its candidate was hidden-correct.

### T25-RECEIPTS

The receipt branch completed the correct mutation and required reads in seven
calls. After reconstruction it used `reopen_result(RES-0002)` once to retrieve
the exact previously read P0 result, even though the compact receipts already
described progress. It then passed `public` and submitted in ten calls.

This was the only `reopen_result` action in all four receipt branches. The
result is important: exact bodies remained available, but Qwen generally did
not need them to reconstruct mechanical progress.

## Pair 3 — observation continuity, seed 173205

### T25-LATEST

Qwen correctly selected candidate-bound `OBS-0002`, reopened the exact
`D4::` marker, and read `codec/label.py`. Its first patch used a fabricated
candidate ID and was rejected. It read the exact target again, recovered with
the correct binding, and made the hidden-correct repair. It then completed both
large records.

Across later resets it repeatedly reopened the same exact observation and
reread the target or records. It exhausted fourteen calls without checking or
submitting. The correct candidate survived every reset.

### T25-RECEIPTS

Qwen reopened `OBS-0002`, read the target, made the correct patch, and read both
records in five calls. At reconstruction, the ledger showed those five exact
accepted actions. Qwen correctly concluded that check and submission remained
and passed `public`.

The next request also showed that passing check in ordinary history. Qwen
noticed it, but then reasoned that the numbered receipt ledger still ended at
sequence 5 and therefore the check might be from before the reset or otherwise
not part of the active phase. It reran the check. This repeated on every
remaining turn. Nine checks passed; no submission occurred.

The actor was not missing the check output. It explicitly quoted or paraphrased
`passed: true`, then discounted it because it did not appear in the numbered
ledger.

## Pair 4 — observation continuity, seed 223607

### T25-LATEST

Qwen again selected the correct observation, made the exact hidden-correct
patch, and completed both large reads. Subsequent resets caused repeated
observation reopening and source reacquisition. It exhausted fourteen calls
without checking or submitting.

### T25-RECEIPTS

The second seed reproduced the receipt behavior exactly: five correct
pre-reset actions, followed by nine consecutive passing public checks and no
submission. Its reasoning repeatedly distinguished the fixed five-entry ledger
from the growing post-reset history and treated ledger absence as if it
overrode the visible passing check results.

The replication across two frozen seeds makes this a systematic
model/interface interaction rather than a random malformed response.

## What the transcripts establish

### Compact exact progress is useful

In all four receipt branches, Qwen reconstructed the pre-reset work accurately.
It did not redo the governing observation, patch, or large reads. All four
reached and passed the public check. The latest-result branches reached none.

This directly supports the Experiment 012 hypothesis that invisible
non-mutating work—not loss of task meaning or candidate state—was the missing
input.

### Result bodies do not need to stay resident by default

Twenty-four receipts were externalized across the four branches. Qwen reopened
only one body. In the other three branches it moved from identities and
mechanical completion fields directly to checking. Large exact bodies remained
available without imposing recurring prompt cost.

### One active phase should not have two ambiguous progress clocks

The observation failures show the residual problem. Qwen interpreted the
numbered ledger as the authoritative progress clock and ordinary history as
potentially historical or otherwise uncommitted, even though the request
contract identified it as post-reset history.

The model's inference was conservative but wrong. The interface made it
possible by failing to give post-reset action/result pairs the same monotonic
phase sequence identity as externalized receipts.

### More reasoning is not the evident remedy

Private reasoning was already enabled and hard-capped. The failed observation
branches repeatedly articulated the exact completed work, the passing check,
the remaining submit obligation, and the remaining call budget. The failure
was not lack of deliberation; it was an unstable interpretation of two exact
progress surfaces.

### The host should expose facts, not decide sufficiency

Nothing here earns a semantic summary or host-selected next action. The narrow
earned correction is mechanical: keep one ordered receipt identity for every
completed action in the active phase. Qwen should still decide whether a
receipt is sufficient, whether a result body needs reopening, and whether to
check or submit.

## Audit conclusion

`T25-RECEIPTS` materially improved grounded progress continuity, reduced
reacquisition, and enabled all four branches to reach a passing public check.
It fully closed both source branches.

The exact v1 presentation is not yet reliable for closure because its ledger
freezes at the last reset while newer effects live in a separate unsequenced
history. The observation pair exposed a deterministic check loop. This is the
next precise information-presentation gap; it is not evidence for richer
metadata or semantic memory.

