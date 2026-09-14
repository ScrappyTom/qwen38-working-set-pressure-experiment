# An uncoached contribution completes, with substantial deliberation cost

Qwen independently selects useful source, adds three meaningful regression tests,
requests a check on its saved successor and submits using that passing result.
The existing library, parsing regression, documentation and unrelated tests are
preserved. The corrected host and combined edit/check reply are now exercised in
an actual uncoached contribution. This is useful completion evidence, with a
52.863-minute task-loop cost that prevents calling the interaction efficient.

Read the [saved patch](../run-001/diffs/EVT-0042.patch),
[complete transcript audit](DIRECT_TRANSCRIPT_AUDIT.md),
[host path](HOST_PATH_AUDIT.md), [construction finding](APPARATUS_FINDING.md) and
[execution/custody receipt](EXECUTION_RECEIPT.md). All four complete responses,
including the long thinking, were directly reviewed against actual inputs,
results and subsequent state. No reviewer facts or guidance entered the run.

## What was completed

The task extends a previously completed configparser backport, starting from its
exact saved candidate and an empty source group. It requests tests for copying
and pickling an exception raised by real parser input, with and without a final
newline on the offending line. It supplies the behavioral contract and target
file, but no reference test, required source list or selected group. This is
coverage work on reused real source, not novel defect discovery.

Qwen searches for the exception and selects four source regions containing its
real constructor, raise branch, test imports and neighboring exception tests.
The existing parsing regression supplies the necessary allow_no_value=True
configuration. Qwen uses that fact without a reviewer correction. One accepted
replacement adds independent copy, deepcopy and pickle test methods. Each uses
a fresh parser for both endings and asserts the required restored identity and
diagnostic state. Pickle iterates protocols 0-5 on the executing Python.

The public check reports:

- Saved suite: 356 tests, five skips, zero failures/errors.
- Edited suite: 359 tests, five skips, zero failures/errors; eight existing
  backport contract cases also pass.
- Actual parser-raised errors traverse both copy modes and all six pickle
  protocols for both newline cases.
- Each of four restoration faults is detected by all three new tests: wrong
  source, wrong line number, stripped raw line and lost errors list. These are
  intentionally failing mutation checks within a passing coverage assessment,
  not failed task checks encountered and repaired by the actor.

Direct artifact review confirms the checks' meaning. The new methods assert the
exact restored class, constructor arguments, source, one-based line number, raw
line, errors and literal expected diagnostic; str/repr are compared too. They
obtain exceptions from read_string, not direct exception construction. All nine
other candidate files are byte-identical. All 106 pre-existing class methods in
the test file retain identical syntax trees. The exact patch is 95 added lines;
no reviewer rewrote it to pass. Fault probes are a bounded quality screen, not
exhaustive proof of every serialization contract or Python implementation.

Final candidate:
baa81a49475c59f1686de781ef396e6709d7efb1cb31eec62992576790b2ab84.
The new check binds both that candidate and the current checker definition.
Historical passing checks stay readable but cannot authorize this new contract.

## Actions and cost

| Response | Actual progress | Input tokens | Generated tokens | Request seconds |
| --- | --- | ---: | ---: | ---: |
| C01 | Search; five source/test locations | 3,775 | 873 | 51.843 |
| C02 | Select four exact source regions with work_on | 3,984 | 5,385 | 284.672 |
| C03 | Save three tests and request successor check; passes | 7,761 | 44,852 | 2,784.234 |
| C04 | Use passing current check and submit | 10,735 | 283 | 39.047 |
| Total | Four requests, five actual operations | 26,255 | 51,393 | 3,159.796 |

Generation includes thinking and final output. Model requests take 52.663 minutes;
the complete task loop takes 52.863 minutes. Response processing and native
admission total 5.217 seconds, included in the loop. Other host/lifecycle work
accounts for the remainder of its 11.985-second difference from request time.
These timings exclude development and full review; reviewer effort and Codex
inference were not separately instrumented. They are not a fully loaded cost.

C03 accounts for 87.273% of generation and 88.114% of request time. It develops a
workable test design early, then repeatedly revisits implementation guesses,
test structure, action order and JSON/Python escaping. A conspicuous spelling
loop eventually resolves through a valid JSON Unicode escape. Further checking
and speculation continue afterward. This is more specific than equating long
thinking with either valuable care or a host defect; precise causal shares are
unmeasured. The full transcript retains useful analysis and adverse cost alike.

The C04 submission is short and correctly uses actual feedback, with no recheck,
reread, rewrite or required explanatory closing call. No executed acquisition is
repeated. Unsupported reasoning and repeated deliberation occur within calls;
they must not be counted as extra tool operations. C02's source reconstruction
is often wrong before acquisition, but its eventual source choice is useful.

## What this adds, and what it leaves open

The contribution is uncoached. Source selection, correct configuration, saved
work, check feedback and submission compose under the current host. Actual
combined use is established; a causal speed gain is not. Host-enforced source
eligibility and passing-check submission are acknowledged rather than counted
as independent proof of voluntary model behavior. The task still supplies a
specific goal, target file and strong checks, and builds on prior assisted work.

All sources remain resident; no working-set externalization or context-pressure
boundary occurs. Peak sent input is 10,735 against 23,808. There is no failed
repair, rejected action, broad-group replacement or older-history retrieval.
This result does not resolve the earlier scalability/selection failures or
demonstrate sustained autonomous productivity across varied work.

Generation is the immediate capacity concern on this trajectory. C03 reaches
52,613 input-plus-generated tokens, only 3,963 below physical context. Its output
exceeds the prospective 32,768 reserve by 12,084. The reserve was never a cap;
no settings changed and no truncation occurred. Success with a 7,761-token input
does not qualify that response at the 23,808 input ceiling. GPU telemetry reaches
163 MiB free under the previously approved advisory policy; the runtime is closed.

## Next decision

Retain the corrected host and this completed artifact. The next useful
qualification is a bounded comparison of reasoning allocation on complete work,
keeping the host, task, starting candidate, input policy and checks fixed. Freeze
one supported alternative effort policy, matched seeds, request/action limits
and a stopping rule before exposure. Judge checked preservation, termination and
total cost; shorter incorrect work is not an improvement. Existing design-call
benchmarks and this single xhigh trajectory do not establish the alternative.

Track output construction explicitly in that review. Do not dismiss the observed
encoding loop because a valid workaround exists. If a representation intervention
is considered, first consult Qwen separately on the exact difficult draft and
input, then qualify one source-checked alternative without simultaneously changing
effort. This recommendation is not another run or an adopted format change.
Qwen remains the test pilot outside active runs; neither this review nor a future
consultation should be inserted as coaching during execution.

The prepared attempt is consumed and its 12 unused requests / 19 operations are
closed. Complete replay and custody checks pass. No additional model inference,
production change, new memory feature or automatic successor follows from this
result.
