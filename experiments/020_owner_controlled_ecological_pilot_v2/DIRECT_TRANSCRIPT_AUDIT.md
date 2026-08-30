# Experiment 020 Direct Transcript Audit

## Review method

This is a condition-aware, post-seal corrective audit. It is not prospective
blinded review.

The primary agent directly inspected all 106 saved coding requests, rendered
inputs, endpoint outputs, private reasoning records, final JSON actions, and
tool results. The audit asks, for every decision:

```text
what Qwen saw
→ what Qwen said it inferred
→ what action it emitted
→ what the host returned
→ what that supports
```

`TRANSCRIPT_INDEX.json` binds the complete review surface. It records exact
artifact paths and hashes, visible event signals and observation rows, action,
result summary, usage, and reasoning excerpts for every call.

## Common model-facing decision frame

Every continuation request gave Qwen:

- the exact owner-authored task and active step;
- current candidate identity;
- completed-step state;
- calls used, calls remaining, and the 512-token reasoning budget;
- a task-independent hierarchical P0 root;
- a single monotonically ordered event frame;
- readable action targets, exact status/ranges, and candidate/file/check
  bindings;
- canonical payload addresses for exact reopening;
- observation identities with readable action/target and candidate binding;
- the compact legal action and check contract.

The frame explicitly said that a handle is an address rather than semantic
evidence, sequence records occurrence rather than completion, and the host
made no sufficiency or relevance judgment. X25 differed only in which old
exact payload bodies remained resident.

The evaluator, expected successor, hidden tests, and task-author rationale
were absent.

## Shared prefixes

### Source family

Both seeds followed the same useful early policy. Qwen read the first nine
required files exactly and kept an accurate checklist of what remained. Its
private reasoning identified the four boundary errors before pressure:

- `>= max_file_bytes` wrongly excluded equality;
- a post-append `> max_files` check admitted one extra file;
- `idx >= MAX_JSONL_LINES` excluded event line 1000;
- the same boundary excluded an embedded artifact on line 1000.

The authentic fork occurred after nine reads, with `policy.py` and
`readiness.py` still outstanding and no mutation accepted.

This matters qualitatively: the branch did not need metadata to discover the
defects after the fork. It needed to preserve exact audit progress and enough
source grounding to execute and close.

### Observation family

In both seeds Qwen saw two observation identities:

- `OBS-0001`, bound to an older candidate and labeled `legacy verifier smoke`;
- `OBS-0002`, bound to the current candidate and labeled
  `offline verifier safety`.

Qwen selected `OBS-0002` immediately and explicitly cited its exact candidate
binding. The reopened body said that absolute/parent paths were accepted and
timeouts behaved as though 60 were a minimum. Qwen correctly inferred the two
source errors, then read all ten required files before mutation.

The observation body carried real signal. It named the current failing suite
and failure classes, while exact source remained necessary to construct the
patch.

## Cell 01 — source, seed 173205

### R50

What Qwen saw: all nine shared read bodies plus the two missing audit
obligations. After reading both, it had the full resident source chronology.

What it did:

1. read `policy.py` and `readiness.py`;
2. emitted a patch to `importers.py` that only inserted a cosmetic blank line;
3. noticed the resulting diff in the next event frame and reread the file;
4. made the actual file-size/file-count repair;
5. reread `saved_runs.py`;
6. repaired both JSONL boundary checks;
7. passed `public` and submitted.

The cosmetic patch changed bytes and was therefore mechanically valid, but it
was not task-progress. Qwen recovered from its own action without host help.
The resulting candidate differed cosmetically from the exact donor and passed
the hidden grader.

### X25

What Qwen saw: the same readable progress plane, while old payload bodies
through sequence 1 and then later sequences moved to custody.

What it did:

1. read the two missing files;
2. noticed that the earlier complete `saved_runs.py` body was no longer
   resident and explicitly reopened canonical `RES-0001`;
3. read current `importers.py`;
4. repaired both importer boundaries in one patch;
5. read current `saved_runs.py` and repaired its two boundaries;
6. passed and submitted the exact donor-equivalent candidate.

The branch did not reopen everything. It selected a task-relevant external
body, grounded against current source before patching, and finished in the
same 19 conceptual calls as R50. It processed 292,404 prompt tokens versus
395,223 for R50, largely because R50 carried the large resident prefix through
every later request.

## Cell 02 — source, seed 223607

### R50

After the two remaining required reads, Qwen emitted an exact no-op replacement
to `importers.py`. The host returned a bounded `tool_rejected` result saying
the patch must change exact bytes. On the next turn Qwen explicitly recognized
the rejection, reread current source, applied the correct importer and
saved-run repairs, passed, and submitted.

This is useful protocol evidence: rejection was visible, comprehensible, and
recoverable without a retry or rescue.

### X25

Qwen again reopened canonical `RES-0001`, but was more conservative than in
cell 01. It additionally read `fixture_packs.py`, reread `saved_runs.py`, split
the importer fix across two mutations with an intervening read, and reread
`saved_runs.py` before its two mutations.

