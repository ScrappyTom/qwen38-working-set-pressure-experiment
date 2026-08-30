# Experiment 015 Direct Transcript Audit

## Review scope

The primary project agent directly reviewed all sixteen saved coding requests, exact progress surfaces, P0 and observation bindings, private reasoning outputs, assistant actions, and tool results. The per-call paths, hashes, metrics, actions, and results are in `TRANSCRIPT_INDEX.json`.

This was a condition-aware development audit. The fixtures were already exposed and their constructed candidates were deliberately hidden-correct before the live calls.

## What Qwen saw

Every branch began at the same kind of exact Phase-B decision point:

- the complete task and exact active user-authored Phase-B instruction;
- completed phase ID `A`;
- a current candidate-bound P0 root;
- exact observation identities and candidate bindings;
- five accepted progress events covering the already completed evidence acquisition, mutation, and required large reads;
- zero newly used calls out of a sixteen-call budget;
- public check capability and strict action schema;
- up to 512 private reasoning tokens.

In `D15-UNIFIED-DUP`, the five old events appeared as compact receipts. After the live check, that exact action/result also appeared in `history` while receipt sequence 6 repeated its mechanical identity.

In `D15-EVENT-FRAME`, all events appeared in one sequence. The first five result-body fields were external behind `RES-0001` through `RES-0005`; the live check became sequence 6 with its small stdout/stderr body resident. There was no `history` field and no parallel receipt ledger.

## Closure family

All four branches—both seeds under both placements—took exactly:

```text
check public on current candidate
→ submit current candidate
```

The single-frame reasoning directly enumerated events 1–5 and said the check and submit remained. After sequence 6 showed a current-candidate passing check, it submitted.

The legacy reasoning did the same using the receipt ledger. One seed, however, explicitly paused over the juxtaposition of `phase_calls_used: 0` and five completed receipts:

> This seems contradictory with having 5 entries in the ledger.

It then used the reconstruction notice to resolve the apparent conflict and chose the correct check. The single-frame branches did not express this progress-clock uncertainty. This is qualitative evidence that the old dual/resource presentation creates avoidable interpretive work even when it does not change the action.

Both event-frame seeds explicitly recovered the already-completed patch content from the richer exact event action. The legacy compact receipts exposed the patch path and candidate transition but not the full old/new strings. That difference is why the rehearsal cannot treat shorter reasoning or endpoint time as a pure placement effect.

## Stale-check family

All four branches correctly distinguished:

- sequence 1: a passed public check bound to predecessor candidate `224c11fe…`;
- sequence 3: the patch producing current candidate `502e49db…`;
- the active obligation to run a new check on `502e49db…` before submission.

Every first live action was the new current-candidate check. Every second action was submit after sequence 6 recorded that passing check.

Qwen's private reasoning repeatedly compared candidate identities rather than relying on action order alone. Typical reasoning was:

> The earlier passing check is bound to the predecessor candidate: run check `public` again on the repaired current candidate.

There were small verbal imperfections. In two second-turn traces, Qwen initially paraphrased sequence 1 as a check on “the current candidate” before continuing to identify sequence 6 as the actual repaired-candidate check. The strict action remained correct and candidate-bound. This is useful restraint: exact bindings supported the decision, but private narration was not perfectly stable.

## Reasoning and action quality

All sixteen actions were coherent with the exact visible state:

- eight current-candidate checks;
- eight current-candidate submissions;
- no source reopen, duplicate check, stale-check submission, or unrelated action;
- no protocol recovery or host correction.

The 512-token private-reasoning cap truncated some prose mid-sentence, especially in the stale-check submit turns. The structured action was still complete and correct. No later prompt retained the private reasoning.

## Token and timing observations

The single event frame used 33,758 cumulative prompt tokens versus 30,516 for the legacy presentation: 3,242 more, or 10.62%. It used 492 fewer completion tokens and 18.2 fewer endpoint seconds, but those differences are descriptive only.

The prompt increase is real and explainable. The new frame retains exact action arguments and structural result fields, whereas the externalized legacy prefix uses compact receipts. On these short already-completed prefixes, removal of one newly duplicated check pair did not repay the richer old-event encoding.

This is not evidence that duplication is desirable. It is evidence that “one plane” and “compact plane” are separate properties. The future controller should use one common event renderer in both branches, and its exact worst-case size must be stress-qualified before a large-world run.

## Qualitative conclusion

Qwen did not require the same progress fact to appear in both history and a receipt ledger. One monotonic event sequence was sufficient for:

- recognizing completed acquisition and mutation;
- recognizing the remaining check obligation;
- distinguishing a stale predecessor check from a required current check;
- recognizing a newly passed current check;
- submitting without confirmation loops.

The single-frame placement therefore clears the narrow comprehension risk. This rehearsal does not yet establish an efficient final encoding or a large-world context advantage.
