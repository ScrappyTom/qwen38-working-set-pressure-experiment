# Experiment operating rules

This repository exists only to test single-boundary exact-context
reconstruction. Keep it smaller than its evidence donor.

Read in order:

1. the active experiment `SPEC.md`;
2. its frozen authorization, schedule, and execution package;
3. `docs/ANALYSIS_GOVERNANCE.md`;
4. prior experiment results and direct transcript audits;
5. `README.md`.

Authority order is direct owner instruction, the active `SPEC.md`, the
implementation plan, analysis governance, then explanatory documents.

Non-negotiable rules:

- preserve exact prompts, outputs, actions, results, candidates, observations,
  token counts, and branch ancestry;
- inspect every saved model input and output before diagnosing behavior;
- do not use evaluator truth, known-good patches, or host-selected relevance
  in the model loop;
- do not add summaries, retention declarations, relationship graphs,
  embeddings, ranking, or semantic host routing;
- one invocation yields at most one strict JSON action;
- one attempt, no retry, repair, rescue, or cross-cell history;
- C50 and T25 must fork from the same exact task, candidate, chronology, and
  pending work within each family/seed;
- any feature or patch must be earned by a directly observed need;
- seal responses before evaluator access;
- measured work is incomplete until every transcript receives a durable direct
  audit and goal-level synthesis.
