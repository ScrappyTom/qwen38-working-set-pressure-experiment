# A prior task's passing check authorized a different contract

This offline probe uses the actual completed documentation candidate and its 39
archived actions. RES-0038 is a passing check of the earlier backport contract.
The new checker requires additional exception-transport regression coverage.
The candidate contains no such new test methods and the new checker returns
passed=false, while all 356 saved tests and eight previous contract tests pass.

The original WorkingSession nevertheless accepts submission on the strength of
RES-0038 because its applicability test checks only the candidate identity. The
candidate has not changed, but the meaning of the public check has. PROBE.json
preserves both the failing new check and accepted premature submission, not a
model prediction or a mocked result. No Qwen inference was performed.

starting-candidate.json, starting-state.json and checker.py preserve the exact
inputs. The task text used at the probe is retained in PROBE.json. Source bindings
identify the unchanged legacy session, executor and candidate implementation.
The state snapshot is before either operation; checker evaluation ran on a clone,
so it did not replace the old passing check in the subsequent submission probe.

The opt-in ContributionSession now records the checker definition fingerprint
on new accepted checks and requires it to match alongside the candidate. Its
view distinguishes candidate_matches from check_definition_matches. Old results
are neither deleted nor rewritten; their check scope is unbound and they remain
historical evidence. CORRECTED.json shows the same early submission rejected.
Tests also qualify reuse when both candidate and checker match, failure when
the checker changes, and scope preservation with status-only feedback.

This is a host defect and separately qualified repair for successive contracts.
It did not occur in the completed Qwen documentation attempt, which performed a
real check after editing and received the required passing result. Do not revise
that historical score or credit this offline probe as model behavior.
