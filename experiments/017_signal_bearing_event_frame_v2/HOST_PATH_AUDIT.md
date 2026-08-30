# Experiment 017 Host-Path Audit

## Coverage

All 21 saved coding requests, endpoint requests, rendered prompts, endpoint
responses, private-reasoning outputs, strict JSON actions, tool results, and
hash-chained branch records were reviewed. All six branches were replayed.

| Cell | Seed | Model actions in order | Host decision after each action | Terminal class |
|---|---:|---|---|---|
| closure mint | 173205 | `check`, `submit` | accept/pass; accept terminal submission | completed |
| closure mint | 223607 | `reopen_result`, `read`, `check`, `submit` | accept exact reopen; accept exact read; accept/pass; accept terminal submission | completed |
| stale sable | 173205 | `check`, `submit` | accept/pass on current candidate; accept terminal submission | completed |
| stale sable | 223607 | `check`, `submit` | accept/pass on current candidate; accept terminal submission | completed |
| historical signal | 173205 | `reopen_event`, `read`, `patch`, `patch`, `check`, `submit` | accept exact payload; accept exact read; reject stale candidate binding and offer next call; accept corrected patch; accept/pass; accept terminal submission | completed after bounded rejection |
| historical signal | 223607 | `reopen_event`, `read`, `patch`, `check`, `submit` | accept exact payload; accept exact read; accept patch; accept/pass; accept terminal submission | completed |

No request was denied before HTTP. No next call was withheld after the one
recoverable rejection. No actor path was classified from a terminal label
alone.

## Signal and payload boundary

Before the first historical-signal call, Qwen received:

- accepted action type `patch`;
- readable target `archive/source.dat`;
- predecessor candidate/file bindings;
- successor candidate/file bindings;
- external payload field names `old,new`;
- payload size/hash;
- handle `EVT-0001`.

It did not receive `ARCHIVE-Z7`, either in the coding request, endpoint request,
or rendered prompt. The marker first entered model-visible state as the exact
result of Qwen's `reopen_event(EVT-0001)` action.

The host did not rank the event, label the marker as relevant, preview its
payload, or choose the handle. It exposed mechanically grounded event identity
and exact access capability; Qwen selected and interpreted the body.

## Candidate/check safety

Both stale-check branches distinguished a passing check bound to the predecessor
from the need for a new check on the current repaired candidate. Neither opened
the old check body. Both issued a current-candidate check and submitted only
after it passed.

The one malformed candidate ID in cell 5 was not admitted. Because the rejected
event preserved the attempted target/status while top-level current candidate
identity remained resident, Qwen corrected it without host repair or rescue.

## Lifecycle and custody

- prepared invocations: 21
- HTTP completions: 21
- completed accepted actions: 20
- completed mechanically rejected actions: 1
- retries/repairs/rescues: 0/0/0
- response seal before evaluator access: yes
- hidden passes: 6/6
- server shutdown: verified
- runtime token-accounting deltas: all zero
