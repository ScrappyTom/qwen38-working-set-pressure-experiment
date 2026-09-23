# Runner boundary inventory in progress

Read-only source review during the frozen search-continuity run; no active code
or policy changed. This supplements PLAN.md and is not an implemented optimization.

The active chain is search_continuity/run_search.py -> diagnostic_continuity/
run_continuity.py -> action_lifecycle/run_continuation.py -> an isolated import of
scripts/run_uncoached_contribution.py -> run_bounded_parser.Loop. The continuation
subclass changes cumulative counters and first-input qualification, not sizing.

The inherited measure() constructs request bytes, returns cached measurements by
exact request digest, and otherwise runs source_check plus runtime health before
native rendering/tokenization. The contribution subclass additionally preserves
exact wire bytes. Its invoke() verifies all bound sources immediately before model
dispatch and again after the completed response, before decoding/executing it.
process_reply() can invoke measure repeatedly for candidate pages and transitions;
the final resulting view is measured again. The controller also verifies sources
at normal final closure. These are separate boundaries, not just one initial check.

Known dynamic input reads: Adapter.request_for reads SYSTEM.txt on each construction;
operating_reference and response_constraints are task callbacks. Task initialization
reads exact historical candidates, state, task/checker definitions and preserved
observations. Candidate/selected-source execution thereafter uses session objects;
that alone is not a complete audit of all dynamic reads. Before implementing the
plan, trace callback/template/observation reads and failure closure as well.

A batched arrangement must not merely replace source_check with a no-op: invoke
uses the same callback for the critical dispatch/execution boundaries. It needs
explicit, separately tested sizing boundaries, with exact bytes unchanged and full
validation before any model exposure or accepted operation. A change detected after
an actual check must preserve its executed observation and saved edit, even if later
presentation or integrity qualification fails. Detection timing is a declared policy
change. No neutral-optimization claim follows just from identical happy-path inputs.

This inventory is incomplete by design and authorizes no weaker checks in an active
run. Historical evidence, current implementation and private runtime identities all
remain in their existing verification closure until a successor is qualified.

## Continuation measurement boundary

The transport closure reuses check_opportunities over all this-task pairs with its
new38-operation cap,so inherited check rows receive different opportunity arithmetic
than their original72-operation run. The field already says action allowance only,
but does not preserve per-event caps or model-request constraints. Exact wire records
retain those facts. A future reporting repair should derive historical opportunity
from each actual input and reply contract,or clearly restrict the old metric to its
current-cap counterfactual. Do not rewrite closed records or mistake this for a
checker/execution defect. The reviewer also assumed a combined reply that the current
interface lacks; that independent mistake is preserved in the search transcript audit.
