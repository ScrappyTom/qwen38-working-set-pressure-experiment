# Experiment 004: bounded-reasoning evidence-to-action diagnostic

## Question

When a fresh 25k reconstruction already carries the verbatim Phase B pointer
and Qwen reacquires the exact governing source or historical observation, does
a small private reasoning allowance improve the transition from evidence to a
candidate-bound patch?

This is not a metadata, retention-policy, digest, workspace, or general
reasoning benchmark. It tests the one failure left by Experiment 003.

## Conditions

- `R0`: private reasoning disabled.
- `R1`: low reasoning effort with a hard 512-token reasoning budget per model
  call.

Both conditions receive the same actor model and quantization, seed, sampler,
fresh fixture, exact shared prefix, 25,000-token active-total ceiling, P0,
verbatim progress pointer, exact observation directory, tools, eight-call
continuation budget, check, and hidden grader.

The common final-answer contract is one strict bare JSON action. `R1` may emit
private reasoning only through llama.cpp's separate `reasoning_content` field;
that exact field is custodied but never inserted into later model history.

## Fresh cases

- `E4-SOURCE`: Phase B requires the current namespace from a large Phase A
  source and a small target repair.
- `E4-OBSERVATION`: Phase B requires reopening an exact dynamic prefix observed
  during Phase A and applying it to a small target repair.

The cases are fresh sibling geometries. They were not selected from observed
reasoning-enabled behavior and do not reuse Experiment 003 candidate bytes,
paths, facts, check scripts, or seeds.

## Schedule

- two exact shared prefixes, one per case;
- one matched `R0` and one matched `R1` branch per prefix;
- branch order alternates by case;
- one attempt per call;
- zero retries, repairs, rescues, or cross-branch history;
- at most 18 prefix calls and eight continuation calls per branch;
- no automatic successor.

## Prospective interpretation

The primary behavioral sequence is:

1. acquire or reopen the required exact fact;
2. stop redundant acquisition;
3. patch the exact target with current candidate/file bindings;
4. pass `public` and submit within the 25k envelope.

Hidden correctness, completion, repeated reads after the governing fact,
evidence-to-patch latency, call count, prompt/completion/reasoning tokens,
maximum occupancy, and closure are reported separately.

`R1` is a useful lead only if it improves the evidence-to-action transition
without introducing protocol failure, premature unsupported mutation, hidden
quality loss, or unacceptable capacity cost. Two cases are diagnostic, not a
population estimate.

If `R1` still loops after the required exact fact is visible, the next earned
design target is an explicit readiness-discriminating action-phase mechanism or
a smaller action surface. It is not richer metadata or another generic note.

## Development gate

Before exposing this bank, one development-only live uptake check must verify:

- server reasoning mode `auto` with request-level off/on control;
- a nonempty, bounded `reasoning_content` field for `R1`;
- strict final JSON action extraction and normal tool execution;
- exact request, rendered prompt, reasoning, response, action, and result
  custody;
- runtime token accounting within the existing allowance;
- clean shutdown and port release.

The development result is apparatus evidence only and cannot select or modify
the fresh measured cases.

## Analysis requirements

Every measured prompt, reasoning field, final output, action, result, candidate,
check, and terminal state must be inspected directly. The durable audit must
distinguish improved reasoning content from improved external action. Reasoning
text is explanatory evidence, not evaluator truth and not proof that the model
used a proposition causally.
