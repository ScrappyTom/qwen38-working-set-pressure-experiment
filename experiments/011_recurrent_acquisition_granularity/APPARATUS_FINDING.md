# Experiment 011 apparatus finding

## Disposition

The authorized primary run is **incomplete and not formally scorable**. It is preserved as immutable partial measured evidence. The model completed 108 HTTP calls, but the external execution host terminated the runner and its owned `llama-server` during the fourth shared prefix. The consumed authorization does not permit resumption or retry.

This was not a model response, a capacity denial, or a caught runner exception. The final durable event is preparation of `E11-OBS-KAPPA-S223607-P04`; its exact coding request, endpoint request, and rendered prompt are present, but no endpoint response exists.

## Exact terminal state

- Run started: `2026-08-29T15:10:05.468943+00:00`.
- Last complete actor result: cell 4 shared-prefix call 3, accepted exact read of `archive/ivory.py`.
- Terminal prepared call: cell 4 shared-prefix call 4, an exact read of `archive/jade.py`.
- The call was admitted at 17,876 offline prompt tokens under the 50,176-token prefix ceiling.
- The server log ends while decoding that request, at 61% prompt processing.
- There is no endpoint response, action, or result for the call.
- Neither the runner's exception receipt nor its orderly server-shutdown receipt was written.
- When inspected, both runner and server processes were absent and port 18113 was free.

The evidence supports abrupt termination of the owning process tree outside the recorded Python exception path. It does not identify the external terminating component with enough certainty to name it. In particular, the server log is not a crash report; it simply ends mid-request.

## Preservation

After confirming that no runner or server remained active, the partial tree was sealed without changing any saved prompt, response, reasoning, action, result, candidate snapshot, record chain, or runtime log. The receipt now records:

- 110 prepared invocations;
- 108 completed HTTP calls;
- one designed pre-HTTP capacity denial (`E11-OBS-IOTA-S173205-T25-L0-B10`);
- one externally interrupted HTTP call (`E11-OBS-KAPPA-S223607-P04`);
- zero retries, repairs, or rescues;
- no evaluator read before the partial seal.

The copied repository tree reproduces the sealed external tree by file count and byte count. Post-seal grading opened evaluator truth only for the five completed Phase-C candidates.

## Completed-path apparatus validity

The host-path audit found no apparatus defect in the 108 completed calls:

- every completed action parsed and was accepted;
- all 14 model-visible checks passed;
- all 14 complete stage record chains replayed;
- all runtime token-accounting deltas were zero;
- candidate, file, check, observation, and submission bindings remained exact;
- five Phase-C paths submitted, and all five passed hidden grading.

The cell-1 L0 capacity stop is an intended experimental outcome. Qwen completed the two required bridge files using four actor-sized pages. The exact next `fork_ready` request was then denied prospectively by the 25k guard. No model call was made for that denied request.

## Effect on validity

The termination does not retroactively invalidate behavior already observed. Three complete L0/L1 pairs remain valid partial measured evidence. It does prevent the frozen four-pair primary comparison from being scored or described as complete. Cell 4 never reached the treatment boundary, so neither of its L0/L1 branches was exposed.

No missing response is imputed. No interrupted call is counted as a model action. No branch is resumed from the partial state.

## Host-lifecycle lesson

An hour-scale GPU run must not depend on the lifetime of an interactive command session. Future measured execution should be owned by a durable operating-system process boundary with:

1. an exact detached launch record written before execution;
2. a persistent runner PID/process-group identity;
3. a durable heartbeat independent of the conversation/tool session;
4. explicit terminal status written by a supervisor even if the runner disappears;
5. exact pre-HTTP custody retained as in this run;
6. the same no-resume/no-retry semantics after actor exposure.

That is an execution-lifecycle amendment, not a change to L0, L1, the controller, the bank, or the model-facing treatment. It must be qualified and separately authorized before any future measured run.

## Boundary

No automatic successor, retry, same-bank repair, or additional actor exposure is authorized by this finding.
