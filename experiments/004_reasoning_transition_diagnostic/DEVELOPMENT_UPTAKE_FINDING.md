# Experiment 004 development reasoning-uptake finding

Date: 2026-08-28

## Disposition

The reasoning-enabled live transport and evidence-to-action path are qualified
on development-only material. The fresh Experiment 004 bank remained
unexposed.

The actor completed the previously difficult observation reconstruction in six
calls:

```text
reopen OBS-0001
read target line 1
read complete two-line target
patch exact target
check public: pass
submit
```

The accepted patch prepended the exact `R7|` value from the historical dynamic
observation while preserving trimming, uppercasing, and ASCII transport. The
public check passed and the submitted candidate matched the known development
repair.

This is apparatus/development evidence, not a fresh outcome and not part of the
Experiment 004 comparison.

## Exact actor envelope

- actor: Qwen3.8-27B-AD-IQ2_S
- actor SHA-256:
  `d416fa422c9035605c778f60d90a94b288c38b4f9ec2126b58ef938ce8d5f716`
- reasoning effort: low
- private reasoning budget: 512 tokens per call
- private reasoning preservation in later history: disabled
- final content: one strict JSON action
- seed: 424242
- continuation limit: eight; used: six
- attempts per call: one
- retries, repairs, rescues: zero
- active-total ceiling: 25,000 tokens

All six responses contained separately extracted, nonempty
`reasoning_content`. The exact reasoning bytes, final JSON, endpoint response,
action result, request, and rendered prompt are preserved for every call.

## Direct prompt and output audit

The first request was a fresh reconstructed context with one latest history
entry, the exact Phase B pointer, current P0, and observation handles
`OBS-0001`, `OBS-0002`, and `OBS-0003`. Older chronology was absent. The final
request contained six history entries and the patched candidate identity.

The private reasoning was coherent with the external trajectory:

1. It identified Phase B and named the required sequence: reopen the probe,
   read `wire/header.py`, patch, check, submit.
2. After reopening, it extracted the exact `R7|` fact and stated that the
   mutation target still had to be read.
3. It initially requested only target line 1, then recognized that this was
   insufficient and read the complete two-line file. This is one avoidable
   extra acquisition, not a loop.
4. It derived the exact replacement
   `return "R7|" + name.strip().upper()` and emitted a correctly bound patch.
5. It observed the accepted candidate transition and selected `public`.
6. It observed the passing check and submitted the same candidate.

This is the behavior Experiment 003 lacked. The reasoning-off pointer branch
on the historical study reopened the correct observation but repeatedly read
the unchanged target without patching. The development uptake is not a matched
fresh causal comparison because it uses another seed and already-exposed
material, but it establishes that the exact reasoning envelope can reach and
execute the intended transition.

## Cost and capacity

| Call | Action | Offline prompt tokens | Completion tokens | Reasoning bytes |
|---:|---|---:|---:|---:|
| 1 | reopen observation | 2,408 | 200 | 740 |
| 2 | read target line 1 | 2,620 | 237 | 792 |
| 3 | read complete target | 2,829 | 568 | 1,918 |
| 4 | patch | 3,046 | 833 | 2,343 |
| 5 | check | 3,498 | 339 | 860 |
| 6 | submit | 3,810 | 260 | 770 |

Totals were 18,211 prompt tokens and 2,437 completion tokens. Maximum prompt
occupancy was 3,810 tokens, far below the 25k boundary. Server and offline
prompt counts matched exactly on all six calls. The 512-token private-reasoning
cap is contained inside the 2,500-token complete response allowance.

The reasoning treatment is substantially more expensive and slower than
reasoning off; the six HTTP calls took about 166 seconds in aggregate. Fresh
measurement must therefore report quality and evidence-to-action improvement
before considering token or latency economics.

## Post-run analyzer defect

The live trajectory itself completed and the server shut down successfully.
The first post-run analyzer then raised `KeyError('kind')` because it queried a
record field named `kind`; the actual append-only schema uses `record_type`.

No model call was retried. The original failed receipt remains preserved.
An offline-only finalizer verified the record chain and run summary, bound all
six reasoning artifacts, sealed the existing response tree, and recorded zero
new model calls. The development script was corrected for future use, but this
exact trajectory was not rerun or reclassified as an uninterrupted receipt.

## Decision

The development gate passes:

- request-level reasoning on/off is operational under one `auto` server;
- private reasoning is separated from strict final JSON;
- reasoning bytes are exactly custodied and omitted from later history;
- patch/check/submit reached the real tool executor;
- token accounting and shutdown passed;
- the fresh E4 bank was not exposed.

Proceed with the already frozen four-branch Experiment 004 comparison. Do not
change the fresh fixtures, prompts, reasoning budget, seeds, schedule, or
execution closure based on this development behavior.
