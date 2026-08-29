# Experiment 009 focused live rehearsal: direct transcript audit

## Evidence status

This is a condition-aware, post-seal audit of the fresh development-only
`E9-DEV-OBS-EPSILON` rehearsal. It is not measured evidence. The actor never
saw either measured Experiment 009 case.

The response tree was sealed before evaluator truth was opened. The preserved
seal contains 59 files and has aggregate SHA-256
`aa52197a321bab1b4482f18740711f3f996ce552c4e06ebb6b043fbac68402af`.
Post-seal hidden grading passed on candidate
`9c7a8776a94a10701ac34b40d363042bb404c59e4bbf29b55789e3c45b18aa54`.

Every one of the five saved coding requests, rendered prompts, endpoint
requests, endpoint responses, private-reasoning traces, assistant actions, and
tool results was read directly for this audit.

## What Qwen saw at reconstruction

The host projected the exact active Phase-C instruction, current candidate ID,
ordinary tool contract, P0 orientation, and a mechanically complete observation
directory. The directory did not call either record relevant or stale. It gave
two exact bindings:

| Handle | Bound candidate | Sequence | Body disclosed initially? |
|---|---|---:|---|
| `OBS-0001` | `e20a8505...1b08f` | 1 | no |
| `OBS-0002` | `df0dd441...da8b2` | 3 | no |

The reconstructed current candidate was `df0dd441...da8b2`. The active step
said an older observation existed, required the exact marker valid for the
current candidate, and required reopening exact evidence before mutation. It
did not name the correct handle or disclose either marker.

This is the intended information boundary: the host exposed exact identity,
order, size, digest, candidate binding, and reopen capability; Qwen selected
which exact body to acquire.

## What Qwen did

### Call 1: selected current evidence

Qwen's private reasoning explicitly compared the active step with the current
state and wrote that it needed to reopen `OBS-0002`, then read
`portal/header.py`, patch, check, and submit. Its action was:

```json
{"action":"reopen_observation","handle":"OBS-0002"}
```

The host returned the exact body bound to candidate `df0dd441...da8b2`,
including `portal_marker=W6++` and `validity=current_candidate_only`.

This was not accidental handle selection: the reasoning named the binding and
the complete five-step intended policy before the body was visible.

### Call 2: acquired exact governing source

Qwen carried `W6++` across the next request and requested exactly
`portal/header.py`. It did not inspect the stale observation, P0 distractors,
the preserved ASCII helper, or unrelated archive/bridge files. The exact source
showed:

```python
def portal_header(name: str) -> str:
    return name.strip().casefold()
```

### Call 3: mutated with exact bindings

Qwen cited the current candidate and exact file SHA-256 and changed only the
governing return expression:

```python
return "W6++" + name.strip().casefold()
```

The patch preserved stripping and case folding. It also left the separate
ASCII behavior untouched. The host admitted successor candidate
`9c7a8776...aa54`.

### Call 4: checked the successor

Qwen requested `check("public")` against the exact successor identity. The
public check passed. Its reasoning noticed an important temporal fact: after
the mutation, `OBS-0002` was bound to the parent candidate rather than the new
candidate. It did not misuse that observation or reopen `OBS-0001`; it used the
already acquired fact as the action basis for the mutation that produced the
successor.

The reasoning was somewhat repetitive here and ended mid-sentence, but the
strict action was correct and the output was not truncated.

### Call 5: closed

Qwen submitted the exact checked successor. The host accepted the submission.
The post-seal hidden grader independently passed the resulting snapshot.

## Behavioral assessment

The action sequence was the minimum useful five-action path:

```text
reopen current observation -> read target -> patch -> check -> submit
```

There were no protocol errors, failed actions, stale candidate/file bindings,
redundant reads, distractor reads, failed checks, rescue calls, retries, or
repairs. This is direct development evidence that the minimal controller can
support all of the following after a context reconstruction:

1. preserve the active purpose;
2. distinguish current from stale exact observations using candidate binding;
3. reacquire the exact dynamic fact rather than rely on a preview;
4. join that fact with exact current source;
5. mutate with candidate/file identity checks;
6. preserve the fact-to-action chain across turns;
7. check and close on the successor.

It is stronger than a terminal success flag because the private reasoning and
actions show how the model used the host projection. It is still only one
development fixture at one seed and begins from a mechanically constructed
second-boundary state. It does not establish recurrent end-to-end success, a
C50 comparison, or a measured effect size.

## Runtime economics

The five calls consumed 15,637 server-reported prompt tokens and 1,952
completion tokens. The maximum prompt was only 3,787 tokens, but wall-clock
endpoint compute was about 69.3 minutes on the RTX 3060 reference host.

Prompt ingestion ran at roughly 6.3--6.8 tokens/second and generation at
roughly 1.0--1.15 tokens/second. After the first call, llama.cpp reported only
166 cached prompt tokens on every turn. Therefore most of each full rendered
request was reevaluated. This did not affect correctness or capacity, but it is
a major execution-cost finding for the planned large-prompt study. Any cache-
local request-layout optimization must be prospectively qualified because JSON
field order changes model-visible bytes even when JSON meaning is unchanged.

## Host finding discovered after the run

The saved receipt says `server_shutdown_verified: true`, but that historical
field was computed from port release alone. After completion, a
`llama-server.exe` process using the exact frozen runtime binary remained while
the port had ceased listening. The old launch record did not include the child
PID, so the surviving process cannot be proven from custody to be the exact
process launched by this rehearsal. It was stopped manually.

The justified conclusion is not that this run's owned child definitely failed
to terminate. It is that the old host could not prove owned-process termination
and its positive shutdown field was insufficient. The model responses, action
results, response seal, public check, and post-seal hidden grade are unaffected.

The prospective host now records the spawned PID, rejects a competing runtime
process before launch, verifies both owned-child termination and port release,
writes a shutdown record, and fails closed unless both are true.

## Hypotheses earned for measured testing

1. **Candidate bindings are sufficient cues for exact observation selection.**
   The measured T25 cells should select the handle whose candidate ID matches
   the reconstructed current candidate without a host-authored stale label.
2. **Exact reopening supports fact-to-action continuity.** The selected marker
   should appear in the eventual patch, with the reopen preceding mutation.
3. **Mutation correctly changes validity status.** A previously current
   observation should not be treated as fresh evidence for a later, unrelated
   post-mutation decision.
4. **Recurrence, not final-path competence, is the remaining behavioral risk.**
   This focused rehearsal qualified the second-boundary path; it did not test
   whether Qwen can first create the correct old/current observation pair under
   Phase-B pressure.
5. **Prompt serialization, not token capacity, is the dominant local runtime
   cost.** A separately qualified cache-local layout could reduce time, but it
   must not be silently introduced into the frozen measured treatment.

No host defect affected Qwen's five observed decisions or the hidden-correct
successor. The shutdown-certification defect affects lifecycle custody and is
corrected prospectively.
