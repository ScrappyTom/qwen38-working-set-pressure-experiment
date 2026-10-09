# In-task observation entry implementation

The new code reuses the current phase session, source/selection/recovery/account
operations, captured checks, controller, native matcher and exact replay core.
It adds no general memory store. OBS identities are derived aliases of accepted
check/probe/fork results in the same ordered archive. Failed executed checks count;
rejected requests do not. A directory page contains at most six identities, and
ordinary RES storage preserves the complete body separately from that inventory.

The integrity fixture is produced only by an actual requested Phase A operation.
Its receipt states authored_fixture_output, actual candidate, exact fixture text
and execution status. It is not an imported incident or external observation.
Reopening resolves the original result and retains those exact bytes through the
existing selected-result mechanism; the complete ordinary view must fit. Recovery
mode can still omit designated bodies explicitly. It does not invent a current
check or source-edit authority. An edit never rebinds an old observation.

The strengthened fork guard is declared: current-candidate integrity, not the old
probe_done boolean. The original check/fork/source-release/shared-opportunity
contract otherwise remains. No automatic probe, semantic choice or task answer
is supplied. The candidate binding remains inspectable after later changes.

The adapter writes diff-map keys as JSON strings before serialization. This fixes
the source entry's round-trip ordering problem at its actual persistence boundary.
Every new scripted checkpoint is restored from serialized state/candidate bytes
and compared with its original view and full exact observation aliases.

CPU-TESTS-001 preserves nine passes and one failed qualification assertion. The
result was present in latest_feedback, deduplicated out of working_set.saved_results.
The assertion incorrectly demanded the latter location. The corrected assertion
checks both actual presentation locations and exact content; no host change was
made to satisfy it. CPU-TESTS-002 passes all ten checks, including the complete
public-reply journey, differing-width edit sequences, stale/current probe, failed
check identity, directory paging, invalid recovery, alias separation across branches,
phase release, exact recovery and preservation on capacity rejection.

Native preparation001 exercises48decoder specimens and26scripted decisions (19
complete route,7crowded recovery), with zero completion requests. Initial input is
6,670tokens. Full rendered initial system/user messages were read directly: fresh
candidate, original assignment, empty account/selection/history/observations,32/96
allowance and no marker or solution. Actual recovered-result and source-group
views were also inspected; their contents support the next scripted correction.
These routes are engineering qualification, not Qwen selection or performance.

The post-run evaluator lives under review/post_run, outside the frozen actor-source
closure, and records its own hash. It waits for full replay, then checks original
phase procedures and independent saved behavior. Alternative exact recovery paths
still require direct review. No result is graded from a passed check alone.
