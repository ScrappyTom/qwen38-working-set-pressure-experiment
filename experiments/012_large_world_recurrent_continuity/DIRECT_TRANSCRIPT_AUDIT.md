# Experiment 012 direct transcript audit

## Review method and coverage

The primary agent directly reviewed all 129 saved coding requests, rendered
prompts, private reasoning outputs, strict JSON actions, results, candidates,
and following host decisions. Sixteen additional prepared requests were
reviewed from their pre-HTTP coding request, endpoint request, rendered prompt,
and capacity record. `TRANSCRIPT_INDEX.json` binds every reviewed artifact by
SHA-256.

Review was condition-aware and post-seal. Hidden grading was opened only after
the response seal. The actor was Qwen3.8-27B AD-IQ2_S, reasoning was enabled but
hard-capped at 512 private tokens, and sampler/seed/runtime settings remained
those in the frozen runtime profile and schedule.

## What Qwen saw

Every active request exposed an exact mechanical decision frame:

- the full verbatim four-phase task;
- the exact active user-authored phase;
- completed phase IDs;
- current candidate identity;
- remaining phase calls and active token ceiling;
- a complete top-level P0 root with eighteen readable directories;
- deterministic `p0_page` access to directory entries and file outlines;
- identity-only dynamic observations with action, readable target, candidate
  binding, size, digest, and reopen handle;
- exact available tools, checks, probes, and their argument contracts;
- current history under either append-only or reconstructed semantics.

The model did not see hidden graders, known-good patches, task-aware ranking,
semantic summaries, relationship graphs, embeddings, or host-selected relevant
files.

At a T25 in-phase reset, Qwen saw the exact current candidate and the last full
action/result pair. Older in-phase action/result pairs were absent. The request
said older chronology remained externally custodied, but it did not enumerate
compact receipts for those absent actions.

## Shared Phase A

Qwen handled all four shared prefixes cleanly. It followed the user-authored
order, completely read both required A ledgers, inspected
`workflow/progress.py`, made the exact `0 -> 1` repair, checked, and forked.
Observation cases also probed compatibility before forking.

Private reasoning consistently identified the governing file, exact mutation,
remaining check, and stopping action. External actions followed that plan.
There was no restart, stale binding, speculative file mutation, or post-check
wander.

The actor occasionally discussed using P0 even when the task already supplied
an exact path. Only one shared path actually spent an extra P0 call on
`records_a`. This was a small orientation preference, not an outcome-level
problem.

## Source continuity: C50

Both append-only actors used readable structure to locate the policy source.
One expanded `api` and `policies`; the other expanded only `policies`. Both read
the exact `POLICY_PREFIX = "orbit-"` definition, read `api/name.py`, and
produced the same exact repair:

```python
from policies.current import active_policy_prefix


def normalize_name(value: str) -> str:
    return active_policy_prefix() + value.strip().casefold()
```

Both then completely read the two required B ledgers, ran the public check, and
forked. Their private reasoning correctly tracked every outstanding obligation.

In Phase C, one seed chose the first C ledger before rereading the current
policy; the other reread the policy and then the ledger. Neither had enough
physical context to complete the phase. The first prospective request after
those observed calls was denied by the 50,176-token guard.

This is a useful control result: full chronology preserved in-phase progress,
but could not support the whole long task physically.

## Source continuity: T25

Before the first in-phase reset, both T25 actors were semantically successful:

- they found and read `policies/current.py`;
- they read the exact target source;
- they produced the same correct Phase-B patch as C50;
- they completely read both required B ledgers.

The next prospective request could not fit under 25k because the two large read
results were still in history. The host reset the active frame to the latest
pair. In both seeds that latest pair was the second ledger read.

After reset, Qwen correctly understood that Phase B remained active and that
one displayed ledger read was complete. It could no longer see that it had
already:

- located and read the policy source;
- read the target before mutation;
- applied the correct patch;
- read the other required ledger.

The current candidate made the patch effect discoverable, but the completed
reads had no candidate-state footprint. Qwen therefore began reconstructing
the phase from the one visible pair. Seed 173205 expanded `policies`, reread the
policy and target, then reread ledger 000. Seed 223607 used a literal search,
expanded `policies`, reread the policy and target, then reread ledger 000.

