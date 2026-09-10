# Wording candidate: prepared and verified, September 10, 2026

The source-checked resource/navigation candidate is ready for the separate
eight-request execution decision. Preparation sent **zero completion requests**.
It preserves the tested complete tool reference and corrects two descriptions:
the correction-cycle illustration is removed, and the P0 root/page scopes are
explained without implying a global completion gate. No behavioral improvement
is claimed before exposure.

The [specification](SPEC.md) contains the exact replacement text and comparison
scope. [WORDING_CHANGE.json](preparation-001/WORDING_CHANGE.json) records the
two edits mechanically. The adapter lives in
[prepare_interface_wording.py](../../../scripts/prepare_interface_wording.py);
it changes the prospective input, preserving the original stored request and
the consumed shared renderer. The original sixteen-request execution closure
and all sealed response artifacts still verify.

## Direct input/output grounding

This preparation revisited the complete C10 and C15 thinking, their actual
native inputs, final actions and exact host results, alongside the completed
comparison audits and current renderer/executor. It did not infer the need from
aggregate time, accepted-action counts or an extracted diagnostic label.

| What Qwen saw | Thinking and actual action | Host result and implication |
|---|---|---|
| C10: complete current two-line source, exact pre-edit guards, full tool reference, and the resource illustration | Thinking line 74 treats the illustrated ideal path as telling it to check next. Final checks the current candidate with the correct guard. | The check executes and legitimately fails on return 1. The host does not require that check before an edit. Procedural interpretation is visible; the check's diagnostic value and how much time the wording caused remain unresolved. |
| C15: only lines 7–8 resident, historical patch/diff external, root scope flagged incomplete, and the old navigation imperative; paging arguments undocumented | It initially recognizes missing source and history. Later it treats p0_page as the way to make the repository complete, repeatedly guessing a parameterless operation. Final requests service.py at offset 1. | The host correctly returns only ready(), the second symbol, whose exact source was already visible. Coverage remains 7–8; missing source and old marker remain absent. This is weak acquisition, not a failure to recognize the partial read. The origin of offset 1 is unresolved. |

Exact evidence:
[C10 input](../comparison/run-001/calls/C10-rendered-prompt.txt),
[thinking](../comparison/run-001/calls/C10-assistant-reasoning.txt),
[final](../comparison/run-001/calls/C10-assistant-content.txt),
[result](../comparison/run-001/calls/C10-host-result.json);
[C15 input](../comparison/run-001/calls/C15-rendered-prompt.txt),
[thinking](../comparison/run-001/calls/C15-assistant-reasoning.txt),
[final](../comparison/run-001/calls/C15-assistant-content.txt),
[result](../comparison/run-001/calls/C15-host-result.json).
The [completed host audit](../comparison/review/HOST_PATH_AUDIT.md) retains the
broader successful and recovered paths. C15 also lacked argument information;
its result cannot predict a wording effect once both arms have that information.

Source checks confirm that build_p0_root supplies the complete top level with
complete_for_repository=false, while p0_page is a stateless path/row-offset
operation. A page's null next_offset ends that scope; it does not alter root
flags or add exact-source reading. A guarded I3 edit succeeds without a prior
check, while a stale candidate guard is rejected. These are implemented facts,
not preferred task strategies. Baseline checks and useful navigation stay allowed.

The candidate's actual rendered system text and I3/I4 user states were inspected
directly. Both the thinking instruction and complete reference are present.
Required exact-source instructions remain. I3 still contains the current source
and guards; I4 still exposes only current tail source and historical recovery
signals. No absent marker, expected answer, audit diagnosis or preferred action
was inserted. The other state bodies are verified byte-for-byte against the
previously reviewed reference inputs; only the declared resource field differs.

## Package and input cost

W01–W08 propose four pairs: I3 and I4, each at seeds 1729 and 271828, reference
versus wording. Order is counterbalanced. These are new seeds on reused
development states, not fresh capability evidence or replacements for consumed
responses. E01–E04 are I1/I2 input regressions only; they are excluded from
completion scope. The package contains twelve exact API inputs and native
renderings, representing eight distinct native prompts because seeds do not
appear in rendered text.

