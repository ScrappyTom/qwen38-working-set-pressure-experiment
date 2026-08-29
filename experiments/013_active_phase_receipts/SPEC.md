# Experiment 013 — Exact active-phase receipts

## Question

When a large active phase crosses repeated authentic 25k boundaries, does a
compact exact ledger of completed action/effect receipts preserve enough
mechanical progress for Qwen to close the phase without carrying full result
bodies resident?

## Conditions

- `T25-LATEST`: the Experiment 012 controller. On each in-phase reset it keeps
  only the latest complete action/result pair.
- `T25-RECEIPTS`: the same controller, actor, task, tools, budgets, and exact
  world, but it externalizes result bodies and exposes compact exact receipts
  for completed actions. Any body is available through
  `reopen_result(handle)`.

Receipts contain only mechanically established identity, binding, range,
completion, hash, size, and acceptance fields. They contain no semantic
summary, relevance, sufficiency judgment, ranking, or recommended next action.
Repeated reads are accepted normally; there is no suppression or cache return.

## Fresh bank

Two fresh 160-file sibling worlds are used:

- a readable-P0 governing-source case using the new `lumen-` value;
- a candidate-bound observation case using the new `D4::` marker.

Each has a shared Phase A and a large Phase B whose correct mutation and two
complete ledger reads occur before check and submission. Two frozen seeds give
four shared prefixes and eight measured branches.

## Primary outcomes

Quality and closure are primary:

- hidden-correct terminal candidate;
- model-visible public check;
- submission;
- repeated acquisition after reconstruction;
- exact use or non-use of receipt bodies;
- capacity and call-budget stops.

Calls, prompt tokens, endpoint time, reset count, receipt bytes, and result
reopens are secondary economics.

## Frozen limits

- Qwen3.8-27B AD-IQ2_S;
- llama.cpp b10434;
- 25,000 total-token ceiling in both conditions;
- 512 private reasoning tokens, omitted from later history;
- maximal exact whole-line reads;
- fourteen Phase-B model calls;
- at most four counted reconstruction states including the first boundary;
- one attempt, no retry, repair, rescue, or cross-cell history.

No same-bank rerun or automatic successor is authorized.
