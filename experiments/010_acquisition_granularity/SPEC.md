# Experiment 010: deterministic exact acquisition granularity

Experiment 009 showed two distinct recurrent noncompletion modes after the
actor already had the right purpose and evidence: one redundant confirmation
read, and one actor-selected 50-line paging policy that exhausted the action
budget. This study isolates only the latter.

Two fresh lexical sibling tasks each require complete acquisition of two
198-line exact files, one small mutation, check `prefork`, and `fork_ready`.
The same Qwen3.8-27B-AD-IQ2_S actor, two frozen seeds, low private reasoning,
P0, action budget, checks, and candidate are used in both conditions:

- `L0`: `read(path, start_line, line_count)`; the actor chooses physical page
  size exactly as in Experiments 006-009.
- `L1`: `read(path, start_line)`; the host returns the largest exact contiguous
  whole-line page that fits the existing frozen result bound and reports an
  exact `next_start_line`.

L1 performs no semantic ranking, relevance selection, summarization, duplicate
suppression, or source interpretation. The model still chooses which file and
where to begin; the host chooses only how many exact contiguous bytes physically
fit. A single source line that cannot fit fails closed.

The eight cells are two cases x two seeds x two conditions, counterbalanced.
Each cell receives one attempt, no retries, repairs, rescues, cross-cell history,
or feedback. The maximum is ten actions. Reasoning is enabled with the already
qualified 512-token private allowance and is omitted from subsequent history.

Primary measures:

- completion of both required full-file reads;
- mutation, public check, and `fork_ready` closure;
- read-action count and exact returned coverage;
- actor-selected line counts under L0;
- prompt tokens, completion tokens, calls, and elapsed time;
- page fragmentation failures;
- duplicate/no-new-information reads, reported separately.

L1 earns promotion only if it improves full acquisition or closure without
reducing hidden correctness or introducing host-path defects. It does not claim
to solve redundant confirmation reads.

The observation-directory v2 correction is qualified in the same offline
implementation commit but is not a treatment in these cells. Historical v1
requests and replay remain byte-identical. V2 uses literal capture order and
does not claim that stage-local sequence numbers form one global ordering.

No observation, relationship, summary, ranking, embedding, declaration,
retention feature, duplicate-result policy, or additional reasoning mode is
authorized.
