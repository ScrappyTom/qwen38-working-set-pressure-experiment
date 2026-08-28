# Experiment 006 apparatus finding

## Disposition

The run is valid for its prospectively bounded question.

Both fresh actor-unexposed prefixes crossed the pressure boundary through real
Qwen actions and exact tool results. All four continuations completed under the
frozen schedule. The response tree was sealed before evaluator access, replayed
exactly, and hidden-graded only after sealing.

## Execution integrity

- actor: Qwen3.8-27B AD-IQ2_S, SHA-256
  `d416fa422c9035605c778f60d90a94b288c38b4f9ec2126b58ef938ce8d5f716`;
- llama.cpp: b10434 (`7e4c0a968`), 50,176-token physical slot, full GPU
  offload, server-enforced private-reasoning budget of 512 tokens;
- prepared invocations: 42;
- actual HTTP completions: 42;
- runtime accounting delta: 0 on every completion;
- retries, repairs, rescues, transport failures, capacity-denied prepared
  invocations, and protocol failures: zero;
- response aggregate:
  `f5458411b0035a2b7a9f6469323353aa3153c712a1765ae14fd0b60cc613feae`;
- server shutdown and port release: verified.

The accounting correction is effective: prospective/prepared invocations and
actual HTTP completions are separately recorded. Unlike Experiment 005, no
capacity-denied preparation was misreported as a completion call.

## Authentic pressure qualification

The source prefix reached `fork_ready` after eight real calls. Its exact next
append-only continuation request was 27,909 offline tokens (28,421 after the
frozen runtime allowance), so it failed the 25k treatment gate and remained
admissible under 50k.

The observation prefix reached `fork_ready` after nine real calls. Its exact
next append-only request was 28,080 offline tokens (28,592 adjusted), likewise
failing the 25k gate while remaining admissible under 50k.

The pressure came only from the real task, complete required source reads,
assistant actions, tool results, candidate mutation, and check chronology. No
filler, duplicated padding, constructed prefix, semantic summary, or selected
relevance fact was inserted.

## Treatment integrity

Within each pair, C50 and T25 shared the exact task, current candidate, P0,
fork binding, observation inventory, active-step pointer, tools, seed, sampler,
output cap, and private-reasoning policy.

The difference was active chronology:

- C50 retained all exact prefix action/result history;
- T25 retained only the exact accepted fork result while preserving complete
  external custody and the identity-only observation directory.

All private reasoning was separately custodied and omitted from subsequent
history in both conditions.

## Limitation visible in the common prompt

The common system prompt says to use `reopen_observation` before relying on a
historical dynamic result. C50 therefore reopened the observation even though
the exact probe result also remained in its append-only chronology, and then
reopened it a second time. This does not compromise the T25 capability result:
T25 still had to select the correct identity-only handle and recover the absent
body. It does mean the observation-case economic comparison should not be read
as the minimum possible cost of an optimally history-using C50 controller.

No apparatus defect, false observation, evaluator leak, or post-exposure
change affected the measured trajectories.
