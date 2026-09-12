# Explicit file admission qualified; larger model work remains next

Nine real source files exceeded the historical 24,000-byte admission limit. The
earlier process-local counterfactual showed that the existing paging/recovery
paths could handle them. This earns a host configuration change, separately from
the saved-work consultation's decision to retain the presentation.

`Candidate.create(..., max_file_bytes=...)` now accepts an explicit immutable
policy. The default remains 24,000. Patches and `with_files` preserve the policy;
reconstruction must explicitly receive the same selected limit from the task's
execution configuration. Candidate IDs continue to identify exact file content.
The existing visible-reference generator can take the actual candidate and state
its effective limit. Its default output remains byte-identical to the archived
small-task reference. No model operation selects or changes this policy.

The selected engineering qualification uses 1,048,576 bytes per file. All other
file-count, total, line, path, patch and result bounds remain unchanged. In
particular, source lines still have a 512-byte limit and a candidate is still
limited to 256 files and 8,000,000 total bytes. This does not admit arbitrary
documents or repositories, or qualify every possible policy the API can express.

The new script uses the actual host on 40 real source files totaling 602,677 bytes,
plus an explicitly constructed 1,048,576-byte Python comment file containing
quotation marks and backslashes. The constructed file tests escaping at the
boundary; it is not a model task or context padding. The real inventory differs
from the earlier counterfactual because the candidate implementation changed.

All 252 whole-line reads store and recover exactly: 56 real-source pages and 196
constructed boundary pages. Each stored result remains independently addressable
when its body is omitted from an external event view. No prior thinking or whole
exchange is added to recovery. Source body, complete result and historical wrapper
all satisfy their unchanged limits. The largest recovered wrapper is 21,933 bytes,
below 22,000. This tests mechanical external rendering and recovery, not delivery
in a token-admitted model input.

A guarded edit of the largest real file (47,907 bytes) succeeds, retains the
selected policy, rejects a stale repeat without mutation, and passes a syntax
check of all 41 files. An old page remains bound to its predecessor after the edit.
Explicit reconstruction and `with_files` retain the candidate and policy. The
five focused tests additionally cover exact-limit admission, one-byte overflow,
growth rejection without predecessor mutation, invalid policy values and truthful
visible requirements. Syntax compilation is not application correctness.

The qualification completes 508 actual host operations and separately replays all
21 saved-work operations under the unchanged default. Their results, final session
and payload identities match the archived snapshot exactly. Another 58 selected
existing checks pass, with eight exact historical wording-action replays. Those
checks cover return/recovery rejection paths, navigation, core candidate behavior,
inspection measurement, V3 events and ecological/consultation fixtures. This is
not a full repository suite or additional model evidence.

The new five-test run and 508-operation qualification pass on their first executed
attempts; the earlier four-test subset is also retained. A later ad-hoc seal check
initially lacked PYTHONPATH and stopped at import before inspecting the files;
the independent standard-library hash check then verified all three sealed public
files. No qualified result or source was changed to address that shell setup error.

Exact operations, inventory, reference text and results are preserved under
`explicit-file-qualification-001/`; its seal is
`a6486c1942a6c2106d38d0cef31a7534e41b40ab238badd763f73318a790ce87`.
The original counterfactual and historical experiments are unchanged. Source and
test identities and all selected-check output are in `default-regressions-001.json`.
The two selected test logs and both executed qualification logs remain available.

This makes larger source admissible through an earned explicit option. It does
not yet demonstrate a useful Qwen contribution on that material, resolve growing
event history, or qualify a new input/generation allocation. The next preparation
must choose a real task whose necessary evidence is available through the existing
tools, qualify exact feedback delivery and check the resulting work. Keep the
1 MiB stress file out of that task. Preserve the current model/runtime/reasoning
policy unless a separately justified change is qualified.
