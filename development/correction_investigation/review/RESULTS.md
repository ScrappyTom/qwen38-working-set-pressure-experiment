# Receipt corrections: completed, with the interface retained

Qwen completed R01 in **14 actions**, made the correct repair, passed **all 38
public cases on its first check**, and submitted that same candidate. The
single owner-approved attempt is consumed. All fourteen complete responses and
actual inputs/results were directly reviewed after sealing and exact replay.

The fix routes each signed contribution to its own receipt's depot/item. This
removes the old receipt from its original group when a correction changes depot
or item, then adds the new receipt to its new group. Validation, revision
selection, duplicate handling, void transitions and independent receipts remain
unchanged and pass the explicit cases.

| What Qwen saw | What Qwen did | What the host did next | Interpretation |
|---|---|---|---|
| Root, then newly discovered nested paths | Four distinct directory pages; exact reads through API, registry and reporting | Returned and delivered each actual page/source | Useful navigation; no repeated-parent operation |
| A fixed destination and separately signed before/after contributions | Explained the mismatch, read records, then patched totals.py | Accepted exact guards and delivered the successor/diff | Correct source-led diagnosis; no failed repair |
| Accepted edit plus still-unread import/validation modules | Reconsidered alternatives, then first-read both modules | Delivered their current source | Real new evidence, alongside substantial repeated thinking |
| A new passing check on the unchanged successor | Submitted that same candidate | Recorded checked terminal completion | Correct use of actual verification; no redundant check |

## Cost and limits

| Measure | Observed |
|---|---:|
| Model-request time | 918.847 seconds / 15.31 minutes |
| Task-loop wall time | 928.469 seconds / 15.47 minutes |
| Cumulative input / generated tokens | 100,163 / 13,348 |
| Initial / peak native input | 3,170 / 13,588 |
| Calls left before / after first check | 12 / 11 |
| Calls left after submission | 10 |
| Minimum sampled GPU free memory | 321 MiB, advisory policy |

Calls 010–012 produce 60.6% of generated output and take 53.3% of request time.
Their full thinking includes useful edge-case checks and repeated reconsideration
of the same repair and already supplied requirements. Those percentages are
whole-response costs, not an estimate of waste. The complete tool contracts
remain available and correctly used; the current evidence does not identify a
missing clarification that would reliably reduce this effort.

Session wording remains imperfect: 011 questions whether the recorded edit was
from a prior session; 013 calls it a previous-session edit despite the actual
annotation. Both use the correct current candidate, and neither treats the
original symptom as a new failure after that edit. Preserve this residual
uncertainty without claiming its causal contribution or erasing it behind success.
012 also briefly guesses file sizes incorrectly, without extra navigation.

Qwen repairs before its first check. It refines its diagnosis from source, but
does not reverse a committed explanation after a failed diagnostic or recover
from a failed repair. All acquired history stays resident, with no pressure
boundary; prior thinking is omitted immediately by the protocol. This authored
task does not establish independent real-world discovery, pressure continuity,
general correctness or a speed comparison with earlier unlike tasks.

## Decision and next question

**Retain the current interface and thinking settings.** This run earns no host
patch, wording variant, suppression rule or memory feature. It also earns no
automatic clarification dialogue solely from lengthy responses. The owner's
caution about pressure to propose changes applies to both Qwen and Codex.
Keep the residual temporal mismatch and administrative distraction recorded;
if they produce a consequential misunderstanding, examine the actual input in a
small separate neutral conversation before settling any new presentation.

The remaining investigation question requires a task where observed diagnostic
outcomes meaningfully separate plausible explanations, beyond a small source
mismatch. A future hypothesis is that Qwen will use a contradicting observation
to revise its explanation and select a corresponding useful next action; unchanged
pursuit of the ruled-out explanation under available evidence would count against
it. Qualification must not require a wrong first action, forced check or padding.

A separate hypothesis is that residual session terminology can remain
operationally harmless with current version/evidence bindings. Treating an old
incident as a new failed repair, using a wrong candidate, or repeating unchanged
work because of that association would contradict it and earn focused dialogue.
Neither hypothesis is resolved by these passing cases. No further live task or
comparison is activated by the ten unused actions.

See [direct review](DIRECT_TRANSCRIPT_AUDIT.md), [host audit](HOST_PATH_AUDIT.md),
[apparatus limits](APPARATUS_FINDING.md), [execution receipt](EXECUTION_RECEIPT.md)
and [verification](VERIFICATION.json). The preparation's eleven focused mocked
checks passed; this report makes no full-suite claim.
