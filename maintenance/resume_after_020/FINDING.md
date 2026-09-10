# Prospective maintenance after Experiment 020

The owner directed proceeding with the resume plan and explicitly required
transcript review for host issues and friction visible in thinking and model
responses. This maintenance preserves the completed experiments. Its mechanical
reanalysis is in [REANALYSIS.json](REANALYSIS.json); the original September 9
assessment remains [the project review](../../PROJECT_REVIEW_2026-09-09.md).

## Measurement repairs

`inspection_status` now checks continuous source coverage against the exact
pre-mutation candidate and file bytes. It does not combine reads from different
versions or credit incorrect content. Adjacent and overlapping ranges may
jointly complete a file, regardless of read order. An empty read beyond EOF
does not establish completeness or erase existing coverage. Reading an actual
empty file at line 1 does count. The first accepted mutation ends the audit
window; rejected edits do not. An individual page's `complete` flag remains a
page-to-EOF indication, distinct from whole-file coverage. This changes the
audit and its callers, not tool behavior or model-facing reading policy.

The new correction-opportunity measurement records remaining calls before and
after each attempted check, identifies the first check, and distinguishes a
failed check from a rejected operation. It reports whether the action allowance
can accommodate check/patch/recheck/submit before a check and patch/recheck/submit
after a failure. These numbers do not establish physical context admission or
that the host offered another request. The action budget and stopping policy
are unchanged. New execution summaries use this measurement; historical
summaries remain unchanged.

The obsolete test asserting that E020 authorization is absent now validates
the saved authorization's exact schedule and qualification bindings alongside
the consumed run's response seal. Historical authorization is not permission
to repeat that run. README navigation distinguishes old preparation milestones
from completed execution and the current development work.

## Historical reanalysis

The new script verified all 1,625 sealed files, all 12 record chains, and final
response/reasoning custody for all 106 actual completions. It reconstructed all
eight terminal candidates and replayed the unchanged frozen hidden graders:
**8/8 still pass**. An independently implemented per-line bitmap agreed with
the repaired interval audit for all required files in all eight branches:
**no missing source lines before the first accepted edit**.

| Cell | R50 calls remaining at first check | X25 calls remaining at first check |
|---|---:|---:|
| 1 | 7 | 7 |
| 2 | 8 | 3 |
| 3 | 11 | 8 |
| 4 | 11 | 7 |

The count includes the imminent check. Cell 2 X25 therefore had only two calls
after its passing check; the full four-action correction cycle was no longer
available. All eight first checks passed, so there are no historical failed
check examples for the new after-failure field. Focused tests cover that case.

The independently specified [additional import probe](import_boundary_probe.py)
tests file limits 0, 1, 2, and 10 against inclusive byte limits 0, 1, and 5,
including excluded paths and an unsupported extension. Both R50 source repairs
and the donor pass 9/12 cases, failing the three zero-file-limit cases. Both X25
source repairs pass 12/12. This separately identified post-hoc finding preserves
the original scores and supports no general condition advantage. No donor or
submitted artifact was repaired to improve its score.

The mechanical reanalysis is not a claim to have newly read all historical
transcripts directly. The targeted interpretation below was checked against its
actual request, reasoning, action, and result; the original exhaustive E020
audits remain the broader interpretive record.

## Host and interface review requirement

[AGENTS.md](../../AGENTS.md) and
[analysis governance](../../docs/ANALYSIS_GOVERNANCE.md) now require direct
transcript review for host defects and interaction friction throughout a run,
including successful and recovered paths. Review prompts, separate thinking,
final responses/actions, tool results, relevant source/artifact/custody evidence,
and the next host decision together. Aggregate diagnostics, generated excerpts,
and script completion cannot substitute for this review.

The existing call-3 example illustrates why: the old actor claimed external
result bodies were absent although their presence flags were true; adjacent
action-payload records had the false flags. It also misstated completed reading.
The next action retrieved valid useful evidence, and the next turn recognized
that all eleven reads were complete. This demonstrates recovered interpretation
friction. It does not establish that the retrieval was wasted or that the host
lost the evidence. The new governance explicitly preserves these distinctions.

## Development handoff and validation

The [bounded Qwen consultation](../../development/qwen_interface_consultation/SPEC.md)
completed its sole 16-response attempt on four actual interface states. It uses the
owner's IQ3_XXS actor, q8_0 K/V, 32,768 context, no MTP, and uncapped native
xhigh thinking. The full crowded saved request is retained with only the
reasoning allowance updated. The remaining states are independently rebuilt
through actual tools. All ordinary next actions precede the separate diagnostic
questions. Design solicitation and any interface alternative remain subsequent
development work; this package gives Qwen no preferred replacement.

All 16 responses finished normally; all eight ordinary actions were accepted
and independently replayed. The [completed results](../../development/qwen_interface_consultation/RESULTS.md)
and full direct transcript/host-path audits distinguish correct core decisions
from argument guessing, resource wording interpreted as policy, and ambiguity
about field-payload sizes versus full saved results. All prompts, thinking,
final outputs, actual tool results, and host decisions have been directly
reviewed. The 178 sealed files and 66 chained records verify.

The [four-request design consultation](../../development/qwen_interface_consultation/FOLLOW_ON_PROPOSAL.md)
is prepared and has made zero completion calls. It will solicit Qwen's preferred
metadata/tool presentation after supplying actual implementation facts, then
support selection of at most one variant for a matched comparison. No refactor
has been adopted. The crowded diagnostics left 582 and 892 physical tokens;
sampled GPU memory reached 316 MiB free. Qualify capacity and generation room
before that follow-on, retaining the owner's q4/approximately 55k option.

Validation completed before exposure: 37 selected maintenance/current-E020/core
tests passed, followed by five interface-state and request-isolation tests.
This was Python unittest plus explicit execution of the six plain E020 test
functions, not a claim of a full pytest run. The native runtime additionally
prepared all 16 prompts, with a maximum of 18,732 input tokens and at least
8,192 physical tokens available for development generation. The admission margin is
not an output cap or the eventual pressure comparison's frozen reserve.

Reproduce the separate measurement addendum with Python 3.12 and `src` on
`PYTHONPATH`:

```powershell
py -3.12 -B -X utf8 scripts/reanalyze_020_measurement.py --output <new-analysis-file.json>
```

The command refuses an existing output path. Reproduce historical executable
closures from their original pinned commit; do not regenerate old receipts
against this changed checkout. Analysis code hashes and the prior Git base are
recorded in the addendum.

## Fresh investigation feasibility

The separate [offline geometry probe](INVESTIGATION_GEOMETRY.json) constructs a
new fault in the donor's `apply_patch_preview`: it returns the old address map
after successfully producing updated content. The actual reopen path then
reports a content-hash mismatch. Independently building the correct map and
extracting the changed function succeeds, distinguishing an update-propagation
problem from incorrect section extraction. The unchanged implementation also
preserves the displaced neighboring function, rejects the old changed-unit
reference, supports a second update, and handles unchanged content.

This is a deliberately injected task candidate, not a newly discovered
production defect. It does not reuse the previous extraction, truncation,
import-boundary, or verifier faults. No operating model has seen this task.
The probe establishes a reproducible failure and behavioral distinctions;
it does **not** establish a natural context-pressure opportunity. A short
correct investigation may finish early. Do not freeze the substantive study
until a credible investigation path and action/generation allowance are
qualified; use a different task if necessary rather than adding inert padding
or a mandatory reading list.
