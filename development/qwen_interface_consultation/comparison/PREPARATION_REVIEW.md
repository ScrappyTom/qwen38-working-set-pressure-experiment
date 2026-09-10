# Visible tool-reference comparison — prepared September 10, 2026

Sixteen exact ordinary-action requests are prepared, natively rendered and
independently recounted. **Zero completion calls were made.** The selected
q4/56,576 runtime closed normally. The [specification](SPEC.md) preserves the
existing separate execution decision; this is no authorization or claim of a
completed comparison. No variant has been promoted to the shared host.

## Selected intervention and its evidence

The [complete design review](../follow-on/continuation/design-review/RESULTS.md)
retains Qwen's preference for visible operation contracts using current names.
The prepared [reference](preparation-001/TOOL_REFERENCE.txt) supplies every
required argument, type and schema constraint, followed by source-checked
effects and host limits. It groups operations into repository access, candidate
operations and saved-information access. This uses the concrete catalog approach
favored in D1–D4 while correcting omissions and inaccurate proposed effects.

The reference is appended to the ordinary system message before the user state.
Every other part of the paired API requests and native inputs is unchanged:
task/source/state, neutral IDs, resource and navigation wording, output grammar,
sampler, thinking configuration and executor. The added information and its
placement together constitute this one presentation variant; an outcome cannot
isolate a particular sentence or claim an effect from names alone.

Schema forms come from `action_schema` in
[`tools.py`](../../../src/working_set_exp/tools.py). The manual effect text was
directly checked against that executor, [`candidate.py`](../../../src/working_set_exp/candidate.py),
[`hierarchical_p0.py`](../../../src/working_set_exp/hierarchical_p0.py), and
[`isolation.py`](../../../src/working_set_exp/isolation.py). This includes the
pre-edit guards, exact replacement/byte constraints, current-check invalidation,
check stream limits, lack of a passing-check enforcement gate on submit, and
actual retrieval envelopes. A saved event address is not automatically a saved
action payload; event retrieval returns old/new rather than adding original
path/version guards. These facts address concrete inaccuracies in the model's
suggestions without changing stored records or executable protections.

State ledgers, new version-aware coverage/check fields, hiding a resident diff,
resource/navigation rewording, payload-object regrouping and memory refactoring
remain deferred in the [design decision](../follow-on/continuation/design-review/DECISION.json).
The generic return/effect descriptions are part of the tool reference; this
comparison does not establish a repair to payload interpretation from an
accepted retrieval alone.

## Direct inspection of what the actor would receive

The reviewer directly read the complete generated reference, then its actual
native system block in C02 and the legacy native block in C01. Both include the
runtime's same xhigh instruction and unchanged ordinary-action system text.
The reference is visible before the full user state. The native suffix starts
the assistant thinking channel; no prior answer, diagnostic question or design
response appears in these conversations.

The four complete source states had already been directly read for D1–D4, with
the scope recorded in the [input review](../follow-on/continuation/INPUT_REVIEW.json)
and [full direct audit](../follow-on/continuation/design-review/DIRECT_TRANSCRIPT_AUDIT.md).
For this preparation, all four original requests, candidate/session snapshots
and provenance files were byte-compared with those reviewed design inputs.
Every one of the sixteen user messages equals that exact original state with
only recursive fixture_id substitution to I1–I4. Both arms use the same
substitution; seeds alter no message text. This review reuses the verified
identical source bodies instead of claiming sixteen separate rereadings of
duplicate material.

Independent checks establish that removing the single added reference from
each native variant yields its paired native legacy prompt byte-for-byte.
The template trims the system message's final newline. An initial verifier
assumed the API's trailing newline survived; direct native inspection corrected
that verifier assumption. No request, template, preparation seal or model-facing
wording was changed, and no completion was involved.

## Native cost and capacity

Each row is used at both seeds, 42 and 314159, with condition order reversed
between seeds. Four states × two seeds × two conditions gives sixteen requests.
For I1/I3, seed 42 is legacy-first and seed 314159 is reference-first; I2/I4
reverse that order. Thus order alternates by seed within each state and by
state within each seed. The manifest freezes the full dispatch sequence.

| State | Legacy input | Reference input | Added input | Physical generation space with reference |
|---|---:|---:|---:|---:|
| I1, crowded source | 18,714 | 20,389 | 1,675 | 36,187 |
| I2, old passing check | 2,882 | 4,557 | 1,675 | 52,019 |
| I3, first repair | 1,597 | 3,272 | 1,675 | 53,304 |
| I4, historical patch and partial read | 2,210 | 3,885 | 1,675 | 52,691 |
| Prospective total input processing, two seeds | 50,806 | 64,206 | 13,400 | Not additive |

The reference is 7,013 UTF-8 bytes. The largest native input is below the
23,808 admission ceiling, leaving 3,419 tokens beyond the prospective 32,768
generation reserve. Thinking and final output remain uncapped; the reserve is
an admission choice, not a guarantee or a future 25k investigation allowance.
No output length, action acceptance, time saving or whole-task benefit has
been measured for this variant.

Native preparation used the pinned IQ3_XXS model and b10434 runtime, q4_0 K/V,
56,576 context, full offload, fitting off, no MTP/context shift and unchanged
xhigh thinking. Monitoring recorded 42 samples and a 563 MiB minimum during
load/template/tokenization preparation. This includes no generation and is not
a replacement capacity qualification. The completed continuation's minima remain
335 MiB for Q2/Q3 and 339 MiB for design, under the owner's advisory 350 MiB
policy. Final inspection found no running server and 11,773 MiB free on the GPU.

## Verification and preserved identities

[Independent verification](VERIFICATION.json) passed all checks: 86 sealed
public files, three local private-runtime files, 21 chained records, 45 source
identities, all sixteen offline/native token matches, unchanged state snapshots,
fresh conversations, counterbalanced condition order and exact single-block
treatment isolation. All sixteen preparation records show no completion sent;
only apply-template/tokenize POST routes occur. Shutdown and the free port are
recorded. Private launch paths and logs remain ignored, with their hashes sealed.

The focused interface suite has 25 passing tests, including five preparation
tests for isolation, schema coverage, zero-completion routes, admission failure,
sealed stops and altered-package rejection. The final reference wording was
rechecked by those five tests. This is not a full-suite run or model evidence.

- [Package manifest](preparation-001/PACKAGE_MANIFEST.json):
  `f8fab01274a39d12acd24e544d81056d4000a3e1a81652cd05d631c8f5328ca5`.
- [Preparation seal](preparation-001/PREPARATION_SEAL.json):
  `c6b78560328cfb86c3a9d3315002b35b493a416dae321218b08d1ebcb9c3f44b`.
- [Prior design decision](../follow-on/continuation/design-review/DECISION.json):
  `2fa6d70caa4f883bba76b26af7c0c26f85c28aa3b8f710e0e755c143f6434bc0`.

The next substantive evidence would come from the specified sixteen ordinary
actions and their complete transcript/host review. The current preparation
script cannot run them. Their separately bounded execution path must preserve
these exact requests and settings, one action on a fresh reconstructed state,
no retry/rescue, raw output custody, independent replay and complete direct
audit. The changing-investigation study remains withheld pending credible
natural pressure and its own task-specific allowance.
