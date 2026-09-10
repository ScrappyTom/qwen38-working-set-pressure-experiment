# Eight-request execution package ready for owner decision

The prepared W01–W08 comparison now has a frozen execution path and **15 passing
focused checks**. Zero new model completions ran, no inference runtime was
started for this execution preparation, and run-001 has not been reserved.
The owner-supplied GPT Pro review supports the unchanged comparison and retains
the separate owner execution decision; that decision remains pending.

The [execution specification](EXECUTION_SPEC.md) and
[manifest](EXECUTION_MANIFEST.json) bind the original inputs to
[run_interface_wording.py](../../../scripts/run_interface_wording.py).
The [verification record](EXECUTION_VERIFICATION.json) confirms all eight API
requests match freshly reconstructed host states and all 48 execution-source
identities match. Previous consumed closures and prepared evidence still verify.

| Binding | SHA-256 |
|---|---|
| Execution manifest | 6e763ce033deb5cbe2cd2c429b688e6d5c430efc3c30ac72bb89372caec3dd2a |
| Execution specification | 15b2a3010522b02abdc9a57059cce7f0b16d5f934199d5d6a143587f00634d65 |
| Original prepared package | b009fe4fdb2e0982c8cb1941791d622fb11cb05f84e80302481453234b4d2112 |
| Original preparation seal | 57074b97fab747c939f689e36678f1088ad7b138a2ea2d6f5370c293586f29fe |

## Safeguards exercised

Seven new tests exercise the actual wording adapter and new execution wrapper.
Eight existing tests exercise the unchanged response-preservation/action handler
that the new wrapper reuses. The two commands were:

```text
PYTHONPATH=src
py -3.12 -B -X utf8 -m unittest discover -s tests -p test_interface_wording_execution.py -v
py -3.12 -B -X utf8 -m unittest discover -s tests -p test_interface_comparison_execution.py -v
```

All 15 passed; this was not a full-suite run. Model endpoints and runtime startup
were mocked. Actual local host tools were used for action execution and replay;
the simulated answers are test data, not Qwen behavior or performance evidence.

The tests cover:

- exact eight-row order, fixed settings and E01–E04 exclusion; missing owner
  approval stops before reserving an attempt or starting a runtime;
- native input mismatch stopping before any completion;
- raw response, thinking and final preservation before one actual action;
- unchanged host state reconstruction between conversations, including after
  a correct guarded edit in the wording condition;
- a complete simulated eight-request run, exact response/result custody and
  independently replayed host outcomes, with no offline example dispatched;
- legitimate failed checks and stale-guard rejections without corrective calls;
- incomplete output, wrong accounting, cache reuse, unsupported channels,
  malformed final/envelope, stale telemetry and unexpected executor failures;
- a partial transport response sealed after one attempted request, followed by
  refusal to restart that attempt.

The runner preserves the existing monitored q4/56,576, no-MTP, uncapped xhigh
configuration and advisory memory policy. Real native preflight will re-render
all eight inputs before the first completion; it cannot silently substitute a
different prompt or configuration. The earlier input-fit and +21-token findings
remain unchanged. These offline tests are not a new inference-memory qualification.

## Decision and follow-through

Approve at most W01–W08, four pairs on I3/I4 at the two prepared seeds, one action
each. Approval is recorded with the attempt; the frozen manifest states that it
is required, rather than claiming it was already supplied. No additional design
round, E01–E04 completion, retry or continuation is part of this decision.

After execution, seal first, replay the results and directly review every actual
input, complete thinking field, final, tool result and following host decision.
Save the existing five review products. Judge compulsory-workflow interpretation
and useful, correctly bound progress; neither fewer checks/navigation calls nor
agreement on the next action is the target. A control that does not reproduce
the earlier confusion limits sensitivity. Four pairs cannot separate the two
wording edits or establish whole-task efficiency.

The quoted review's recommendation is retained: make a bounded presentation
decision, then return to multi-turn investigation preparation. Do not default to
another interface micro-test. A new consequential finding would need to earn
one. The next investigation still needs an authentic pressure opportunity and
task-specific allowances, and remains separate from this eight-request approval.
