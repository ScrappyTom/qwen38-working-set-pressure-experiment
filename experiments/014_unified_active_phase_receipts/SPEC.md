# Experiment 014 — Unified active-phase receipt sequencing

## Question

After a 25k reconstruction, does assigning every newly completed action the
same monotonic active-phase receipt sequence eliminate repeated passing checks
without permitting submission based on a check bound to an older candidate?

## Conditions

- `T25-SPLIT`: the Experiment 013 receipt surface. The numbered receipt ledger
  freezes at the latest reset; newer exact action/result pairs live only in
  post-reset history.
- `T25-UNIFIED`: identical, except every post-reset action also receives the
  next receipt sequence immediately. Exact result bodies remain in recent
  history or behind the same `reopen_result` handles.

The conditions are byte-identical until the first post-reset action completes.
No receipt contains relevance, sufficiency, a semantic summary, ranking, or a
recommended action.

## Fresh cases

- `E14-CLOSURE-MINT`: exact observation, patch, and two large reads occur
  before reconstruction. A passing current-candidate check must then lead to
  submission.
- `E14-STALE-SABLE`: a public check passes on candidate V1, then a patch creates
  V2 and invalidates that result. After reconstruction, Qwen must check V2 and
  submit rather than relying on the stale pass.

Two frozen seeds produce four shared prefixes and eight measured branches.

## Primary outcomes

- hidden-correct final candidate;
- passing check bound to the current candidate;
- submission;
- repeated passing checks;
- stale-check reliance or rejected submission;
- calls, tokens, resets, and exact result reopening.

## Frozen execution

- Qwen3.8-27B AD-IQ2_S, llama.cpp b10434;
- 25,000-token ceiling;
- server-enforced 512-token private reasoning, omitted from later history;
- maximal exact reads;
- sixteen Phase-B calls;
- at most four counted reconstruction states including the first boundary;
- one attempt, no retry, repair, rescue, or cross-cell history;
- no summaries, relationships, embeddings, ranking, read suppression, or host
  semantic selection.

No same-bank rerun or automatic successor is authorized.