A second reset again retained only the latest ledger pair. The actors repeated
the same acquisition pattern. Near the end, the reasoning explicitly compared
the visible three-action history with `phase_calls_used = 13` and concluded
that earlier calls must have occurred but were not shown. It nevertheless had
no exact receipt stating which obligations those hidden calls had completed.
The only epistemically safe action was another read.

Both source T25 candidates remained Phase-B correct. Neither reached check or
fork because fourteen actual model calls were consumed by duplicated
acquisition.

## Observation continuity: C50

At Phase-B entry, both append-only actors selected `OBS-0002`, whose candidate
binding matched the phase-entry candidate, reopened the exact body, extracted
`A3::`, read `codec/label.py`, and made the correct patch.

One seed reopened the same observation two additional times despite its exact
body remaining visible. This is genuine model over-confirmation. It did not
change the selected marker or candidate and did not prevent closure under the
50k control. The other seed spent one extra P0 page on `codec` and then
continued normally.

Both actors read the required B ledgers, checked, probed again, and forked. The
new probe produced `OBS-0005` bound to the current Phase-B candidate with marker
`B6::`.

At Phase-C entry, both private reasoning traces explicitly compared observation
candidate IDs, selected `OBS-0005` rather than stale `OBS-0002`, reopened it,
and used `B6::` in the exact `codec/header.py` mutation. Their external actions
matched the reasoning. Both resulting candidates passed the frozen Phase-C
checker after sealing.

Each actor then read one required C ledger. The next request was physically
denied before check/probe/fork. Thus candidate-bound observation selection and
evidence-to-action succeeded; append-only capacity prevented closure.

## Observation continuity: T25

The first reconstructed segment was also semantically successful in both
seeds. Qwen:

1. selected and reopened `OBS-0002`;
2. extracted exact marker `A3::`;
3. read `codec/label.py`;
4. produced the correct patch;
5. completely read both B ledgers.

The next request was denied at 25k. The fresh frame retained only the second
ledger body. Qwen still saw the persistent observation directory, but no
receipt that the observation had already been reopened, the first ledger had
already been read, or the target had already been patched.

Across later segments, each actor reopened `OBS-0002` four times total. Each
read ledger 000 three times and ledger 001 twice. One reread the already-correct
two-line label once. These actions were not random: each was locally justified
by the incomplete displayed history. The model repeatedly rebuilt the missing
obligation set, then another large exact result caused another reset.

Neither T25 actor confused `A3::` with a different marker or generated an
incorrect patch. Both final candidates passed the Phase-B checker after seal.
They failed to reach check/probe/fork before the fourth in-phase capacity
denial.

## Reasoning versus action

The 512-token private reasoning budget was enough for the actor to identify:

- the exact active phase and remaining obligations;
- the governing policy or observation;
- the correct target and mutation;
- the need for complete required reads;
- candidate bindings and check/fork closure;
- the shrinking action budget.

Observable actions generally followed those plans. The main mismatch was not
between reasoning and action; it was between the model's accurate local plan
and incomplete model-visible progress state after reconstruction.

The actor sometimes wrote that it could perform independent reads "in
parallel", but every final output remained exactly one valid action. It also
occasionally re-explained an already-correct target after rediscovery. No such
language caused a malformed or rejected action.

## P0 behavior at larger scale

The hierarchical P0 root stayed small despite 160 files and more than two MiB
of exact source. Qwen used directory names and sizes to choose `policies`, then
resolved `policies/current.py` without scanning distractor modules. It also
used `api` or `codec` pages occasionally.

The study does not fully qualify unknown-target discovery at repository scale.
Most ledger and mutation paths were verbatim in the user-authored phase text,
and `policies` was a strongly named one-file directory. What is supported is
that hierarchical P0 did not confuse the actor or force broad irrelevant
source acquisition.

## Central qualitative finding

Qwen did not fail because the large world obscured the semantic facts. It found
the right facts and made the right mutations in every branch. It failed because
the reconstructed frame represented current purpose and world state but not
the exact history-derived progress of a partially completed active phase.

The missing object is mechanical, not semantic:

```text
accepted action identity
+ target/path/handle/range
+ candidate/file/result binding
+ complete/accepted status
+ exact body hash and reopen handle
```

The full evidence body can remain in external custody. A compact ledger of
these exact receipts would tell Qwen which obligations are already satisfied
without summarizing what the evidence means or suppressing a model-requested
read.
