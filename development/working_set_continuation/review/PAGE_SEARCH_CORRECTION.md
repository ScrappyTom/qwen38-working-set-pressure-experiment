# Prospective correction after the completed run

The original run and its complete review are published at **f74466d8**. That
revision retains the frozen host needed by `verify.py`; the original exact replay
receipt is unchanged. The following correction is not applied to the saved run,
its actions or its model inputs. No further Qwen request is sent.

Source deduplication can split a selected range around a new feedback page.
Extending the feedback to the retained range's end removes the trailing fragment
and its metadata. Consequently a longer page can be cheaper than a shorter page.
The old binary search incorrectly assumes otherwise and can report no fitting
page even when an interior interval fits.

The correction keeps the existing full-page/binary search first. Before a read
is rejected, it also tries mechanically known same-file fragment boundaries at
the same preferred and hard input limits. It uses the existing native complete
input measurement and exact whole-line construction. It does not remove selected
source, change the budget, truncate a stored result, commit a rejected read or
edit, or select evidence by semantic importance. Group replacement retains its
existing search; no claim is made that this finds the globally largest page for
every possible tokenization cost function.

The actual C03 request now returns tests **1855–1864 at 23,762 native tokens**.
It preserves every selected source range and the unchanged candidate while
supplying one previously absent line. Qualification reconstructs C01/C02 exactly,
uses the unchanged C03 action, checks the corrected complete input against the
already sealed native measurements, and requires the only changed frozen source
to be `working_session.py`. It sends neither new tokenization nor inference.
This is a host counterfactual, not a prediction of Qwen's next action or outcome.

**80 selected tests pass** across page layout, exact source/binding boundaries,
the working session, contribution reply/runner/task, historical evidence,
capacity and visibility. This is not the full repository suite. The three new
regressions cover an interior fitting interval, genuine failure without source
commitment, and exclusion of unrelated-file coordinates from boundary search.

The first test run had two fixture errors: their fake meter made the rejection
message oversized too, so the host correctly refused to commit that rejection.
The fixtures now distinguish an oversized source reply from a deliverable error.
Production code was not changed to satisfy those mistaken fixtures. The failed
output and original test source remain in `page-search-correction-001`; the
corrected 80-test output is separate. The native qualification records the test
source as it stood before that fixture correction; its source is preserved in
`tests-before-fixture-correction.py`. The production host hash is unchanged across
both test runs and native qualification.

Evidence: [native counterfactual qualification](page-search-correction-001/QUALIFICATION.json),
[final validation](page-search-correction-001/FINAL_VALIDATION.json),
[80 passing selected tests](page-search-correction-001/selected-tests-corrected.txt),
[original native probe](page-search-probe-001/RESULT.json), and
[completed model outcome](RESULTS.md).

The larger C15 edit still exceeds the input limit under its retained source group.
This correction does not qualify that edit's delivery, a better selection policy,
Qwen's use of the fitting C03 page or autonomous task completion. The separate
interpretation consultation remains the next proposed model exposure; no new
presentation, coaching, reasoning policy or memory mechanism is adopted here.
