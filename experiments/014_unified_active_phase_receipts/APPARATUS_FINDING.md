# Experiment 014 apparatus finding

## Disposition

Experiment 014 is a valid, sealed, and formally scorable comparison of the
frozen `T25-SPLIT` and `T25-UNIFIED` conditions.

The run completed all four shared prefixes and all eight measured branches. It
prepared 120 prospective invocations, of which 112 reached the endpoint and
eight were denied before HTTP by the exact 25,000-token guard. No retry,
repair, rescue, or cross-cell history occurred. Evaluator truth was opened only
after the response seal.

The response seal inventories 4,633 files with aggregate SHA-256
`c31fd43111b8e8042151d9f8c48fae12b660a7af31230280c099d617736aee87`;
the seal document has SHA-256
`3ce601e7c646375e4e199fcc62253d8347aee324de8a3da2a4a3938c7e31b0ef`.
The repository copy is byte-identical to the external `C:\e14-primary` tree:
4,636 files, 193,460,877 bytes, and zero per-file SHA-256 differences.

## Live-path integrity

- all 112 endpoint response IDs are unique;
- every completed call has its exact coding request, rendered prompt, endpoint
  request, endpoint response, assistant reasoning, strict action, and result;
- every denied prospective call retains exact pre-HTTP request and prompt
  custody;
- all twelve stage runs replay successfully;
- all runtime token-accounting deltas are zero;
- every invoked public check passed;
- the owned server terminated and port 18117 was released;
- all eight post-seal hidden graders passed.

The server returned process code 1 after host-requested shutdown. The run,
response seal, grading, process termination, and port-release checks completed;
this is shutdown behavior rather than an experimental failure.

## One rejected model action

One of the 112 completed actions was rejected. In cell 3 `T25-SPLIT`, Qwen
mistyped the current candidate ID by inserting an extra character in its first
Phase-B patch. The exact mechanical rejection entered history. Qwen identified
the copied-ID error and issued the correct candidate-bound patch on the next
turn.

This was intended fail-closed host behavior and a recovered model error, not an
apparatus defect.

## Treatment fidelity

Within each cell, both branches began from the same exact shared candidate,
task, active step, observations, P0 root, seed, actor, budget, and tool
contract. Before the first Phase-B capacity reconstruction, the conditions
were byte-identical.

After reconstruction:

- `T25-SPLIT` exposed the exact externalized receipt prefix plus exact newer
  action/result pairs in ordinary history. Its receipt sequence did not advance
  for those newer pairs.
- `T25-UNIFIED` exposed the same exact history and result bodies, and also gave
  every newer action the next receipt sequence number in the one active-phase
  ledger.

Neither surface supplied relevance, sufficiency, next-action advice, semantic
summary, ranking, or hidden truth. Exact bodies remained separately visible or
reopenable. The only treatment was whether recent effects shared the same
mechanical progress sequence.

## Stale-check safety

The stale-check family intentionally required a passing check on candidate V1,
a mutation to V2, and another passing check bound to V2 before submission.

All four branches submitted only after a passing check whose
`checked_candidate_id` matched the submitted current candidate. The earlier V1
checks never authorized V2 submission. This closes the safety concern for the
tested paths: unifying receipt identity did not erase candidate validity or
turn an old check into a current one.

## Apparatus conclusion

No transport, capacity, checker, evaluator, replay, candidate-binding,
response-seal, or server-lifecycle defect affected the comparison. The one
rejected action was a model error handled by the frozen protocol. Experiment
014 is formally scorable.
