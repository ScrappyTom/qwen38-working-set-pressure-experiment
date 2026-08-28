# Experiment 004 attempt 1 results and decision

## Executive result

The attempt produced one clean matched observation-reacquisition pair and no
source-reacquisition pair.

Both reasoning-off and reasoning-enabled Qwen reopened the exact historical
observation, read the exact current source, produced a hidden-correct patch,
passed the public check, and submitted in five calls. Reasoning-on consulted the
governing observation one call earlier and emitted the exact known-good patch;
reasoning-off emitted a semantically equivalent patch. Reasoning-on did not
improve task success or call count and cost 1,674 additional completion tokens
and 88.172 additional seconds.

The prospectively claimed hard 512-token reasoning treatment was not actually
enforced. The measured evidence must therefore be labeled reasoning-enabled
with low effort and a 512-token *requested* budget, not bounded reasoning.

## Answer to the research question

This attempt does not show that bounded private reasoning is required for
evidence-to-action transition after an exact-context reset. On the one valid
pair, reasoning-off already performed the complete transition correctly.

It does show that private reasoning can make the model's information policy
more explicit. R1 stated the missing fact, chose the observation before source,
tracked closure, and used a formulation that preserved the prefix more exactly.
That is a qualitative process difference, not an earned outcome advantage.

The source branch remains unanswered because the common prefix, not either
treatment, exhausted its budget. No R0/R1 comparison may be inferred from that
cell.

## Project-level implication

The evidence continues to support the minimal architecture already earned by
Experiments 001-003:

```text
exact external custody
    + readable structural orientation
    + exact source/observation reopen
    + model-directed action
```

The observation pair is positive evidence that reasoning-off Qwen can use that
architecture after reconstruction. Turning on private reasoning was not needed
for this transition and imposed a large output/latency tax.

## Decision

Do not promote reasoning-on as a default feature. Do not spend a fresh measured
bank under the current configuration.

The only earned immediate follow-up is a development-only runtime-control check:

1. impose the 512-token budget at llama-server launch rather than relying on the
   ignored per-request field;
2. prove that reasoning-off remains off under the shared server;
3. prove that reasoning-on cannot exceed 512 private tokens;
4. use a mechanically constructed exact fork on already-exposed source material
   so the check isolates post-reset transition rather than live prefix policy;
5. preserve and directly audit the result, but do not call it a fresh primary
   measurement.

Only if that check reveals a meaningful source-reacquisition benefit should a
new fresh R0/R1 bank be considered. Otherwise, the higher-ROI program step is
to continue the main context-pressure work with reasoning off and improve
prefix/read economics separately.

Automatic successor work remains blocked by this decision record; the owner has
already authorized the development-only testing implied by “proceed as
recommended,” but no new measured actor exposure is inferred.

