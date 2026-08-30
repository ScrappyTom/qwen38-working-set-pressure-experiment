# Experiment 018 Apparatus Finding

## Disposition

Experiment 018 is mechanically valid and scorable. The run completed exactly
once, sealed all response evidence before evaluator access, replayed every
completed segment, and shut down its owned server. No transport, parser,
checker, candidate-binding, custody, or runtime-accounting defect invalidates
the behavioral result.

The result is mixed for the controller, not failed apparatus:

- all four R50 branches stopped prospectively before HTTP when the next fully
  resident request exceeded the physical 50,176-token envelope;
- all four X25 branches continued within the 25,000-token envelope;
- two X25 observation branches checked, passed hidden grading, and submitted;
- two X25 source branches exhausted the frozen action budget after making
  substantive progress but did not reach a correct terminal candidate.

The exact response seal is
`499ab2c9d7b58572a7dec06d795a3d6f95184ecb159075a010532806c117277d`.

## Execution integrity

The sealed run records:

- 91 prepared invocations;
- 87 actual HTTP completions;
- four prospective capacity denials before HTTP;
- zero retries, repairs, rescues, malformed envelopes, or rejected actions;
- zero runtime/offline token-accounting delta on every completion;
- one response ID per completion;
- exact server shutdown and port release;
- evaluator truth opened only after the response seal.

All shared, R50, and X25 run logs replay under `verify_run`. The fresh bank,
execution package, runtime profile, actor, authorization, and executable
closure remain hash-bound. Post-seal hidden grading was independently rerun
from the terminal candidate snapshots during analysis and matched the saved
grading rows.

## The capacity stops are real outcomes

R50 did not emit a model response at its terminal point. The denied next
requests were:

| Family | Offline prompt | Adjusted prompt | Ceiling |
|---|---:|---:|---:|
| source | 55,139 | 55,651 | 50,176 |
| observation | 56,205 | 56,717 | 50,176 |

The X25 branches mechanically externalized only old payload bodies. Their
largest completed prompt counts were 21,970, 21,749, 21,485, and 21,883.
After the 512-token runtime allowance and 2,500-token output reserve, every
actual request remained within 25,000. The tightest admitted source request
had only 18 tokens of headroom, so this was authentic pressure rather than a
nominal small-context condition.

## No missing progress signal caused the duplicate reads

Two X25 trajectories reread a completed ledger page. Direct inspection of the
corresponding coding requests shows that the event frame already contained:

- the readable ledger path;
- both exact read ranges;
- `complete: true` on the terminal range;
- exact file and candidate bindings.

For example, cell 02 call 005 visibly contained completed terminal events for
both `required_00.py` and `required_01.py`. Qwen nevertheless described them
as incomplete and reread `required_00.py:211`. This is a model integration or
tracking lapse, not omitted host signal. The lapse consumed one action and
contributed to that branch reaching its budget before checking.

## Exact-reopen indirection is a real interface-economics finding

The observation branches exposed a non-corrupting but undesirable interaction
between generic event custody and exact reopening.

After `reopen_observation(OBS-0002)`, the exact observation body was the result
body of a new event. Once that new event aged past the X25 residency boundary,
the renderer assigned it another `RES-*` address. Qwen then either:

- reopened the newer result address, producing a second-level reopen chain; or
- invoked the original observation handle again.

The exact bytes, hashes, and candidate bindings remained correct. Both
trajectories ultimately recovered `HARBOR-K9`, patched correctly, checked, and
submitted. Therefore this did not invalidate or reverse an observed outcome.
It did consume two additional acquisitions in each successful trajectory and
nearly exhausted one branch's action budget.

This is not evidence that handles lack signal: the observation directory and
event fields correctly identified the current record and the exact body class.
It is evidence that an exact reopen should preserve a canonical stable source
address rather than encourage a model to traverse addresses of addresses.
Any correction must be prospective; the sealed run remains unchanged.

## Source-family semantic limitation

Both source X25 branches interpreted:

> preserve the current policy value by repairing `api/primary.py` so it
> prefixes ... with the exact current `active_prefix()` value

as an instruction to call `active_prefix()` dynamically. The frozen checker
instead required `normalize_primary` to retain the pre-change value
`ember-` after the policy changed to `quartz-`.

Cell 01 reached the public check, received the exact failure, and explicitly
diagnosed the intended snapshot semantics in private reasoning. It had only
one action left, reread `api/primary.py`, and could not correct, recheck, and
submit. Cell 02 spent an additional action on a duplicate completed ledger
page and exhausted its budget immediately after the final patch, before a
check.

The checker is correct for the frozen expected successor, and the run is
formally scorable against that contract. However, the wording admits a
plausible dynamic-call reading and both seeds chose it independently. The
source-family 0/2 should therefore not be interpreted as pure evidence that
X25 lost semantic continuity. It combines a task-specification ambiguity with
tight closure economics and, in one seed, a progress-tracking lapse.

## Validity conclusion

Experiment 018 supports apparatus-valid behavioral claims about:

- authentic R50 physical exhaustion;
- X25 continuation under a smaller active envelope;
- exact current-observation reacquisition and use;
- candidate-bound mutation, check, and closure in the observation family;
- actor tracking and acquisition failures visible in the source family.

It does not support a clean aggregate efficiency estimate or a broad claim
that X25 reliably solves every large-world task. Cumulative prompt totals are
not directly comparable as efficiency because R50 was forced to stop much
earlier while X25 continued doing work.

