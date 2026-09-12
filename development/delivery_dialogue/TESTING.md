# Focused preparation checks

The first execution of four dialogue checks passed three and failed the exact
four-message continuation assertion. The test double returned the same mutable
`initial` object on every call; appending the continuation also changed the
test's expected initial-message list. The production builder creates a fresh
request on each call. The test double was corrected to return a deep copy;
production code was not changed to satisfy this mistaken test assumption.

Original failure: `test_four_message_continuation_keeps_exact_final_and_follow_up`,
`AssertionError: Lists differ`, with the expected initial list incorrectly
containing the added assistant/user messages. This happened before preparation
or model exposure. The corrected run passed all four checks in 0.180 seconds.
They cover exact historical input preservation and uncapped settings, all four
continuation messages with exact final/follow-up bytes, rejection of executable
channels and invalid conversation shapes, and zero completion dispatch after
native mismatch or input-capacity denial. Both rejected preparations preserve a
stopped seal and refuse reuse of the turn directory. These are mocked lifecycle
checks, not model responses. The six separate delivery-probe checks also pass.
