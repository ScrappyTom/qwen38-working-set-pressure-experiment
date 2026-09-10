# Analysis governance

Exact custody is infrastructure for interpretation, not a result.

After any model-exposed run, preserve five separate products:

1. execution receipt: identities, hashes, counts, replay, and lifecycle;
2. host-path audit: host decisions and interface behavior throughout the run,
   including successful and recovered paths, with the exact input/output and
   following host decision for every defect, friction finding, or stop/failure;
   include whether another call was actually offered;
3. apparatus finding: validity and contamination boundaries;
4. direct transcript audit: every prompt, raw output, action, result, candidate,
   observation, check, and terminal state;
5. results decision: paired C50/T25 synthesis against the research question.

Never infer model failure from a terminal label alone. Classify each path as
model-chosen, model-budget-exhausted, host-withheld, mechanically capacity-
denied, protocol/transport-failed, checker-failed, operator-interrupted, or
completed. If the host did not send the next request, the model did not fail to
answer it.

The audit must state actor, quantization, reasoning mode, sampler, seed,
context/output bounds, exact fork identity, occupancy, and runtime accounting.
For each fork it must identify what the model knew before the boundary, what
left active context, what T25 reacquired, what it failed to reacquire, and how
that affected mutation and closure. Dynamic observations count as information.

The owner may receive a concise executive summary only after the complete
analysis is saved as Markdown.

An interrupted or formally unscorable run does not waive direct review.
Preserve and audit every completed call whose custody remains valid, then state
separately which behavioral/component claims survive and which paired or
promotion claims do not. Infrastructure or operator failure must not erase
earlier valid acquisition, mutation, evidence-selection, or reasoning behavior;
nor may that behavior be promoted beyond the surviving evidence boundary.

Live monitoring must follow global run progress and the current hash-chained
record/receipt state. A file count scoped to one cell or branch is not a valid
liveness signal after the runner may have advanced. Operator intervention must
record the exact active prepared invocation and produces an immutable partial
run; exposed cells are never silently resumed or replaced.

For reasoning-enabled conditions, inspect the exact private reasoning field and
the final action separately. Report whether the reasoning identified the
governing fact, mutation target, exact patch, check, and stopping condition;
then report whether the external actions actually followed that plan. Do not
credit reasoning content that never changes or supports observable behavior.

Direct review must actively look for host issues and interaction friction,
including issues visible in thinking or the model's response that a passing
final result would conceal. Compare interpretations of metadata, tool effects,
visibility, completed work, and candidate/check validity with the exact state
actually supplied. Trace the resulting action, tool result, host decision, and
later recovery or cost. Inspect relevant source, artifact, and custody records
before attributing a mismatch to the model or host. A correctly implemented
interface can still impose avoidable interpretation or interaction costs.

For each finding, state what the model saw, what its thinking and final
response indicate separately, what the host actually did, the observed
consequence, and any uncertainty. Distinguish absent-evidence recovery,
confirmation after mutation, misplaced acquisition, and redundant work.
Do not count a useful retrieval as waste merely because the model also
misstated a field. Neither a passing grade nor eventual recovery waives this
review, and a rationale alone does not establish causal use or a host defect.
Record findings in the existing audits and carry actionable or deferred
interface suggestions into the results decision. Generated excerpts, counters,
and custody checks assist review; running a script cannot certify that a human
or reviewing agent directly read the transcripts.

When the causal reason for an action remains unclear after exact prompt,
reasoning, response, and host-path review, specify a fresh diagnostic with
reasoning enabled. Do not rerun an exposed measured cell merely to obtain an
explanation, and do not change reasoning mode inside a sealed comparison.

Any host defect that affected an outcome must be fixed and mechanically/live
qualified before fresh measurement. Historical evidence remains immutable and
is reclassified rather than rewritten. Results must include a compact table of
`what Qwen saw -> what Qwen did -> what the host did next -> interpretation`,
followed by explicit falsifiable hypotheses for the next study.
