# Independent readiness review of the small-repair prerequisites

22 September 2026. Read-only review of SPEC.md, repair_task.py, case_reports.py,
run_repairs.py, qualify_repairs.py, native_public.py, repair_qualification.py,
tests/test_readiness.py, the preserved prerequisite results and selected common
runner/observation code. No model, checker, vocabulary sampler or test was rerun.
The only new file from this review is this document.

No additional material implementation blocker was found. Full native input and
edit/check/submission preparation for each task remains pending; these prerequisites
are not permission to skip it and are not model task outcomes.

## Exact tasks and operating policy

The current TASK.txt and PUBLIC_CHECK.py files for all three original investigations
were byte-compared with their original preparation-001 copies: all match. The
recorded prerequisite original candidates match those historical preparations:

- Artifact map: `0f67505a0ad439530ae16095fac49db730b34ca253794657e06273420c2ba872`.
- Shift window: `b77c87956a3936ab169f80f5df55b4a2731b6015968fdebcb1e2a1095469c6ea`.
- Receipt corrections: `cb2c2d7e160c4c829b71ae1a033d34e1416224bfab84d57477857c94a731f349`.

The new session begins with no action history, selected sources or model account.
Its explicit episode annotation distinguishes the reported pre-session incident
from new work. The inspected native-005 artifact-map wire input contains that
annotation, the original task and an empty source group. The preparation script's
BAD/GOOD edit is used only after the initial input has been preserved, in the
separately identified offline reference route. It is not passed as task guidance.

Only public checking is supported. The declared policy requests a separate check
after an edit; there is no automatic edit check and no check_after reply field.
The reference explains this, the schema permits only the public scope, and the
preparation explicitly edits, then checks the observed successor, then submits.

## Projection and prerequisite custody

case_reports.py retains exact execution/capture metadata and raw access. When a
case summary appears complete but execution or capture did not complete, it keeps
the observed cases and adds an unmet public_execution criterion. A real outer
failure cannot become a pass because individual case rows passed. The inspected
tests cover timeout/capture-limit records, complete outer failure, pagination and
preservation of the single-observation checker's stdout. These are reviewed test
definitions and saved outcomes, not an independent test rerun.

The prerequisite gates validate status, declared outcomes, source closure, each
sealed output's size/hash and inventory identity. The native producer has no
status field in its seal; its separately sealed RESULTS.json supplies passed
status and the zero-inference/vocabulary-only declarations. Failed qualification
artifacts cannot satisfy the gate. Live source binding includes prerequisite seals
and their outputs, so preparation is not relying on an unbound historical “pass.”

I independently recomputed hashes against the current checkout:

| Prerequisite | Current source files | Sealed outputs | Differences |
|---|---:|---:|---:|
| checker-qualification-005 | 432 | 37 | 0 |
| native-005 | 398 | 29 | 0 |

The recomputed seal hashes are respectively
`eecedb4362fc4fac598a1da7d863f5efad33b682f6298a8c24b12f10dfd82fb2`
and `a735ff66814fc6705eafc619379eac24c10653b339553a021d816573671babc4`.

## Corrected native boundary evidence

The 004 unsupported-check_after case stopped at token index 27 because its patch
keys used an unsupported order. It does not demonstrate rejection specifically
of the extra field. Preserve it as that incomplete qualification.

In 005, explicit_patch.txt uses the actual accepted order. Its saved sampler result
accepts the complete reply including EOS. unsupported_check_after.txt contains
the identical complete operation and adds only the top-level check_after field;
its result rejects at token index 76 (token ID 13933, not EOS). The two saved texts
share all 296 characters before the positive reply's final outer brace, and their
parsed objects differ only by check_after. This paired positive/negative evidence
addresses the previous confound. I inspected the inputs/results and harness,
but did not independently tokenize the inputs or rerun the native sampler.

The recorded 17 native cases all match their expected outcomes. Completing the
remaining native preparation still needs to establish the actual rendered input,
token counts, complete feedback and guarded edit/check/submission sequence for
each of the three cases under the selected runtime.
