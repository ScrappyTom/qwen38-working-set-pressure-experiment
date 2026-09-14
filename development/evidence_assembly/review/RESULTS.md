# Evidence assembly: better partial tests, no completed contribution

The authorized pair is closed. Supplying implementation evidence improves the
grounding of some proposed and saved tests, but neither condition completes the
test/documentation contribution. The assembled condition costs more generation
and time. Its initially sound test proposal is rejected at the actual input limit;
after narrowing the group, Qwen releases supporting code, reconstructs its work,
and eventually saves weaker tests. This is evidence about maintaining usable work
and evidence across decisions, not a successful automatic-selection system.

## Actual outcomes and cost

| Measure | Broad initial group | Assembled initial group |
| --- | ---: | ---: |
| New model requests / operations | 8 / 9 | 8 / 9 |
| New test methods saved | 13 | 18 |
| Edited suite | 372 tests; 3 errors; 5 skips | 377 tests; no failures/errors; 5 skips |
| New documentation | None | None |
| Diagnostic assertions | Reference substrings only; preceded by failing rawval access | None |
| Overall actor-requested check | Failed | Failed |
| Submission | None | None |
| Correction requests after first check | 0 | 0 |
| Input tokens, cumulative | 138,318 | 115,800 |
| Generated tokens, thinking + final | 37,570 | 70,796 |
| Model-request time, minutes | 42.502 | 73.098 |
| Task-loop time, minutes | 42.898 | 73.730 |
| Peak sent input | 23,439 | 22,782 |
| Peak input + generation | 36,916 | 37,070 |
| Sampled minimum free GPU memory | 140 MiB | 142 MiB |

Both preserve the library and every prior contribution. Broad's saved tests invent
an error.rawval attribute and produce three actual errors. Assembled's saved tests
correctly assert the four-element args tuple and exercise real Basic/Extended
lookups, including cross-section transport through copy/deepcopy/all pickle protocols.
They detect all four restoration mutants against a passing baseline. They still
omit the required diagnostic-text assertions and documentation. Passing individual
test methods is not completion of the requested contribution.

The assembled package reduces cumulative input 16.3%, while increasing generation
88.4% and model-request time 72.0%. These are descriptive differences from one pair,
not reliable effect estimates. The two loops total 116.629 minutes and 108,366
generated tokens. Task-loop time excludes preparation, runtime startup, post-run
assessment and reviewer labor; no total-project productivity improvement is claimed.
The final assembled response alone generates 30,658 tokens in about thirty minutes.
All outputs fit the prospective reserve in this pair; no physical exhaustion occurs.

Machine-readable accounting is in [broad](METRICS-broad.json) and
[assembled](METRICS-assembled.json). See [artifact assessment](ARTIFACT_ASSESSMENT.md)
for the actual additions and qualification of the checker results.

## What the actual turn inputs explain

The initial assembled input contains the real exception constructor, the base
Error formatter, interpolation raise paths, parser configuration/get behavior,
test examples and editable regions. Broad has large test/documentation pages but
never obtains the exception implementation. Its final response repeatedly invents
that implementation and saves the nonexistent rawval assertion. Assembled correctly
uses the supplied tuple and formatter in its first complete test proposal, C04.

This first proposal is not accepted: its refreshed group plus actual edit receipt
requires 25,457 tokens, 1,649 above the declared ceiling. No mutation is committed.
The rejection and exact proposed action are preserved, and the complete rejection
enters C05. The host does not falsely reject a fitting input in this case.

Qwen then replaces its broad accumulated group with the exception constructor and
test/documentation insertion points. The next input falls to 4,362 tokens, but the
replacement releases the base Error class, interpolation/get code, imports and
examples. The rejected proposal remains archived and is not selected. Qwen rereads
the now-absent imports, then guesses a library range that fails to reach the raise
sites it wants. Its earlier plan and private drafts are not carried forward either.
The small input is now affordable, but no longer expresses the same working situation.

C08 gives a particularly concrete consequence. It initially drafts correct full
diagnostic assertions. Later it assumes that the absent Error class has no initializer
or str override, concludes that the formatted message is lost, and removes those
assertions from the actual final patch. The real eleven-line excerpt, present until
C05's replacement, stores message and makes str return it. Missing source and an
unsupported negative inference matter here. This is stronger evidence than diagnosing
indecision from response length, but does not isolate the benefit of retaining those
eleven lines or explain every repeated draft/encoding passage.

The initial assembly also has a preparation limitation: the supplied test example
calls two helpers whose definitions are absent. Qwen's first broad read obtains
them. A scripted route using independent tests does not prove that every reasonable
model-chosen implementation approach needs no further acquisition. The actor's broad
range choice and our incomplete example context belong in the same assessment.

