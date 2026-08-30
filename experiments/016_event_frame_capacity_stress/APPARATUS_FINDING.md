# Experiment 016 Apparatus Finding

## Disposition

The offline qualification is valid and negative for the exact Experiment 015
event-frame representation.

No model server, endpoint, GPU, fresh measured fixture, or evaluator was used.
The proof exercised the actual candidate and tool implementations, the frozen
strict action byte bound, the pinned tokenizer, the existing reasoning/output
allowances, and the exact R50/X25 pre-request guard.

## What was executed

For each stress family, the host created sixteen files and then applied sixteen
sequential candidate-bound patches through `ToolExecutor`. Every action:

- passed strict JSON parsing;
- remained below the 5,000-byte raw-action cap;
- remained inside the frozen patch response schema;
- was accepted by the actual candidate patcher;
- produced the successor candidate bound by the next action.

The ordinary ASCII family used 512-character `old` and `new` fragments. The
escaped-control family used 170-character fragments. The largest escaped
action tokenized to 1,853 tokens; together with the full 512-token private
reasoning allowance it requires 2,365 tokens, below the frozen 2,500-token
completion allowance. The counterexample therefore does not depend on an
action that the execution envelope could never return.

Each complete sixteen-event request was then rendered twice: with result
bodies resident and with all result bodies externalized. Saved requests and
every exact action/result body are hash-inventoried in `qualification_artifacts`.

## Host-path validity

The R50 and X25 guards behaved fail-closed. The resident escaped-control frame
was denied under both envelopes. After result-body externalization, the same
request was admitted under the physical R50 envelope but still denied under
X25. No HTTP request was attempted.

Event sequences were contiguous. Resident results round-tripped exactly.
Externalized results retained phase-scoped exact custody. A simulated phase
transition started a new sequence at one under a distinct phase scope without
overwriting the prior sixteen results.

## Defect classification

This is not a tokenizer or guard defect. It is a representation-capacity
defect:

> V1 externalizes result-body fields but retains every historical action in
> full. Patch `old` and `new` payloads can therefore dominate the reconstructed
> decision frame.

The ordinary ASCII maximum passed X25 after result externalization, but with
only 1,858 tokens of total-envelope margin on the intentionally small stress
base. That is insufficient as a universal large-world proof. The fully legal
escaped-control sequence is a direct counterexample and defeats the contract.

## Scope

This finding does not say typical coding trajectories will contain sixteen
large patches. It says the current legal state machine permits a trajectory
that cannot be reconstructed even after performing the only externalization
operation V1 defines. A positive capacity guarantee cannot be based on the
average Experiment 015 transcript.

The R50 branch remains mechanically safe because the exact guard denies an
over-capacity next call. It is not guaranteed to retain sixteen maximum events.
The blocking result is that X25 cannot necessarily recover by externalizing
all result bodies.
