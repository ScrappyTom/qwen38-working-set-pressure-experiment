# Interpolation run-002: interrupted-attempt reconciliation

The recorded prefix replays exactly through C21. It contains **21 complete
responses, 34 operations and no new test or documentation edit**. C22 was
dispatched on September 16, 2026; no response or normal closure was preserved.
Its outcome is unknown. This is an interrupted development attempt, not a
completed task or a measured model failure at C22.

The original run remains unchanged. `INTERRUPTION_SEAL.json` is a retrospective
inventory of existing bytes, explicitly not a replacement `RESPONSE_SEAL.json`
or an invented `runtime_closed` record. Private runtime file identities are
listed separately; their contents remain local. This audit runs no Qwen request,
checker subprocess, tokenization or runtime launch.

## What was verified

`audit_interruption.py` checks the 393 identities in the original execution
manifest, the full 845-record custody chain and all 1,119 recorded artifact
references (949 distinct paths). It reconstructs 84 native inputs from the
unchanged pinned request code and compares the saved native/template/wire bytes
and token-list lengths. It does not retokenize them or independently rerun the
decoder.

The 21 final replies decode exactly to their saved actions. Every recorded
operation, host result, intermediate state and candidate reproduces through
replay. The one new baseline-check observation is recovered from saved bytes,
without re-execution. Every displayed current-source extent in each of the 22
dispatched requests is checked against the exact unchanged candidate bytes.

The final committed checkpoint is `after/C21-O01-state.json`, with candidate
`after/C21-O01-candidate.json`. The candidate bytes equal `starting-candidate.json`
exactly; its identity remains
`047eeceb0bc5b21006965a5acec83b6f79e1ddcb4ea8744b30985d3c20c52f78`.
The initial candidate already contains previously assisted work. Its preservation
does not make this a fresh end-to-end backport.

The next input reconstructed from that checkpoint exactly equals the archived
C22 wire request. It contains C21's returned source, the existing selection and
the model-authored C19 account. No C22 reply may be inferred from this fact.

## Costs and remaining opportunity

| Measure | Recorded value |
| --- | ---: |
| Completed model replies | 21 |
| Dispatched requests | 22 |
| Completed-request time | 1,930.72 seconds / 32.179 minutes |
| Completed-request input tokens | 293,079 |
| Completed-request generated tokens | 22,731 |
| Peak sent input | 23,808 tokens |
| Peak completed input plus generation | 26,841 tokens |
| C22 dispatched input | 13,618 tokens |
| Minimum sampled free GPU memory through dispatch | 186 MiB |
| Recorded operations | 34 of 96 |
| Requests still available if C22 is charged as dispatched | 10 of 32 |
| Operations still available | 62 |

The reported time/tokens exclude C22's unknown generation and latency. They are
not an exact whole-attempt cost. The saved C21 state says 21 requests used;
continuation accounting must additionally retain the unreturned C22 dispatch.
It must not reset the historical allowance or label C22 a free request.

The 34 operations are thirteen account updates, thirteen reads, five searches,
one baseline check and two selection replacements. Two reads were rejected for
capacity; both rejections reached the following input. The other operations were
accepted, but an accepted baseline check returned a real failing assessment.
No edit, successor check or submission occurred.

## Interpretation and continuation boundary

The direct review is in `../LIVE_REVIEW.md`. It now includes the previously
undocumented C11–C13 details and the complete C19–C21 outputs and actual next
inputs. That review distinguishes model-chosen recovery from completed work,
source actually absent from merely reread source, and account authorship from
supported understanding.

Two reporting problems remain justified correction candidates: inherited
submission feedback lacks the prior-work episode label already present in recent
activity, and a shortened requirement list combines Basic rows with an Extended
cross-section description while leaving the actor to infer the remaining eighteen
paths. Later source acquisition also exposes a separate navigation-retention
question: recovery omits previous search coordinates after another operation.
Those findings do not explain all repeated acquisition or establish that any one
repair will produce completion.

A separately frozen corrected-host continuation can begin from the exact last
committed checkpoint. It should retain candidate, evidence, attributed account,
original task boundary and known consumed operations; conservatively charge the
unknown C22 request. It must not inject a reviewer-selected group, correct the
model's account silently, execute an internal draft or relabel earlier work.

The audit cannot establish normal shutdown, C22 output, full runtime duration or
an allocation-failure cause. Those are deliberately absent from the verification
claim. A later machine-level absence check can authorize a new owned runtime, but
cannot retroactively prove the original runner closed normally.

## Audit development note

The first successful audit/seal pair is preserved as `INTERRUPTION_AUDIT-001.json`
and `INTERRUPTION_SEAL-001.json`. Adding explicit displayed-source checks and
operation counts caused the exclusive output writer to refuse overwriting those
files. They were retained under the numbered names, and the completed rerun
produced the unsuffixed files. This was an audit-output collision, with no change
to run bytes and no inference or checker execution. The final unsuffixed files are
the prospective continuation's audit inputs.
