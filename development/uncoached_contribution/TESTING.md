# Focused checks and preserved preparation corrections

Executed on the Windows checkout with Python 3.12 and PYTHONPATH=src;tests;scripts:

`py -3.12 -B -X utf8 -m unittest test_uncoached_contribution test_roundtrip_task test_contribution_reply test_bounded_parser test_working_session -q`

The final selected command passes 58 tests: 14 new uncoached/session tests, five
task-quality tests, and the existing contribution wrapper and bounded host/runner
checks. This is not a full repository suite. Native qualification is separate;
the mocks in these tests are not Qwen responses or measured native token counts.

New runner coverage includes exact wire custody before sending, unchanged model
settings, no reviewer or private-thinking feedback channel, automatic next-result
delivery, paired edit/check receipts, actual correction after a failed check,
stale rejection, separate request/action allowances, pre-mutation allowance
failure, discussion-only closure, native-preparation stopping, current-bundle
draining, preserved incomplete responses, and normal runtime closure/sealing.
Contract tests distinguish a prior passing check on the same candidate from a
passing check of the current definition, including status-only returned feedback.

Task-quality checks establish that the saved baseline fails only the new coverage
requirement; the offline reference adds one test, passes the 357-test edited
suite and detects all four restoration faults. Default-protocol-only coverage,
transports without diagnostic assertions, and changing an existing regression
all fail the new acceptance contract. The reference never enters the actor's
candidate or initial input. Its execution does not establish Qwen can select
the source, write the test or use the new host controls.

The first selected execution ran 56 tests with four failures. All four stopped
inside the test helper before invoking its checker because I used the nonexistent
anchor `class InlineCommentTestCase`. Direct inspection found the actual
`class InlineCommentStrippingTestCase(unittest.TestCase):` at line 1865. I corrected
the helper, leaving application source untouched; the five task tests then passed.
Two lifecycle/scope checks were added before the final 58-test execution. The
failed attempt remains recorded here and in the tool transcript.

Source review also corrected the native qualification's peak measurement before
execution: proposed oversized sizing trials are distinct from admitted inputs.
Only actual next inputs and feedback states are subject to the admission ceiling;
oversized trials are measured in order to select pages that fit. Both maxima are
reported. This was a preparation-code correction, not a failed native/model run.

The new check-scope defect was reproduced against the actual saved candidate and
actual new checker before the opt-in correction. Read check-scope-probe-001.
Historical session implementations and all consumed evidence remain unchanged.

Both native qualification routes subsequently pass and replay exactly; see
PREPARATION_REVIEW.md and VERIFICATION.json. Index-byte verification confirms all
737 qualified evidence or bound source paths retain their exact SHA-256 content
after staging. The new evidence directory disables Git text conversion, and no
private runtime file is staged. The whitespace check's one fixture exception is
the frozen REFERENCE_TEST.py blank suffix used in insertion; it is preserved with
the qualified patch bytes. Production/test source and authored prose checks pass.
