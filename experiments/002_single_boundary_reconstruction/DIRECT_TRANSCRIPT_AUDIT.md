# Experiment 002 direct transcript audit

## Audit identity and method

Audit mode: condition-aware post-seal primary analysis. Reviewer: Codex,
working directly from the sealed actor inputs, raw assistant outputs, tool
results, candidate snapshots, record chains, runtime evidence, and frozen
evaluator artifacts.

Actor: `Qwen3.8-27B-AD-IQ2_S.gguf`, SHA-256
`d416fa422c9035605c778f60d90a94b288c38b4f9ec2126b58ef938ce8d5f716`.
Reasoning was off. Sampler: temperature 0.7, top-p 0.8, top-k 20, min-p 0,
presence penalty 1.5, repeat penalty 1.0. Prefix and continuation output cap:
2,500 tokens. T25 total active envelope: 25,000. C50 physical envelope:
50,176.

All 70 prospective coding requests were decoded and checked against their
condition, stage, candidate, P0, invocation budget, fork binding, observation
directory, and exact prior history. All 67 returned assistant contents and
tool results were read. The three remaining requests were capacity-denied
before HTTP. Particular attention was given to both T25 reset prompts, the
last prefix prompt/result, every probe result, and every mutation/check path.

## What T25 actually received

The T25 reset was not an empty or vague restart. It contained:

- the complete original two-phase task;
- `stage: continuation`;
- the exact current candidate and task-independent P0 directory;
- the exact accepted `fork_ready` action/result as its sole active history;
- a notice that older chronology was externally custodied and should be
  reacquired only when needed;
- a complete directory of reopenable dynamic observations;
- ordinary read/search/tree, exact patch/check, reopen, and submit tools.

It did not contain the bodies of old source reads, the body of the runtime
probe, a semantic task summary, or a host-selected statement of which prior
fact mattered.

For E2-SOURCE, P0 explicitly located `release_prefix` at
`policy/channel.py:230-232`, `release_tag` at `release/tag.py:1-2`, and
`display_tag` at `release/formatting.py:1-2`.

For E2-OBSERVATION, the observation directory contained five exact handles
for the repeated `wire` probe, each visibly labeled `action: probe` and
`target: wire`, followed by the successful prefork check and fork boundary.
The exact reopened probe body would have said `wire_prefix=XP9:`.

## Fork 1 — E2-SOURCE, seed 42

The prefix began efficiently: begin, three required large reads, readiness
read. It then spent three calls pre-reading Phase B source and the first tail
line of policy. It checked before repairing readiness, learned the check
failed, patched readiness correctly, and passed the check.

At call 12 it attempted `fork_ready`, but the policy file had not yet been
read completely: its first page ended at line 227. It used calls 13 and 14 on
lines 229 and 230, omitting line 228 and still not completing lines 231-232.
The prefix therefore ended without a fork. No C50/T25 branches were created.

This is not a source-comprehension failure. It is a sequencing and exact-page
completion failure under a tight action budget. P0 disclosed the relevant
line ranges, but the actor’s chosen page boundaries and premature fork attempt
consumed the remaining horizon.

## Fork 2 — E2-OBSERVATION, seed 314159

The actor called the same `wire` probe seven consecutive times. Every call
returned the same exact `XP9:` observation. It then read the three required
large audit files and readiness. It checked before patching, received the
expected failure, and made the correct readiness patch on call 14. With no
call left for a passing check and `fork_ready`, the prefix ended incomplete.

The repetition is important. The actor was not confused about the probe
schema or unable to obtain the fact; it repeatedly chose an already-completed
information action despite exact prior results remaining in context. The
dominant failure is action policy and closure budgeting.

## Fork 3 — E2-OBSERVATION, seed 42

The prefix called the probe five times, read all three audit files, read and
patched readiness, passed `prefork`, and reached the exact fork on call 13.

### C50

C50 retained the five exact `wire_prefix=XP9:` results. It read
`protocol/banner.py` and `protocol/transport.py`, then patched the banner to
return `"XP9:" + name.strip().upper()`. It passed the public check and
submitted in five calls. The final candidate was byte-identical to known-good
and passed the hidden grader.

This establishes that the task and actor were viable when the dynamic
observation stayed directly in active chronology.

### T25

T25’s first request visibly offered the five `wire` observation handles and
identified the stage as continuation. Nevertheless its first two actions were
full reads of `audit/alpha.py` and `audit/bravo.py`, exactly restarting Phase
A in the original task order. It never used `reopen_observation`, never opened
the Phase B source, and never mutated.

The prospective third HTTP call contained those two large exact read results.
Its prompt was 22,334 tokens; with the 512-token runtime allowance and 2,500
output tokens the total was 25,346, so the guard stopped it before HTTP.

The behavioral difference is therefore not missing access. The decisive
observation had five readable exact handles. The actor failed to interpret
the accepted boundary as completed progress and chose obsolete acquisition.

## Fork 4 — E2-SOURCE, seed 314159

The prefix read the required large files. Its first policy page ended at line
230, so it attempted `fork_ready` prematurely, read lines 231-232, read
readiness, attempted `fork_ready` prematurely again, then patched readiness,
passed `prefork`, and reached the exact fork on call 11.

The full prefix had already exposed the exact governing source, including
`RELEASE_PREFIX = "stable-"`, and P0 continued to pinpoint
`release_prefix()` at lines 230-232.

### C50

C50 read the two small Phase B files, then reread policy lines 1-230 and
231-232. Instead of patching, it reread lines 1-230 a second time. That second
large result made its next prospective request 52,836 prompt tokens; total
occupancy would exceed the 50,176 physical envelope. The guard stopped call 6
before HTTP. The candidate remained at the correct Phase A state and failed
the hidden Phase B grader.

Append-only chronology therefore did not guarantee economical use of retained
facts. The model both retained and reacquired the same policy, then reacquired
it again.

### T25

T25 ignored P0’s exact Phase B locations. It reread `audit/alpha.py`,
`audit/bravo.py`, and policy lines 1-230 in the original Phase A order. It did
not read lines 230-232 directly, inspect the Phase B targets, or mutate. Its
fourth prospective prompt was 31,298 tokens; total occupancy would be 34,310,
so it stopped before HTTP.

## Cross-trajectory qualitative findings

1. **Exact availability is not working-set selection.** External custody, P0,
   and observation handles made every needed fact accessible. The actor still
   selected obsolete or redundant acquisition.
2. **The full original task can overpower a mechanical stage marker.** After
   reset, both T25 branches followed Phase A instructions from the beginning
   despite `stage: continuation` and an accepted fork receipt.
3. **Dynamic observation reopening was comprehensible but unused.** The
   observation directory was explicit enough to identify `wire`, but the
   actor never tried it. C50’s direct in-context probe body supported a correct
   patch.
4. **P0 locates facts but does not tell the model whether reacquisition is
   necessary.** In the source branch, the actor ignored precise symbol ranges
   and reread the large file.
5. **Append-only context also suffers retrieval-policy failure.** C50 solved
   the observation case, but redundant reads exhausted even 50k in the source
   case.
6. **Reasoning-off action control is the current bottleneck.** Repeated probes,
   premature checks/forks, incomplete pagination, and redundant reads consumed
   more capability than coding itself. When the actor reached mutation with
   the governing fact active, its patches were correct.

## Contamination boundary

There was no false tool result, retry, repair, or host rescue. Capacity stops
occurred before HTTP and are part of the treatment. Hidden grades were applied
after the response seal and do not alter the direct behavioral record.
