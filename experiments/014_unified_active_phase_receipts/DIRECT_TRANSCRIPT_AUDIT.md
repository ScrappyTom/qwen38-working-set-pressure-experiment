# Experiment 014 direct transcript audit

## Review scope

The primary project agent directly reviewed all 112 saved Qwen coding
requests, rendered prompts, private reasoning outputs, strict actions, and tool
results, plus all eight exact prospective requests denied before HTTP. Exact
per-call identities, hashes, prompt state, receipt state, reasoning excerpts,
actions, results, and runtime usage are indexed in `TRANSCRIPT_INDEX.json`.

This is a condition-aware post-seal review. Evaluator truth was unavailable to
the actor and was opened only after sealing.

## What Qwen saw

At every reconstructed turn Qwen received the same earned decision frame:

- exact full task and exact active user-authored step;
- completed phase ID `A`;
- exact current candidate and remaining call/token budget;
- small readable P0 orientation;
- candidate-bound observation identities;
- exact boundary receipt and compact tool contract;
- up to 512 private reasoning tokens, separately custodied and omitted from
  subsequent history.

Both conditions exposed the same exact action and result facts. The treatment
changed only whether post-reset actions also advanced the numbered receipt
plane.

## Shared prefixes

The four shared Phase-A prefixes used 30 completion calls. In every prefix Qwen
began, read both required 182-line records, read and repaired
`workflow/progress.py`, passed `prefork`, and called `fork_ready`. The two
closure prefixes also captured the required `integrity` observation. The
shared work was coherent and gave each pair identical ancestry.

## Closure family, seed 173205

Both branches followed the same seven-action path:

```text
reopen OBS-0002
→ read target
→ patch target
→ read both large records
→ check public
→ submit
```

The first Phase-B capacity guard fired just before the check. At reconstruction
Qwen saw receipts 1–5 and no recent history, correctly concluded that check and
submit remained, and closed. After the check, both the split history and the
unified receipt were sufficient in this seed.

This pair is an important restraint: the split representation can work. The
problem found in Experiment 013 was reliability, not literal information
absence.

## Closure family, seed 223607

Before reconstruction the paired branches were again identical. Qwen reopened
the marker, made the exact hidden-correct patch, and read both large records.
The next check request was denied before HTTP at 25k, causing the frozen
reconstruction.

### Split

The reconstructed ledger ended at receipt 5. Qwen ran `public`; the check
passed and its exact result appeared in recent history. On each subsequent
turn, the actor could see the growing chain of passing results. Its reasoning
even said variants of:

> the history already shows 3 public checks that passed

and later:

> the public check has been run many times already

It nevertheless treated the unchanged `complete_through_sequence: 5` as the
authoritative completion boundary and issued another check. By the final turn
it saw ten exact passing checks in history and still ran an eleventh. The branch
exhausted all sixteen Phase-B calls without submitting. Its final candidate was
hidden-correct.

This is a direct reproduction of the Experiment 013 two-clock failure on a
fresh case and seed.

### Unified

The first passing post-reset check became receipt sequence 6 while its full
result remained in recent history. On the next turn Qwen enumerated receipts
1–6, explicitly marked the public check complete, and submitted.

The paired difference was nine calls and 58,821 prompt tokens. More
importantly, the added receipt sequence changed the model's interpretation of
the same exact passing result from "possibly not active progress" to
"completed active-phase effect."

## Stale-check family, seed 173205

Before the in-phase reset, both conditions showed a separate behavior that is
not caused by the receipt treatment: Qwen ran the required initial V1 public
check three times before moving to source. Both then read the target and both
large records. The frozen first reset therefore externalized the same six
actions.

The split branch ran one more V1 check, reread the target body, mistyped the
candidate ID in its first patch, recovered with the exact ID, passed a check on
V2, and submitted in twelve calls.

The unified branch used `reopen_result(RES-0004)` for the exact previously read
target body rather than rereading the file. It still ran one extra V1 check,
then patched V2, ran a V2-bound check, and submitted in eleven calls.

The unified sequence saved one call and 3,619 prompt tokens, but did not remove
all redundant checking. Its real safety success was that it never confused the
old passing V1 check with authority to submit V2.

## Stale-check family, seed 223607

The two conditions were behaviorally identical until the receipt reset: three
V1 checks, target read, correct patch to V2, and both required large reads.

After reconstruction both ran a check bound to V2, reread the already repaired
two-line target, ran another V2 check, and submitted in eleven calls. The
unified ledger numbered the post-reset check and reread; the split surface kept
them in history. Both reasoned their way to the correct current check binding
and closure.

This pair shows that unified receipts are not a universal cure for redundant
confirmation. The model can still choose an unnecessary read or check even
when progress identity is unambiguous.

## What the transcripts establish

### One progress clock removes a real ambiguity

The strongest paired evidence is closure seed 223607. Exact check output was
already present in split history; Qwen repeatedly acknowledged it and still
discounted it because the numbered progress ledger had not advanced. Adding
the same check as receipt 6 caused immediate submission.

This supports the causal interpretation from Experiment 013: the failure was
not missing evidence, lack of reasoning, or checker uncertainty. It was the
presentation of one active phase through two progress clocks.

### Unification is safe under candidate change in these paths

Every stale-check branch distinguished checks by candidate binding. All four
submitted only after a current V2 check. A monotonic ledger records progress;
it does not declare an effect current independently of its binding.

### Receipts help mechanical continuity, not general planning

The stale family still contained repeated checks and redundant reads. Before
the first reset, both conditions ran the initial check three times because no
receipt treatment difference existed yet. After reset, unified presentation
did not always prevent another confirmation action.

The correct claim is narrow: one receipt sequence makes completed effects less
ambiguous across reconstruction. It does not make Qwen optimally economical or
eliminate every repetition.

### Exact bodies can remain off the progress plane

The ledger needed action identity, binding, acceptance, pass/range/hash/size
fields, and a reopen handle—not resident large bodies. Qwen used one exact
result reopen in the stale seed-173205 unified branch; otherwise compact
receipts were sufficient to decide what had mechanically happened.

## Audit conclusion

`T25-UNIFIED` preserved hidden quality, submitted 4/4 versus 3/4, and eliminated
the fresh replicated split-ledger check loop. Across all four pairs it used ten
fewer branch calls and 61,133 fewer prompt tokens, although almost all of that
aggregate advantage comes from the single avoided loop.

The earned architectural statement is therefore precise:

> Maintain one monotonically sequenced exact active-phase action/effect ledger.
> Keep result bodies separately demand-loaded and preserve candidate/environment
> validity bindings. Do not infer that this alone solves planning or redundant
> confirmation.
