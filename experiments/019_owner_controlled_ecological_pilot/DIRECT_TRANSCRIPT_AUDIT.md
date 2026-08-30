# Experiment 019 Direct Transcript Audit

## Review scope

The primary agent read every one of the thirteen saved coding requests,
rendered-input custody records, endpoint responses, private-reasoning files,
assistant action objects, and tool results. `TRANSCRIPT_INDEX.json` binds the
review to their paths and hashes. This is a condition-aware corrective audit
of a partial run, not a blinded comparative review.

## What Qwen actually saw

Both exposed cells were the source task, under seeds 173205 and 223607. Every
request contained the exact task and active step; current candidate and call
budget; a root P0 row stating only that `src` contained 25 files and its total
size; an initially empty then monotonically ordered event frame; exact result
bodies resident during this pre-pressure segment; no observation entries; and
the compact tool contract with a 512-token private-reasoning allowance.

The task named `artifact_units.py`, `reopen.py`, `records.py`, and `hashing.py`
and stated both desired semantics verbatim. Qwen did not need P0 expansion,
search, or metadata inference. The dominant signal was exact authorized task
plus exact source.

## Cell 1 — seed 173205

| Call | Qwen action | Exact host result | Interpretation |
|---:|---|---|---|
| 1 | read `artifact_units.py` | complete lines 1-459 | Located the inclusive-end slice defect. |
| 2 | read `reopen.py` | complete lines 1-83 | Located `>= max_chars`. |
| 3 | read `records.py` | complete lines 1-460 | Satisfied mandated supporting inspection. |
| 4 | read `hashing.py` | complete lines 1-39 | Completed all required reads. |
| 5 | patch `artifact_units.py` | candidate advanced | Used `unit.end_line`. |
| 6 | reread `reopen.py` | complete, unchanged hash | Conservative current-source confirmation. |
| 7 | patch `reopen.py` | candidate advanced | Changed `>=` to `>`. |
| 8 | check `public` | passed on current candidate | Correct check binding. |
| 9 | submit | accepted with current pass | Correct closure. |

Qwen repeatedly and correctly explained Python's exclusive slice end and why
equality at `max_chars` is complete. At the final turn it used the ordered
event plane to enumerate both accepted mutations and the current passing check
before submitting.

The call-6 reread was unnecessary for correctness. Qwen explicitly noted that
`reopen.py` had not changed, then reread because the instruction required exact
*current* source. Candidate-wide version changes can make conservative
reacquisition rational even when a file hash is unchanged. One such call did
not impair the outcome and does not earn suppression or a new feature.

Cell 1 processed 100,547 prompt tokens cumulatively, peaked at 16,265 prompt
tokens, and passed the hidden grader after sealing. Its terminal candidate is
`5c7eba4fbad9c51325a9abc4f4b27c5b8d9eedb5b344558b5921915ed854a49f`.

## Cell 2 — seed 223607

Calls 1-3 repeated the mandated reads of `artifact_units.py`, `reopen.py`, and
`records.py`; exact bodies and hashes matched cell 1. Qwen's reasoning also
identified both correct edits before it acted.

At call 4, with 21 calls remaining, reasoning again derived the inclusive-end
correction but ended mid-sentence at `And then: material`. The final channel
contained a strict schema-valid patch whose `old` and `new` fields were the
same short prefix of `artifact_units.py`. The raw endpoint returned HTTP 200,
`finish_reason=stop`, and an ordinary JSON object.

This is model behavior, not malformed transport: the actor knew the desired
edit in reasoning but emitted a no-op action. The host returned an accepted
empty diff and unchanged candidate, then crashed while re-saving that exact
candidate. Under the corrected host this becomes a bounded rejection and
Qwen may respond next turn. The historical path is not reclassified as though
that continuation occurred.

Cell 2 contributed four exact completions and 27,549 cumulative prompt tokens,
but no scorable terminal candidate.

## Information-presentation findings

1. **Exact task signal dominated orientation.** The files and semantics were
   named; the P0 root was harmless but behaviorally unused.
2. **Exact bodies grounded the repair.** Both seeds quoted and correctly
   interpreted the actual faulty lines. No summary or relationship layer was
   needed.
3. **The ordered event plane supported closure.** Seed 173205 recognized both
   mutations and the current passing check without repeating them.
4. **Presence did not guarantee action quality.** Seed 223607 had the right
   facts and articulated the correct edit, yet emitted a no-op. Richer metadata
   would address the wrong failure.
5. **Candidate-wide change induced conservative rereading.** Keep measuring
   this policy; do not suppress it on one non-causal instance.

## Limits

No request externalized a payload. No R50 or X25 branch ran. No observation
directory was exposed. Qwen never used any reopen action. These transcripts
provide no new live evidence about canonical payload identity or the
resident-versus-externalized treatment.
