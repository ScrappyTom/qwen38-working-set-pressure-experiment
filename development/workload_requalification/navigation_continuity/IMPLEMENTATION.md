# Navigation and immediate change projection: CPU readiness

22 September 2026. This implements the opt-in navigation and immediate-edit portions
of PLAN.md. No original attempt, shared host source, task, checker, action schema,
candidate, edit effect or acceptance rule was changed. Prospective accepted edit
results now also preserve the actual applied diff before archiving.

`navigation.py` exports `NavigationMixin`, `NavigationSession`,
`project_navigation`, `project_immediate_change`, `present_receipts` and
`REFERENCE_ADDITION`. A task adapter can use
`class Session(NavigationMixin, ExistingTaskSession)` so its existing task-specific
rendering and check assessment remain in effect. Its system reference must include
the addition. The convenience `NavigationSession` uses the existing coherent
diagnostic session. Neither class starts a runtime or executes a checker on import.

Accepted tree and p0 directory/outline results enrich only the existing six recent
rows. The projection retains the returned entries, scope, totals and continuation
coordinate. Outline entries gain only their exact matching archived source-region
reference. It does not infer a parent class, target, diagnosis or new region.
Search behavior remains unchanged.

Whole identical pages are shown once. A page fully present in latest feedback is
not repeated. This comparison includes returned region references, so a reduced
latest receipt cannot falsely suppress missing references. Original candidate
identity accompanies historical pages. An outline's file fingerprint is separately
compared with the current file; old directory statistics are never refreshed or
presented as a new observation. Navigation adds no delivered source or edit
authority.

Optional detail is bounded by 8,192 added UTF-8 JSON bytes and the existing complete
input admission callback. It yields complete pages, oldest first, before inherited
history reduction or recovery fallback. If omission labels themselves prevent
admission, the final fallback is the exact unextended view. Existing RES handles
remain in the rows; the permanent reference explains that a row without navigation
contains no result body. Large pages are omitted whole, never clipped internally.

The admitted rendering limit is saved as `navigation_projection_pages` inside the
existing `last` wrapper, copied before mutation. It is absent from displayed
feedback and exact archived pairs. Existing snapshot/restore of `last` therefore
preserves the admitted view without a new checkpoint field. A subsequent operation
creates a fresh wrapper and retries the full optional allowance. Omission labels
say `input_admission_budget`: admission can concern the preferred input margin,
not only the physical input ceiling.

## Immediate applied change

After an accepted patch or literal region replacement, `_patch` adds the exact
already-computed diff to `result.applied_diff` before `_record` archives that result.
The original action stays separate. In particular, a literal proposal missing its
boundary newline remains exactly that proposal in EVT, while the applied diff and
the recorded `supplied_boundary_separator` describe the actual saved file. A
rejected edit has no applied diff. Existing RES paging exposes the new exact field;
no new tool or recovery handle is introduced.

The decision view removes the raw result field and supplies
`latest_feedback.applied_change`. It contains a complete diff and its exact RES
field address when possible. Its separate 8,192-byte optional rendering allowance
includes metadata; large diffs are omitted whole. Full input admission tries all
navigation reductions before removing this immediate diff, then tries the omission
metadata, then the exact earlier receipt shape. The permanent reference explicitly
states that absent detail is not visible and where the prospective exact result
can be retrieved. Thus even an omission label cannot block an edit that otherwise
fits. These are presentation choices; archived result and candidate remain exact.

`immediate_change_detail_mode` persists beside the navigation setting in the
existing last wrapper: 2 permits complete detail, 1 shows only omission metadata,
0 removes all optional change detail. Both internal settings are hidden from the
model-facing receipt. Diff text grants neither exact-source eligibility nor check
applicability. It describes an observed change, not its intent or correctness.

The two class flags `navigation_enabled` and `immediate_change_enabled` support
separate native qualification axes. `historical_diff_projection` defaults false.
Only explicitly labeled old-state qualification may enable it to project a saved
snapshot diff absent from the original RES. It then states that absence and supplies
no fabricated RES recovery address. The C19 counterfactual does not rewrite history.

