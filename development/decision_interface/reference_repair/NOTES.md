# Running implementation notes

R01: The inherited resolver covers designated selections and acquisition receipts,
but not the current recovery extents after refresh/merge. The successor derives
addresses with the same source renderer and consults actual last-delivered sources
for stale detection. It leaves edit delivery/current-version guards intact.

R02: The first new unit fixture omitted the required edit_checks argument. All four
new cases therefore errored before exercising production code. Preserve tests-001;
correct the fixture, not the production constructor. The other 52 selected checks
passed in that attempt. No model exposure occurred.

R03: Qualification-001 replays all thirteen unchanged replies and applies the actual
public correction, with all 72 target faults detected. Preparation-001 then catches
a checkpoint-adapter error: JSON converted integer diff keys to strings, preventing
the runner snapshot from naming the preserved diff. No completion was sent. Preserve
both sealed packages and the two original adapter sources under qualification-001-source.
Restore integer diff keys explicitly and repeat qualification/preparation in new
002 folders. This is an adapter repair, not a change to Qwen's task or source guards.
