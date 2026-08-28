# Experiment 004 attempt 1 direct transcript audit

## Audit identity and scope

- reviewer: Codex, condition-aware post-seal direct audit
- audit date: 2026-08-28
- actor: Qwen3.8-27B AD-IQ2_S, reasoning-off prefix
- matched branch seed: 65537
- sampler: temperature 0.7, top-p 0.8, top-k 20, min-p 0.0,
  presence penalty 1.5, repeat penalty 1.0
- active branch ceiling: 25,000 total tokens with a 2,500-token response
  allowance and 512-token runtime prompt-accounting allowance
- branch history: reconstructed context with the exact latest prefix action and
  result, exact fork binding, exact current candidate and P0, a verbatim Phase B
  pointer, and an exact observation directory; older prefix chronology absent
- private reasoning: saved separately, read directly, not inserted into later
  history

Every one of the 39 saved assistant outputs was inspected. Every R1 private
reasoning artifact was read in full. The audit uses the saved coding requests,
raw endpoint responses, extracted actions, tool results, candidates, and
receipts rather than inferring behavior from summaries.

## Shared prefix: E4-SOURCE

The task explicitly required four complete release-file reads before a staging
repair and fork. The actor began correctly but adopted a highly conservative
paging policy:

| Call | Action |
|---:|---|
| 1 | `begin` |
| 2-8 | `archive/amber.py`, ten lines per call |
| 9 | complete `archive/amber.py` from line 71 |
| 10-16 | `archive/cobalt.py`, ten lines per call |
| 17 | complete `archive/cobalt.py` from line 71 |
| 18 | first ten lines of `archive/ivory.py` |

The actor followed exact continuations and did not invent a path, but its local
choice of tiny pages consumed the entire protocol horizon. Maximum prompt size
was 23,389 tokens; cumulative prompt tokens were 164,995. It never observed the
governing namespace fact and never exposed either branch. This is evidence
about prefix acquisition economics, not about reasoning mode.

## Shared prefix: E4-OBSERVATION

The actor made the following eleven calls:

```text
begin
probe(routing)
read archive/amber.py
read archive/cobalt.py
read archive/ivory.py
read staging/gate.py
check(prefork)                 # accepted invocation, failed check
patch staging/gate.py
fork_ready                     # rejected because check had not passed
check(prefork)                 # passed
fork_ready                     # accepted
```

The exact routing result was externally custodied as `OBS-0001`, not placed in
the reconstructed branch prompt. The branch saw only the observation row:
action `probe`, target `routing`, stable handle, candidate binding, size, and
hash. The exact body had to be reopened. The current candidate already carried
the successful staging repair. Both branches started from the same exact fork
identity.

## Matched branch comparison

| Measure | R0: reasoning off | R1: reasoning enabled, low requested |
|---|---:|---:|
| Calls | 5 | 5 |
| Action order | read, reopen, patch, check, submit | reopen, read, patch, check, submit |
| Reopened governing observation | call 2 | call 1 |
| Patch call | 3 | 3 |
| Public check | pass | pass |
| Hidden grader | pass | pass |
| Submitted | yes | yes |
| Exact known-good candidate identity | no | yes |
| Prompt-token sum | 15,167 | 15,439 |
| Completion-token sum | 378 | 2,052 |
| Elapsed endpoint time | 50.811 s | 138.983 s |
| Private reasoning bytes | 0 | 6,344 |
| Maximum prompt tokens | 3,681 | 3,743 |

All server-reported prompt counts equaled the independently tokenized rendered
prompt counts for these ten calls.

### R0 qualitative behavior

R0 first read the exact two-line target, then reopened `OBS-0001`, obtaining:

```text
routing_prefix=K3>
```

It patched the function to:

```python
return ("K3>" + name.strip()).upper()
```

The patch is not byte-identical to the known-good patch because it applies
`upper()` to the prefix and normalized name together. For the exact uppercase
ASCII prefix in this fixture, it is behaviorally correct: public and hidden
checks passed. It then checked and submitted without wandering.

### R1 private reasoning and external behavior

Call 1 reasoning correctly identified all governing elements: Phase B, the
absent routing prefix, `OBS-0001`, the target source, patch, check, and submit.
Its first external action followed the plan and reopened the observation.

Call 2 explicitly extracted `K3>` from the reopened exact body and recognized
the contract requiring exact current source before mutation. It then read
`packet/code.py`.

Call 3 reconstructed the exact governing fact and exact two-line source. It
considered reading `packet/transport.py`, repeatedly reconsidered whether that
was necessary, and ultimately made the efficient decision to patch without the
extra read. The emitted patch was exactly the known-good formulation:

```python
return "K3>" + name.strip().upper()
```

Call 4 correctly identified the next closure step and ran the public check.
Call 5 recognized the passed check and submitted. Every external action was
consistent with the final plan.

The reasoning was useful as an inspectable plan, but it was not concise. Call 3
alone contained 3,252 bytes and tokenized to 809 tokens, with substantial
repetition around a transport-file read that was never taken. The five traces
tokenized to 1,670 tokens total. This is why the result cannot be described as
a hard-512 treatment.

## Behavioral interpretation

Both modes demonstrated the target capability in this case:

1. recognized that the governing dynamic fact was absent from the active
   source/context;
2. used the exact observation directory rather than guessing the prefix;
3. reopened the exact historical observation;
4. read exact current source before mutation;
5. produced a correct patch;
6. passed the public and hidden checks; and
7. submitted within five calls.

Reasoning changed acquisition order and produced the exact canonical patch, but
it did not reduce calls, avoid a read, improve hidden correctness, or improve
closure. It added 272 prompt tokens, 1,674 completion tokens, and 88.172 seconds
of endpoint time. One easy observation case is insufficient to infer a general
quality advantage.

