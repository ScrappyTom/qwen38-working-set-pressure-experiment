# Shift-window baseline: evaluator-only source audit

22 September 2026. Read the exact original task, all nine candidate files, fixture
construction, complete public checker, original specification and historical
reviews. Also inspected the historical emitted patch, final source, saved complete
public result and submission. No checker, model, native runtime or task operation
was executed. This document is evaluator material outside the runtime source closure
and must not be supplied to the actor as diagnosis, reading list or repair guidance.

## Contract and invariant

The task reports a confirmed overnight shift missing from the following day's
hours report. It asks for repair of daily reporting, counting only time inside the
requested local day, combining employee contributions, and preserving offset
handling, void exclusion and invalid-input rejection. It requires exact current
source before editing, a public check on the final candidate and submission.

The README adds precise existing contracts: fixed offsets rather than machine
timezone or named-zone daylight-saving rules; midnight-inclusive/next-midnight-exclusive
day boundaries; fractional minutes; additive overlapping rows; no employee key when
that employee contributes no time. Each valid CSV row is a separate shift.

For each employee `e`, the intended total is the sum, over confirmed rows for `e`, of

`max(0, (min(shift.end, window.end) - max(shift.start, window.start)).total_seconds() / 60)`.

Only positive intersections enter the mapping. The interval expression is over
aware instants: importer normalization to UTC and the requested fixed-offset day
refer to the same absolute timeline. The formula is a source-derived correctness
argument, not a newly executed oracle or additional acceptance criterion.

The public call path is `daily_minutes` -> `read_shifts`, `day_window`, then
`report_minutes`. The importer checks exact CSV fields, complete rows, employee/status,
aware instants and positive duration; it normalizes instants to UTC. `day_window`
constructs the requested calendar date at the explicitly supplied fixed offset.
The `Shift.duration_minutes` property describes the full shift, not its intersection
with a reporting day. `DayWindow.contains` explicitly means full containment.

Sources: [TASK](../../../shift_investigation/TASK.txt),
[README](../../../shift_investigation/source/README.md),
[api](../../../shift_investigation/source/src/shiftledger/api.py),
[importing](../../../shift_investigation/source/src/shiftledger/importing.py),
[windows](../../../shift_investigation/source/src/shiftledger/windows.py),
[model](../../../shift_investigation/source/src/shiftledger/model.py),
[reporting](../../../shift_investigation/source/src/shiftledger/reporting/daily.py).

## Defect and sufficient repair

The reporting loop first excludes nonconfirmed shifts, then excludes every shift
not wholly inside the day using `window.contains`, and adds the full duration of
each remaining shift. The first condition loses partial overlaps. Merely replacing
containment with an overlap predicate admits those rows but still overcounts time
outside the day. A valid repair must handle both eligibility and clipped duration.

For the supplied overnight example, 23:30-01:30 at +02:00 must contribute 30 minutes
to the preceding day and 90 to the reported day. A shift covering both day boundaries
contributes exactly 1,440 minutes. Merely touching either boundary contributes no
time and creates no zero-valued employee entry.

The fixture's BAD/PARTIAL/GOOD strings make the two defects explicit for engineering
qualification. They are evaluator artifacts. The future model need not emit the
reference bytes or use that exact implementation; assess the saved behavior and
preservation. Changing the documented full-containment meaning of `contains` is not
necessary and would deserve independent review even if the public report passed.

## Public acceptance coverage and limits

The [exact public checker](../../../shift_investigation/PUBLIC_CHECK.py) contains
24 behavioral cases with literal expected results, not reference-candidate comparisons:

- Five acquisition/window checks: decoded count, employee/status, UTC start, UTC end,
  and report-window UTC endpoints.
- Fourteen report checks: overnight, preceding/following day, both-boundary span,
  ordinary shift, touching boundaries, exact full day, mixed employees, additive
  overlaps, void exclusion, fractional minutes, equivalent UTC input, negative
  reporting offset and empty input.
- Five rejection checks: naive timestamps, reversed duration, empty duration,
  unknown status and empty employee.