| State | Reference input tokens | Wording input tokens | Change | Wording physical generation space | Proposed exposure |
|---|---:|---:|---:|---:|---|
| I1: crowded external-source state | 20,389 | 20,410 | +21 | 36,166 | None; offline input regression |
| I2: old check and current successor | 4,557 | 4,578 | +21 | 51,998 | None; offline input regression |
| I3: current source before repair | 3,272 | 3,293 | +21 | 53,283 | Two seeds per condition |
| I4: historical patch and partial read | 3,885 | 3,906 | +21 | 52,670 | Two seeds per condition |

For the proposed eight requests, reference input totals 14,314 tokens and wording
14,398: **84 added tokens across four candidate invocations**, about 0.59%.
There is no padding. The reference itself remains the tested 7,013-byte,
1,675-token block in both conditions. The net +21 includes the longer scope
explanation and the removed resource field, not a signature change.

All inputs fit the unchanged 23,808-token admission ceiling. The largest leaves
36,166 physical tokens, 3,398 above the 32,768 planning reserve. The proposed live
inputs are much smaller; even their largest leaves 52,670 physical tokens.
Generation remains uncapped. These numbers establish input fit, not a bound on
future thinking or qualification of the pending 25k continuity study.

The runtime was the selected q4_0 K/V, 56,576-context, no-MTP, full-offload b10434
configuration. Native inputs retain thinking on/xhigh, all generation limits -1,
the fixed sampler and disabled cache reuse. Effective startup checks passed,
the owned server shut down and its port was released. The 49 preparation-only
memory samples reached 563 MiB free. No prompt inference or generation ran;
this is not a new inference-memory qualification or a replacement for the earlier
327 MiB observation. The owner's advisory 350 MiB policy is unchanged.

## Verification and limits

Seven focused tests passed:

```text
PYTHONPATH=src
py -3.12 -B -X utf8 -m unittest discover -s tests -p test_interface_wording.py -v
Ran 7 tests ... OK
```

They cover unchanged state/grammar/budgets/reference across all four examples,
the two exact permitted edits, new-seed and eight-call scope, rejection of missing
contracts or unknown scope, actual paging/read behavior, guarded editing without
a compulsory baseline check, render/tokenize-only preparation, and preservation
of a failed preparation without retry. This is a focused run, not a full suite.

The separately implemented [verifier](../../../scripts/verify_interface_wording.py)
checks each control against the previously reviewed reference request with only
its declared seed changed. It reverses the candidate's two edits and requires
all other message and native bytes to match that reference. It independently
recounts all twelve inputs with the pinned offline tokenizer; all counts agree.
It checks 71 sealed public files, three local-only runtime files, 47 source
identities and the 17-record chain. [VERIFICATION.json](VERIFICATION.json)
preserves those results; it does not claim to certify direct reading.

| Identity | SHA-256 |
|---|---|
| Prepared manifest | b009fe4fdb2e0982c8cb1941791d622fb11cb05f84e80302481453234b4d2112 |
| Preparation seal | 57074b97fab747c939f689e36678f1088ad7b138a2ea2d6f5370c293586f29fe |
| Independent verification | 6703392e1a40570a79ffccd8bb793d9f3328119c49c3f9f5377fc1573aca30a2 |
| Retained reference | 75f774a6335da7a8d98dcbae4e4b025f2ab81a0421f74dd06503813fda4fba0f |

## Next decision

Recommend the bounded eight-request check in the specification, with exact
execution safeguards bound to this package before dispatch. No additional design
conversation is needed. The preparation script has no completion or live-action
execution route; the consumed sixteen-request runner cannot execute this scope.
The owner has not yet approved these newly specified eight calls. Follow the
existing separate execution boundary; do not rerun an old cell or add E01–E04.

Assess whether the actor understands the resource and navigation consequences
while making useful, correctly bound progress. A baseline check can remain
appropriate; a read or recovery can be useful; the same next action in both
arms is not required. Absence of a wording mistake in the new control would
limit this test's sensitivity. Thinking alone cannot prove action causality,
and accepted actions alone cannot show correct returned-object interpretation.

The two edits are one declared package; this comparison cannot isolate which
edit helps. Its small, selected examples cannot establish whole-task efficiency.
Keep the complete reference regardless. Accurate host-generated grouping and
object-scope clarity remain deferred options with explicit evidence requirements,
not rejected categories. The fresh changing investigation still needs a natural
pressure opportunity and its own action/generation allowance.
