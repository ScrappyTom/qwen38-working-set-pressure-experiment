# Compiler incident execution readiness

The comparison is prepared for the separate owner execution decision. **No Qwen
completion, new tokenization request or model launch occurred during this work.**
The task, host, representation, reasoning policy and sealed preparation are intact.

The frozen [execution manifest](EXECUTION_MANIFEST.json) has SHA256
`c195b5c1ae0f0e234ba46f77d052fb86aa71ce8848d190d28a8b14612501d10d`.
It binds the prepared task, its review and verification, 71 source files, the
execution specification and the two initial requests. The proposed live scope is:

| Cell | Seed | Continuation order, if pressure occurs |
|---|---:|---|
| C01 | 49979687 | Resident 23,808, then externalized 16,000 |
| C02 | 67867967 | Externalized 16,000, then resident 23,808 |

Each trajectory has **32 actions including its shared prefix**. There are at most
**128 completion attempts** across the stage, with no retry, replacement or rescue.
A shared prefix is executed once. Early submission or exhausted allowance creates
no artificial fork. The bound is conservative: sharing at least one action in each
forked cell limits that worst-case schedule to 126 distinct requests.

## Safeguards and checks

The new [runner](../../scripts/run_compiler_incident.py) loads the sealed candidate,
task, checker and observations without the task's oracle builder. Both initial
inputs must match their original native bytes and 3,744-token count before any
completion. Actual later inputs are reconstructed and counted; the first complete
input above 16,000 creates the fork. Exact candidate, check state, history and
canonical recovery maps are copied before changing residency. Only the oldest
payload prefix is removed, with no semantic selection or automatic retrieval.

It preserves raw inputs and responses before parsing, validates actions against
the supplied schema, checks source identity around requests, records actual tool
feedback and verifies its reconstruction into later inputs. Structurally valid
tool rejections consume allowance and return normally. Incomplete output,
transport failure, invalid accounting, source drift or lost monitoring stops and
seals the entire attempt. An ordinary branch capacity stop permits its peer to
proceed. A shutdown guard prevents reporting completion with an unclosed runtime
or occupied dedicated port.

[Test records](execution-checks-001/README.md) document **22 distinct passing
focused tests**: a 21-test run, followed by three lifecycle tests after the final
shutdown guard (two repeated and one new). They cover real-tool fork/recovery,
both branch orders, passing and failed checks inherited at a fork, actual
correction afterward, full shared-inclusive budgets, early unchecked submission,
capacity denial, invalid responses, partial transport, source changes, monitoring,
package tampering and once-only reservation. These are selected checks, not a
full-suite claim. An attempted historical suite refused setup because its older
host pin differs after the documented return-boundary maintenance; that failure
is saved and is not counted as passing coverage. Its frozen package was not edited.

## Frozen-engine rehearsal

The [sealed rehearsal](execution-rehearsal-001/MOCK_REHEARSAL_SEAL.json) uses mocked
answers with the exact previously prepared native inputs and real tool execution.
The test helper has no network fallback. The final frozen engine produced:

| Quantity | Observed offline |
|---|---:|
| Mocked responses / actual Qwen requests | 34 / 0 |
| Shared actions in each cell | 6 |
| Input at each fork | 17,753 tokens |
| Resident / externalized trajectory actions | 11 / 12 |
| Largest admitted resident / externalized input | 20,812 / 15,817 tokens |
| Checked submissions | 4, each passing all 26 contract cases |

[Independent replay](execution-checks-001/REHEARSAL_VERIFICATION.json) verified all
34 selected actions and actual results, all 50 prepared inputs including withheld
trials, 402 custody records and 599 sealed files. It reconstructed each input from
the preceding real tool state, checked exact native bytes against the preparation,
and verified candidate/check/submission identity. This is engineering evidence;
mocked thinking and token output are not Qwen behavior or measured inference cost.

Direct inspection of the smaller branch's boundary inputs confirms the important
evidence distinction. At action 7, the original capture is external; the first
build, second build and partial report remain visible. The mocked action retrieves
the original. In the next input, that exact return and the second build are visible,
while the first build is now external. Its finding remains in the resident partial
report patch. The report is completed, the optimizer repaired, and the actual
passing check is then used for submission. A future model success must account for
that retained report as well as recovered evidence.

## Remaining decision and limits

Use unchanged Qwen3.8-27B UD-IQ3_XXS, q4/56,576, no MTP and uncapped xhigh thinking.
The 32,768 generation reserve is planning space, not an output cap; actual harder
responses may still exhaust physical capacity. The accepted GPU margin remains
advisory with 200ms sampling and fresh boundary checks. Sampling during a pending
HTTP request is not an interrupting watchdog. No new margin approval is needed.

The 16,000 treatment is an input working set, not the former 25,000 total envelope.
The historical comparison depends on the captures; the optimizer repair itself
can be source-led. Finite scripted routes do not guarantee Qwen reaches pressure,
rejects a hypothesis or needs a correction. Preserve whichever trajectory occurs.

The existing [task specification](SPEC.md) and [execution specification](EXECUTION_SPEC.md)
reserve the separate owner decision on these two cells and at most 128 requests.
The run directory has not been reserved and no execution approval is recorded here.
After approval and execution, seal and inspect every actual prompt, full thinking,
action and result before deciding whether a separate Qwen dialogue or any change
is earned. Retaining the interface remains a complete outcome.
