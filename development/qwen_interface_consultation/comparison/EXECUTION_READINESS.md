# Execution readiness — September 10, 2026

The owner explicitly authorized the sixteen prepared requests after safeguards
pass. The [execution specification](EXECUTION_SPEC.md) records that instruction
and the pair-level interpretation refinements from the owner-supplied review.
It changes no model input, reference text, output grammar, candidate state or
runtime setting. The review is not itself new model evidence.

The separate `scripts/run_interface_comparison.py` reuses the frozen native
runtime, strict action, executor and custody helpers. It verifies the pinned
preparation seal and source closure, natively checks all sixteen requests before
dispatch, and reconstructs exact original candidate/session state independently
for each response. Every raw endpoint reply enters custody before parsing;
separate thinking/final text enters custody before completion/accounting checks
or action execution. Each returned action is executed at most once. Actual
after-state is preserved even if an unexpected executor exception occurs.

Protocol, native/accounting, runtime or telemetry failure stops dispatch. Failed
checks and normally returned tool rejections remain observed outcomes. A fixed
run-001 directory prevents restart/resume; both stopped and completed runs are
sealed, including partial transport bodies and lifecycle/memory evidence.
The 350 MiB reference stays advisory and thinking stays uncapped. No additional
live qualification or design response is added to the sixteen-call scope.

Validation completed before freezing:

`py -3.12 -B -X utf8 -m unittest discover -s tests -p 'test_interface*.py' -v`

**33 tests passed**, including eight new execution tests for manifest/configuration
and schedule mismatch, native mismatch before any completion, exact response
preservation before one action, state isolation, legitimate failed checks and
stale-guard rejection, incomplete/malformed/cache/channel/accounting/telemetry
stops, unexpected mutation before an executor failure, and sealed transport
failure without retry. The tests use explicit runtime/endpoint doubles; they are
not model completions or a full-suite claim. Prior raw endpoint replies were
directly inspected to confirm the pinned response accounting/channel fields.

The existing preparation review already directly inspected the actual native
system/reference placement and established exact identity of the four full
source states and all paired message bodies. The execution path repeats native
render/hash/count checks instead of altering or padding those messages. Complete
post-seal thinking/action/result review and independent replay remain necessary
before any performance or presentation decision.