The task adapter uses `present_receipts` to remove raw applied-diff fields and
internal presentation settings from preceding receipts. This package has explicit
checks, never an accepted edit followed by an automatic check in the same response.
The helper prevents an accidental large-diff leak if supplied such a receipt, but
does not qualify a combined edit/check detail policy. That remains outside this
configuration.

## Evidence and limits

`TESTS-006.log` records twenty-three passing CPU checks. Fourteen inspect exact source-bound
C04-C10 and C16 wire inputs and checkpoints, deduplication, unchanged search and
archive bytes, stale and unchanged-file references, edit authority, complete feedback
priority, a rejection followed by selection replacement, checkpoint behavior,
100-versus-10,000 archived pages, and whole-page omission under a synthetic oversized
signature. The artificial size stress is not an accepted model operation. Nine
additional tests exercise ordinary and literal edits, original proposal versus
separator handling, actual RES recovery of a large omitted diff, rejected edits,
priority/fallback, no new source/check authority, the safe preceding-receipt helper,
and the exact C19 historical counterfactual. These use real CPU host operations,
not model-selected actions.

`cpu-qualification-002/` saves all eight original and projected navigation views,
record-bound source identities, imported source-code identities and output hashes.
It adds 1,621-3,323 JSON bytes across these states (C16: 2,422). These are byte
measurements, not native token counts. Removing the new navigation fields reproduces
each exact original view. Every archived pair remains unchanged. C19 additionally
has separate change-only and combined counterfactual views: 884 and 2,444 added
JSON bytes respectively. Its exact diff comes from the recorded checkpoint and
is explicitly absent from the unchanged original RES. `cpu-qualification-001/`
remains the earlier navigation-only qualification against its recorded source;
its old source identities are historical, not a current-source gate.

No model request, native render/tokenization or checker execution occurred. The CPU
capacity tests use deliberately defined measurement callbacks to exercise the real
admission/transition code; they do not establish native input fit. The projection
has no semantic ranking, persistent automatic navigation collection, or guarantee
that the actor will use a location correctly. Facts expire with the existing recent
window unless the actor selects their saved result. C09 remains a counterexample to
any claim that absent navigation alone caused repeated acquisition.

Before exposure, the parent task must integrate the reference, qualify native
complete-input cost and real checked-work/control transitions, inspect actual
rendered prompts, and freeze the prospective package. Native qualification should
measure navigation and change detail separately and together, including zero-added-
detail admission and actual checked work. No behavioral benefit has been measured.

## Running development notes

1. `TESTS-001.log` retains two failed test assumptions. One compared displayed
   feedback with the internal last wrapper, which deliberately also carries the
   hidden admission setting. The other assumed an empty directory query is rejected;
   the host legitimately returns an empty listing. Tests now compare displayed
   feedback and use a noncanonical parent path for deliberate rejection. Production
   behavior was not changed to satisfy either mistaken assumption.
2. `TESTS-002.log` records thirteen passing tests after those fixture corrections.
3. A source review tightened latest-feedback deduplication to require the returned
   kind and region references as well as entries/pagination. A fourteenth test
   removes references from an otherwise matching latest outline and verifies that
   the projection still supplies the archived references. `TESTS-003.log` passes.
4. The admission setting belongs to presentation, not an archived result. Keeping
   it outside `pairs` prevents a fit decision from changing the observation it is
   supposed to present. This distinction should survive later governance updates.
5. The C19 addendum earned preservation of the actual applied diff in prospective
   RES records. The earlier EVT route contains the proposal, not a guaranteed
   applied diff. Tests and old-state projections preserve that difference.
6. `TESTS-004.log` records all fourteen navigation checks after the extension;
   `TESTS-005.log` and `TESTS-006.log` record twenty-three passing checks with change
   qualification. No further failures were discarded. The last run followed the
   updated CPU qualification script and current combined source seal.
7. Projection source was handed to the native qualifier at SHA256
   `e6cb976f54f47d45d9b165e229d74250600d78dc8af9a3b65eaa049c6f7707f8`.
   Capacity omission wording was corrected before freeze to avoid calling a
   preferred-margin restriction a hard-ceiling failure.