Mappings require the expected keys and numerically close values (`math.isclose`,
absolute tolerance 1e-9 plus its default relative tolerance). Final success requires
no failed case and exit zero. Five decoding/window observations can distinguish a
parsing/window explanation from reporting logic; they do not supply a patch. This
is informative public evidence, not hidden grading or a novel-discovery task.

Coverage is finite. It does not directly test every malformed CSV form, invalid
date/offset syntax, whitespace normalization, extreme datetime/offset values,
arbitrary streams, microsecond arithmetic, returned dictionary order, or standalone
`DayWindow.contains` compatibility. It does not check documentation changes or
require a particular code diff. Its five rejection cases are not a proof of all
invalid-input rejection. If the actor changes the importer, window construction or
other files, source review must examine that additional scope rather than infer
preservation from the 24 passing cases.

Some imports, decoding/window setup and invalid-input calls are outside the report
helper's exception handler. An unexpected exception there can end execution with
only a partial case stream. The current assessment must retain incomplete execution
as such, rather than infer a full pass from the cases printed before termination.

## Saved contribution assessment

The independent final audit should establish:

1. The saved source implements positive interval overlap and clipping, preserves
   confirmed-only selection, sums rather than overwrites repeated employees, retains
   fractional minutes and excludes zero/nonoverlapping contributions.
2. Existing offset/UTC interpretation and validation remain intact. Review all changed
   files against original bytes. Preserve the prior sorted mapping behavior unless
   a justified alternative still meets the task; checker key comparison alone does
   not enforce ordering.
3. An actual complete public execution applies to the final candidate and unchanged
   checker. Submission names that same candidate. Saving a patch or seeing a host
   eligibility flag is not independent evidence that the model chose/usefully
   interpreted verification.
4. Each action is interpreted against the actual source, navigation, account and
   feedback that reached that call. Credit legitimate new acquisition; distinguish
   lost discovered locations from repeated navigation while locations remain visible.
   Applied-change feedback describes the saved diff, not proof of correctness or a
   retained rationale. Reopening historical results is not a new check.

Do not require an initial failed check, wrong repair, account update, externalization
or prescribed reading sequence. A direct correct source-led repair counts. If no
pressure or recovery occurs, leave those claims untested.

## Historical evidence and current identity

The source fixture has nine files and 5,019 bytes. Original candidate:
`b77c87956a3936ab169f80f5df55b4a2731b6015968fdebcb1e2a1095469c6ea`.
Task SHA256: `684983575d7af64c5ea6717ba33a280cb245a9a2fe42e76c6876bfc9643fb527`.
Public checker SHA256: `0624eca3c49b91efabfcb8b5c0e888de8d2cf7ffd2dbca212c525d5814bba060`.
Original reporting-file SHA256:
`10a29a0b918482b736d5012dc6e333b9bdbd2b9f5ae32ff7977de2b83b47b450`.

The original S01 saved a correct overlap patch, then explicitly checked and submitted
candidate `b05e48a5080daa02f4a2dcc57b8b6de6287370048237033a24382c8a9d165606`.
Directly inspected saved stdout contains all 24 passing cases, final passed status,
exit zero and no stream truncation. This review did not rerun it or independently
reverify its entire custody seal. The prior complete audit reports eleven actions,
606.263 model-request seconds, no failed check/rejected action and no pressure boundary.

That run used the earlier xhigh policy, seed 161803, 20-action allowance and resident
event presentation. The prospective regression uses medium, seed 961221, 24 requests/
72 operations, revised bounded presentation and enforced current checked submission.
The same task/candidate/checker does not make this a controlled navigation-only or
latency comparison. A current-host pass will close this corpus entry, not establish
general investigation or sustained pressure continuity.

Historical evidence: [emitted patch](../../../shift_investigation/run-001/calls/S01-009-assistant-content.txt),
[actual check](../../../shift_investigation/run-001/calls/S01-010-host-result.json),
[final candidate](../../../shift_investigation/run-001/calls/S01-011-candidate-after.json),
[historical results](../../../shift_investigation/review/RESULTS.md).
