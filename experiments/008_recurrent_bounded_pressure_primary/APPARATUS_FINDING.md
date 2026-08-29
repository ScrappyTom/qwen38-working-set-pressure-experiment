# Experiment 008 apparatus finding

## Disposition

The sealed run is valid as immutable partial measured evidence. It is not the
complete four-cell primary study and cannot support the frozen paired promotion
decision.

The run produced 87 HTTP completions from 89 prepared invocations, with zero
retry, repair, or rescue. One prepared invocation was mechanically denied by
the 50,176-token capacity guard. The other had exact pre-transport custody and
was in flight when the operator interrupted the server after misreading stale,
cell-scoped filesystem monitoring as evidence of an unbounded call.

The response tree was immediately sealed. No exposed cell was resumed or
rerun. The fourth frozen cell was never exposed.

## Execution integrity

- actor: Qwen3.8-27B AD-IQ2_S, SHA-256
  `d416fa422c9035605c778f60d90a94b288c38b4f9ec2126b58ef938ce8d5f716`;
- llama.cpp: b10434, one 50,176-token slot, full GPU offload;
- private reasoning: enabled with a server-enforced 512-token maximum and
  excluded from subsequent chronology;
- response allowance: 2,500 tokens;
- seeds exposed: 173205 for both geometries and 223607 for E8-SOURCE;
- prepared invocations: 89;
- completed HTTP calls: 87;
- retries, repairs, and rescues: zero;
- sealed files: 885;
- sealed response aggregate:
  `42f8ec2177f12cb0a6e0381ad42275a5316df14642b3a2f6a199d5feca6f2d02`;
- response-seal SHA-256:
  `5158e0ee920e1ac14a9f20cd869ecee6f831268f66d5fedbf959073f64f39b05`;
- server shutdown and port release: verified.

Every completed call has exact coding-request, endpoint-request,
rendered-prompt, raw endpoint-response, assistant-content, private-reasoning,
and tool-result custody. The interrupted call has exact request-side custody
but no response artifact, because no response was accepted before shutdown.

All 885 sealed artifacts and their aggregate were reverified after copying the
run into the repository. Eleven terminal stage record chains and summary
bindings pass the existing custody verifier. The twelfth, interrupted stage
has a valid hash-chained partial record containing one completed action and the
following prepared invocation.

## Pre-exposure qualification corrections

Two corrections happened before any E8 actor exposure and are already
disclosed in `PRESEAL_QUALIFICATION_NOTES.md`:

1. a lexical sibling-fixture rename left the source checker importing the
   wrong generated module; the generator was corrected and every derived bank
   artifact rebuilt;
2. the observation scripted path landed six tokens below the intended 25k
   edge, so one inert required ledger row was added and all identities rebuilt.

Neither correction used model behavior. The final bank was sealed only after
both scripted paths proved two 25k denials, 50k admission, and a hidden-correct
known-good successor.

## Operator interruption

The operator polled only the cell-02/C50 evidence count. That count correctly
stopped changing when the C50 observation branch hit its physical capacity
guard, but the runner continued to cell 03. The stale scoped count was
mistaken for one hung completion. The operator sent Ctrl-C while cell-03/C50
Phase C call 2 was in flight.

This was not a llama.cpp timeout, a runner deadlock, an endpoint-envelope
failure, or a model-quality stop. It is an operator-caused integrity event.
The proper response is preservation and limited interpretation, not a retry.

Future live monitoring must follow the global receipt/record chain and current
server activity. A count scoped to one completed branch is not a valid liveness
signal. This process correction does not require a model-facing or controller
change.

## Valid evidence boundary

The interruption does not retroactively invalidate the preceding completed
calls. They support:

- direct analysis of all completed prompts, reasoning, actions, and results;
- exact stage-end candidate grading;
- one completed recurrent T25 source trajectory;
- observed call- and capacity-bound failures before a second transition;
- qualitative analysis of purpose, acquisition, and evidence-validity policy.

They do not support:

- a complete C50/T25 paired primary comparison;
- a four-cell success rate;
- a seed-reliability estimate;
- a conclusion about Phase-C current-versus-stale observation choice;
- replacement or continuation of the interrupted cell.

The formal research disposition is
`immutable_partial_measured_evidence_not_complete_primary`.
