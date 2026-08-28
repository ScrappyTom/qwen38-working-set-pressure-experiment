# Experiment 005 direct transcript audit

## Scope and method

- reviewer: Codex, condition-aware post-seal audit
- audit date: 2026-08-28
- actor: Qwen3.8-27B AD-IQ2_S
- conditions: R0 reasoning off; R1 low reasoning with server-enforced 512-token
  maximum per call
- seeds: 73771 and 88001
- sampler: temperature 0.7, top-p 0.8, top-k 20, min-p 0.0,
  presence penalty 1.5, repeat penalty 1.0
- active envelope: 25,000 total tokens, 2,500 response allowance, 512 runtime
  prompt-accounting allowance

All 25 prospective coding requests were read and structurally inspected. All 24
actual assistant outputs and tool results were read. All 13 R1 private
reasoning traces were read in full. Terminal candidates were replayed and
hidden-graded after the response seal.

## What each branch knew

Within a case, R0 and R1 began from the same exact constructed fork. The active
request contained:

- the exact Phase B task as a verbatim user-authored pointer;
- the exact current candidate and P0 path/symbol/signature/range directory;
- the exact accepted `fork_ready` action and result;
- the exact fork binding and current invocation budgets;
- an identity-only observation directory;
- the ordinary exact tools;
- no older Phase A chronology, semantic summary, ranking, or selected fact.

The coding request bytes were identical within each pair. Only the frozen
reasoning envelope differed. All later requests retained exact append-only
branch action/result history.

## E5-CHANNEL

### R0

```text
read publish/slug.py
read all 221 lines of policy/channel.py
patch using imported ACTIVE_CHANNEL
check public: pass
submit
```

R0 was semantically decisive. It acquired the target and governing file, made
the correct patch, and closed in five calls. Its inefficiency was acquisition
width: it pulled the complete 12,182-byte policy source into append-only
history even though P0 exposed the relevant getter near the end.

### R1

```text
read publish/slug.py
read policy/channel.py lines 210-221 around active_channel()
read policy/channel.py lines 1-30 to resolve ACTIVE_CHANNEL
read publish/render.py
patch using imported ACTIVE_CHANNEL
check public: pass
submit
```

R1 reasoning explicitly decomposed the task into target source, governing
source, dependent behavior, patch, check, and submit. It used P0's symbol range
to inspect the getter, recognized that the getter only named a constant, and
then read a small header page to obtain the exact value. It followed its plan.

The `publish/render.py` read was conservative but unnecessary: R0 preserved the
same behavior without it. Two traces reached 511 tokens and repeated parts of
the state. Despite that extra call and reasoning overhead, R1 avoided the large
resident source result. Both branches produced the same terminal candidate and
passed hidden grading.

## E5-FRAME

### R1

```text
read wire/header.py
read config/frame.py lines 200-217 around frame_prefix()
read config/frame.py lines 1-20 to resolve FRAME_PREFIX
patch exact known-good implementation
check public: pass
submit
```

R1 reasoning first mentioned the dependent ASCII encoder as something it might
inspect, then correctly decided it already had sufficient evidence and did not
spend the call. It identified `FRAME_PREFIX = "m7:"`, kept that lowercase exact
prefix outside the uppercase normalization, emitted the exact task-author
known-good patch, and closed in six calls.

### R0

```text
read wire/header.py
read all 217 lines of config/frame.py
read all 217 lines of journal/alpha.py       # irrelevant to Phase B
read stage/gate.py                            # already-completed Phase A state
read wire/encode.py
patch using imported FRAME_PREFIX
prepare check public                          # denied by 25k guard; no HTTP
```

After the second call, R0 possessed both the exact target and exact governing
fact. It nevertheless reopened a large audit journal and the already-completed
staging target before inspecting the dependent encoder. No private rationale is
available in R0, so the internal cause cannot be asserted. The observable
behavior is chronology/closure drift despite the exact Phase B pointer.

R0 eventually produced a hidden-correct patch, but the two large source results
made the next request unadmissible. It could not check or submit. This is not a
semantic coding failure; it is an information-policy failure that became an
operational correctness failure under the active-context contract.

## Per-branch results

| Case | Condition | Hidden correct | Checked/submitted | HTTP calls | Exact read bytes | Prompt tokens | Completion tokens | Peak prospective prompt |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| E5-CHANNEL | R0 | yes | yes | 5 | 12,257 | 41,412 | 442 | 12,585 |
| E5-CHANNEL | R1 | yes | yes | 7 | 2,171 | 27,068 | 3,132 | 5,340 |
| E5-FRAME | R0 | yes | no | 6 | 24,516 | 80,667 | 390 | 22,103 |
| E5-FRAME | R1 | yes | yes | 6 | 2,036 | 22,253 | 2,141 | 5,074 |

## Qualitative conclusion

Bounded reasoning did not make the model understand the patch when R0 could
not. R0 produced hidden-correct code in both cases. Bounded reasoning changed
which exact evidence entered the active chronology and whether the actor
retained enough headroom to close.

Across both fresh cases, R1 consistently translated P0's readable symbols and
ranges into scoped exact reads. R0 consistently acquired the complete governing
file. In the second case, R0 also reopened irrelevant/completed material and
lost the ability to check. That is the mechanism-level result.

