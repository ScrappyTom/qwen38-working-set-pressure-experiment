# Experiment 011 results and decision

## Executive result

The exact four-pair primary run is incomplete and formally unscorable because the external execution host terminated during cell 4's shared prefix. Three complete L0/L1 pairs remain valid partial measured evidence.

Within those three pairs, L1 produced one recurrent completion that L0 lost to context capacity, while the other two pairs tied on recurrent completion and hidden quality. All five trajectories that reached Phase C submitted and passed hidden grading.

This is strong corroboration of the narrow acquisition mechanism, but it is not a completed four-pair primary result.

## Observed outcomes

| Pair | L0 | L1 | Interpretation |
|---|---|---|---|
| IOTA / 173205 | Correct Phase-B patch/check and complete required reads; next `fork_ready` denied by 25k guard | Reached Phase C, selected current observation, hidden-pass, submitted | L1 removed two fragmented pages and preserved closure |
| IOTA / 223607 | Hidden-pass, submitted | Hidden-pass, submitted | L0 chose a 250-line page; no acquisition advantage remained |
| KAPPA / 173205 | Hidden-pass, submitted | Hidden-pass, submitted | L0 chose a 200-line page; no acquisition advantage remained |
| KAPPA / 223607 | Shared prefix interrupted before treatment | Not exposed | Missing primary pair |

Aggregate facts for the sealed partial run:

- 110 prepared invocations;
- 108 HTTP completions;
- 108/108 completed actions accepted;
- 14/14 model-visible checks passed;
- 14 complete stage runs replayed;
- 5/5 completed Phase-C candidates hidden-pass and submit;
- zero runtime token-accounting delta on every completion;
- zero retry, repair, or rescue.

## Economics

In pair 1, L0 used four bridge reads versus L1's two. L0's Phase B consumed nine completed calls and 61,592 prompt tokens, then lost the prospective `fork_ready` to capacity. L1 used eight Phase-B calls and 56,360 prompt tokens and reached the second boundary.

In pairs 2 and 3, L0 chose page sizes large enough to complete each bridge file in one call. Phase-B call counts were therefore identical at eight per condition, and prompt-token differences were only 26 tokens in each pair. L1's total branch cost was higher only because its Phase-C reasoning chose an additional wire-source confirmation read in both pairs.

The treatment's value is conditional rather than universal: it removes a failure mode when the actor fragments a required exact extent, but cannot save work that the actor would already transfer in one bounded read.

## Hypotheses supported by the transcripts

### H1 — Page fragmentation is causally capable of losing recurrent closure

Supported. Pair 1 held task, seed, prefix, candidate, evidence, and branch purpose constant. L0 split two 198-line files into four reads and could not admit `fork_ready`; L1 transferred them in two reads and completed Phase C.

### H2 — Maximal paging is neutral when actor-selected paging is already adequate

Supported in pairs 2 and 3. L0 selected 250 and 200 lines, respectively. Both conditions then had the same Phase-B call count and hidden-correct closure.

### H3 — Maximal paging does not solve confirmation policy

Supported. L1 made an extra two-line/wire confirmation read in two Phase-C paths. The host did not suppress or reuse those reads. Both were harmless but economically negative.

### H4 — Low bounded reasoning preserves semantics better than resource planning

Supported qualitatively. Qwen reliably tracked phase obligations and candidate-bound observations, but its chosen line counts varied from 100 to 250 despite exact P0 ranges and visible budgets.

## Decision

Experiment 011 does not receive a formal primary PASS/FAIL because the frozen schedule did not finish.

The narrow L1 mechanism remains **earned for operational use** based on:

1. the complete Experiment 010 result, where it removed all fragmented transfers and improved economics without harming quality; and
2. this partial recurrent evidence, where it converted one authentic 25k capacity stop into a hidden-correct recurrent completion and was quality-neutral in the other two observed pairs.

This decision does not claim a population effect, universal token savings, or a reliable recurrent controller. It says only that choosing the maximum mechanically fitting exact page is a defensible host responsibility and removes a demonstrated low-value actor decision.

The most important program-level finding remains unchanged: the controller's semantic continuity is working. Qwen selected current over stale evidence and made correct recurrent mutations in every reached Phase-C path. Reliability is now lost mainly through execution economics and lifecycle robustness.

## Next boundary

Do not resume or rerun this output under the consumed authorization.

Before any later GPU study, qualify a durable OS-owned execution lifecycle so a long run cannot be killed with its interactive command session. A future study may either:

- use fresh sibling cases for a pristine primary replication; or
- explicitly classify a same-bank run as post-exposure corrected replication.

Given the complete Experiment 010 result and the clear pair-1 mechanism here, repeating the same narrow question has lower research value than carrying L1 into the next genuinely broader recurrent task after lifecycle hardening. That next task still requires separate owner authorization; no automatic successor is created here.