Nothing it reacquired was false or stale. The extra actions were confidence
and confirmation work caused by absent old bodies, not an inability to locate
the source. The branch still reached the same donor-equivalent candidate,
passed, and submitted with two calls left. It used 23 conceptual calls versus
18 for R50 and 373,256 prompt tokens versus 350,862.

The paired source result is therefore seed-dependent economically: X25 won
large in cell 01 and paid an acquisition premium in cell 02.

## Cell 03 — observation, seed 173205

### R50

The current observation body and the complete `verifiers.py` body remained
resident. Qwen directly patched timeout clamping and path rejection, ran the
check, and submitted in four continuation calls.

Its reasoning was exact: it identified Python's `and`/`or` precedence error
and replaced the lower-bound-only timeout expression with an inclusive clamp.

### X25

The event signal still said that `OBS-0002` was current and that all ten reads
were complete, but the old observation and `verifiers.py` bodies were
external. Qwen:

1. reopened current `OBS-0002`;
2. reopened canonical source result `RES-0002` for `verifiers.py`;
3. patched timeout clamping;
4. read the current relevant source slice after mutation;
5. patched path rejection;
6. checked and submitted.

It never selected stale `OBS-0001`. It used the readable target and candidate
binding to choose the current exact evidence. X25 added three conceptual calls
and 32,558 prompt tokens relative to R50, but reduced peak resident prompt
from 27,933 to 20,940 tokens.

## Cell 04 — observation, seed 223607

### R50

Qwen used the resident current observation/source, fixed timeout and path
safety in two patches, passed, and submitted in four continuation calls.

### X25

Qwen did not rely on the observation identity alone. It first reread complete
`verifiers.py`, then explicitly reopened `OBS-0002`. It patched path safety,
read two overlapping current source slices to locate/confirm the timeout
function, patched timeout clamping, checked, and submitted.

The path patch used an alternative but valid formulation with an explicit
empty-string guard. Hidden grading passed. The two source-slice reads were
conservative confirmation rather than missing host signal: the event frame
already recorded the earlier complete read and the current source was also
available from the first branch-local read.

X25 used four more conceptual calls and 46,544 more prompt tokens than R50,
while reducing peak prompt from 27,908 to 20,864 tokens.

## Cross-condition behavioral synthesis

### 1. Externalized exact custody preserved grounding

All four X25 paths completed, passed hidden grading, checked, and submitted.
No path used stale observation evidence or mutated before its required audit
was complete. The model could convert readable event identity into explicit
exact reacquisition and then into correct source-bound action.

### 2. Signal-bearing metadata helped, but presence did not imply sufficiency

The event frame gave Qwen truthful completion signals. Qwen understood them
well enough to avoid broad rediscovery, but it did not always treat them as
sufficient evidence for mutation. It sometimes reopened or reread exact
content that had already been completely acquired earlier.

That is the important model-side limitation:

```text
knowing that an exact read occurred
is not always the same as feeling grounded enough to act
```

Adding another completion flag would address the wrong problem. The signal
was already present and readable.

### 3. Observation identity was more locally actionable than old source-read identity

The observation directory described a small semantic choice: old smoke result
versus current verifier-safety result. Both seeds selected the correct current
record immediately.

The source event plane described a much larger evidence surface. When old
bodies were absent, Qwen sometimes paid extra reads to reconstruct confidence
about how several functions interacted. This suggests that identity rows work
best when their readable target corresponds to a discrete information need;
large generic source events remain useful orientation but weaker substitutes
for exact bodies.

### 4. Canonical identity fixed address indirection, not acquisition demand

No X25 path created a result-of-result handle chain. Reopens retained the
original canonical source. Yet Qwen could still request the same canonical
evidence or overlapping source more than once. Canonical identity solves
provenance and address stability; it does not tell the model that evidence is
semantically sufficient.

### 5. Low bounded reasoning was adequate

The 512-token private reasoning allowance was enough for Qwen to maintain the
audit checklist, compare candidate bindings, diagnose boolean precedence and
off-by-one errors, recover from a rejected action, and close all eight paths.
No transcript provides evidence that more reasoning was needed.

### 6. Resident-body and externalized-body economics cross over by trajectory

R50 was locally simpler whenever all relevant exact bodies still fit. X25
reduced every peak prompt but sometimes needed more calls. Across all pairs,
those effects almost canceled in cumulative prompt processing.

The appropriate product interpretation is not “externalize everything because
it is cheaper.” It is:

> Keep exact bodies resident while affordable; when pressure requires
> externalization, retain readable exact progress identity and let the model
> reacquire canonical evidence.

That is already the tested controller rule.

## Hypotheses earned for later ecological use

1. Candidate-bound readable observation rows support accurate stale/current
   choice without resident body text.
2. Externalizing broad source bodies increases confirmation/reacquisition
   variance even when progress signal is exact.
3. Peak-context savings can preserve executability without reducing total
   prompt processing; capacity and cumulative cost are distinct outcomes.
4. Canonical payload identity removes provenance ambiguity but will not by
   itself suppress rational or irrational reinspection.
5. A small hard-capped reasoning channel is sufficient for this controller's
   current source and observation decisions.

No new interface feature is justified by these transcripts. The next useful
evidence should come from deploying the frozen controller on more varied work,
not another metadata micro-ablation.

