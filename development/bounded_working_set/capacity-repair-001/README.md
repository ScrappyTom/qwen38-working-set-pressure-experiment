# Prospective reserve and rejection corrections

These fixes were prepared in an isolated checkout while bounded run-001 kept its
frozen 2a58d31 source. They are not a rescue, replayed model continuation or change
to that run's results.

Two actual saved sizing trials establish an avoidable host restriction. C04's
complete saved check result requires 23,348 input tokens, below 23,808, but the
host rejects it because it insists on keeping another 1,024 tokens free. C05's
complete single search match requires 22,838; the host substitutes status-only
feedback at 22,800 for the same reason. Qwen then spends C06 retrieving the match,
receiving only a 53-byte prefix that does not contain it. Exact storage is intact;
the immediate restriction comes from the admission policy.

The correction makes acquisition headroom spendable. Complete historical results,
edits and ordinary tool feedback may use the actual 23,808-token input allowance.
Bulk source acquisition still prefers to leave 1,024 tokens, but can use them
when no requested page/group fits that preferred target. Every admitted state is
measured; actual hard-limit failures preserve transactional rejection or the
explicit read-only status fallback. No selected source is silently removed, no
result is silently shortened, and model/reasoning settings are unchanged. This
does not promise room for every subsequent edit or solve semantic selection.

The file-filtered history route now includes work_on acquisitions. Its recent/
history row shows source_paths derived from the actual action, rather than
omitting the files acquired by that operation. Full actions remain archived.
The new paths are additional input cost when such rows are shown, not a claim
of behaviorally neutral presentation. No Qwen action has tested this correction.

Source review also found an uncaught CandidateError: a proposed overlong source
line could stop the runner instead of returning a rejected edit. The isolated
candidate-boundary-before.txt reproduces the failure. The host now catches that
declared candidate-policy error and returns it without changing source, ranges,
versions or diffs. Candidate limits themselves are unchanged. The live Qwen run
has not exercised this failure.

Eighteen focused host tests and five mocked runner tests pass after the corrections
(23 selected checks, not a full suite). QUALIFICATION-002.json reconstructs the
actual pre-C04/pre-C05 states, applies the emitted actions in the corrected host,
and obtains the exact full-input bytes already measured by the running server:
23,348 and 22,838 respectively. The candidate and all selected source remain
unchanged. There are no new inference requests or independent re-tokenization in
this replay; token counts come from the original verified native sizing responses.
It establishes delivery feasibility, not what Qwen would do with restored output.

The earlier five new checks, 22-check pass and initial native replay are retained.
qualified-source-001 preserves every identity in the first QUALIFICATION.json,
before the additional rejection-boundary fix. The first attempt to reconstruct
the old test-file snapshot used one fewer separator newline and failed its hash
assertion; the corrected snapshot matches its recorded SHA exactly. No experimental
input, action or result was altered. Use the final source and QUALIFICATION-002
for prospective execution preparation; keep run-001 verification at its frozen
source revision.
