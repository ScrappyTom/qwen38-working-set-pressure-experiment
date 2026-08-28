# Experiment 003: Verbatim progress-pointer diagnostic

## Question

At an authentic 25,000-token reconstruction boundary, is the failure to continue caused by missing task-progress state rather than missing source orientation or exact custody?

## Earned intervention

Experiment 002 showed that reconstructed branches restarted Phase A despite receiving the exact full task, current candidate, latest fork result, P0, and an exact observation directory. The intervention is therefore limited to one additional mechanically safe field:

- `completed_protocol_stage: phase_a`, mechanically established by the accepted `fork_ready` result;
- `active_protocol_stage: phase_b`;
- `active_step_verbatim`, copied byte-for-byte from a separately frozen user-authored Phase B task component;
- the component SHA-256 and an explicit statement that no semantic host summary was produced.

The pointer contains no inferred relevance, source fact, observation body, expected patch, or evaluator truth. The full original task remains present in both conditions.

## Conditions

- `T25-M`: the current mechanical reconstruction contract from Experiment 002.
- `T25-P`: exactly `T25-M` plus the frozen verbatim progress pointer.

Both use reasoning off, the same AD-IQ2_S actor, P0, exact ordinary tools, exact external custody, one attempt per call, no retries, and a 25,000-token active-total ceiling.

## Fresh geometries

- `E3-SOURCE`: Phase B requires reacquiring an exact governing source fact via P0 and exact read.
- `E3-OBSERVATION`: Phase B requires reopening an exact historical probe result absent from source.

Each geometry has one exact shared live prefix followed by matched `T25-M` and `T25-P` continuations. The observation probe is a one-shot capability: after its first accepted result it is absent from subsequent request and response schemas. This prevents repeated probes from consuming the prefix without adding information.

## Frozen schedule

- Source seed `314159`: `T25-M`, then `T25-P`.
- Observation seed `173205`: `T25-P`, then `T25-M`.
- Prefix call limit: 18.
- Continuation call limit: 8.
- Maximum prospective completion calls: 68.
- One attempt per call; zero retry, repair, rescue, or automatic successor.

## Pass criteria

The pointer is useful only if `T25-P`, relative to its matched `T25-M` branch:

1. does not restart Phase A;
2. uses P0 to target and read the governing source in `E3-SOURCE`;
3. reopens the exact historical observation in `E3-OBSERVATION`;
4. mutates, runs `public`, and submits within the 25k boundary; and
5. preserves hidden-grader correctness.

Final quality, actions, prompt tokens, redundant reads, time-to-governing-evidence, and evidence-to-mutation lag are reported separately. A two-case diagnostic cannot establish a general population effect.

## Evidence and review

All exact requests and outputs are custodied before evaluator access. Responses are sealed before hidden grading. Every prompt/output pair is directly reviewed, including model-quality failures. Infrastructure failures stop the study; ordinary model failures remain outcomes.
