# Experiment 011 — Recurrent acquisition granularity

## Question

Does deterministic maximal exact paging improve recurrent 25k completion when compared with actor-selected physical page size, under the already-earned controller?

This is a project-level reliability test, not a read-suppression study. Every read executes. There is no cache, duplicate interception, summary, ranking, semantic selection, or host-selected relevance.

## Conditions

- `T25-L0`: Qwen chooses `path`, `start_line`, and `line_count`.
- `T25-L1`: Qwen chooses `path` and `start_line`; the host returns the largest exact contiguous whole-line page that fits the frozen result bound and supplies exact continuation.

Both use the same AD-IQ2_S actor, 512-token low reasoning budget, P0, exact custody, purpose/progress projection, observation directory v2, ordinary tools, 25k admission guard, action budgets, checks, and reconstruction controller.

## Causal boundary

Four fresh case/seed prefixes are executed once using the historical interface. Each prefix is then cloned into both conditions. The read-mode treatment begins only after the first authentic pressure boundary.

Two fresh lexical sibling cases retain the prospectively earned recurrent observation-validity geometry: Phase B requires complete acquisition of two 192-line custody files before a second boundary; Phase C requires choosing and reopening the current candidate-bound observation rather than the stale one.

## Schedule and authority

- two fresh cases;
- two frozen seeds;
- two post-boundary branches per shared prefix;
- eight measured branches;
- one attempt per branch;
- no retry, repair, rescue, or automatic successor;
- evaluator truth remains unread until response sealing.

## Primary outcomes

- reaches second reconstruction;
- hidden-correct terminal candidate;
- public check and submission;
- stale/current observation selection;
- complete required-source acquisition;
- action-budget and capacity stops.

Secondary economics include calls, read calls, pages per required file, prompt tokens, runtime, redundant exact reads, and headroom before closure.

## Interpretation

L1 is supported only if it improves recurrent completion or acquisition economics without reducing hidden quality or evidence validity. A duplicate read is observed as model behavior and is never suppressed by the host.