All sixteen complete responses, finals, actual results and relevant input/source
changes were directly reviewed. [The turn audit](DIRECT_TRANSCRIPT_AUDIT.md) preserves
useful acquisition, resident rereading, released-source recovery, unsupported guesses,
and correct operational bindings separately. No reviewer supplied any of these findings
to either active run.

## Preserved work and measurement boundaries

An isolated post-closure assessment of the exact rejected C04 proposal reproduces
its uncommitted trial candidate. Its 377-test suite passes with five skips, it exercises
all frozen lookup/transport/raw/resolution paths, detects all four restoration faults,
and contains the correct diagnostic assertions. Overall acceptance still fails for
absent documentation. This demonstrates a sound, more complete test proposal blocked
by the declared capacity rule; it does not turn C04 into an accepted edit or rescue
the trajectory. The [executed assessment](REJECTED_C04_ASSESSMENT.json) and
[reproduction script](check_rejected_proposal.py) make no native-admission claim and
send no inference requests. The later model did not receive this result.

The frozen checker also needs careful interpretation. Both final artifacts contain
functioning raw=True tests. Its observer reports no raw bypass because it requires
the same parser instance as an observed failed lookup; these tests use separate
equivalent instances. Do not call that absence of raw testing. Conversely, the
checker does not mechanically enforce diagnostic-text assertions. Missing docs and
the independently reviewed coverage gaps establish incomplete work without relying
on the raw-association discrepancy. Preserve the original grades; align prospective
acceptance with the stated contract before reusing this checker for another comparison.

Both first checks occur after the final model response. Three operations remain,
but zero requests, so neither has an actual correction opportunity. The original
outcome's explicitly action-only flags remain untouched.
[CHECK_OPPORTUNITIES.json](CHECK_OPPORTUNITIES.json) reports both allowances. All
fourteen nonterminal results are present completely in the next actual inputs.
The final edit/check receipts are stored, but there is no later model decision to
consume them. They are terminal unconsumed feedback, not omitted feedback on a sent
request, and no failure-recovery behavior is established by their mere existence.

One smaller host-policy issue remains: C03's full requested documentation page fits
the hard bound at 22,837 tokens, but the preferred acquisition headroom returns only
already-visible lines at 22,778. The five requested new lines cost just 53 tokens
above the preferred target. This follows the frozen preference, rather than a false
size computation. Its needed edit anchor was already visible, so those five lines
are not a demonstrated explanation of task failure. The common task sentence
"No actions have yet run in this attempt" also becomes stale after dispatch and
should be scoped to the starting snapshot in future work. See the
[host audit](HOST_PATH_AUDIT.md); neither issue is changed inside this comparison.

## Design, verification and decision

This is the [declared evidence-assembly package](../SPEC.md), frozen at ae563cf8,
seed 961211, broad then assembled, with fresh conversations. Both start from the
same actual candidate/67-action archive after C12 of the prior continuation. Both
initial groups are researcher-supplied. Only their initial selected sources differ;
the task, checker, interface, host, sampler and allowances remain identical. Adding
implementation and removing unrelated text also changes length, placement and
generation room. This does not isolate information addition alone, autonomous
selection, or fresh investigation capability on an unseen task.

Qwen3.8-27B UD-IQ3_XXS uses q4_0 K/V, 56,576 physical context, no MTP, native thinking
on/medium/uncapped, a 23,808 input ceiling and 32,768 prospective generation reserve.
No coaching, retry, budget extension, helper inference, configuration switch or host
change occurs during the pair. Each closes three unused operations. The accepted
advisory GPU-margin policy remains in force; neither runtime reports CUDA failure
or truncation, and both owned servers/monitors close normally.

[Broad verification](VERIFICATION-broad.json) and
[assembled verification](VERIFICATION-assembled.json) exactly replay sixteen replies,
eighteen operations, thirty-five native inputs and 429 custody records, including
actual failed checks, source identities, wire constraints and private runtime custody.
Preparation separately passed four focused methods and four native scripted
complete/correction routes, totaling thirty native states and zero inference calls.
Its preserved test/wrapper failures and the execution's pre-reservation missing-parent
error are process findings, not model retries. No full repository-suite rerun is claimed
for this evidence/reporting tranche. Direct reviewer time was not separately timed.

Retain the verified host core and the complete tool reference. Do not promote this
assembly as a productivity improvement or launch another prompt/effort variant from
the consumed allowance. Information at the decision really matters; initial assembly
alone does not keep it available or turn a proposal into a completed contribution.

The next bounded development target should be the transition actually exposed here:
carry an already-formed edit and its supporting interfaces through a working-set
change, then save, check and complete the contribution. First qualify that route
offline using the preserved proposal and existing exact-selection/retrieval operations.
Use a small separate Qwen interpretation consultation before settling a changed
presentation or retention behavior. Judge what it can establish about the missing
base class and pending edit, not whether it can suggest another field. This pair
does not select a new memory mechanism, justify weakening the admission ceiling,
or authorize another live task run. Its attempts and allowances remain closed.
