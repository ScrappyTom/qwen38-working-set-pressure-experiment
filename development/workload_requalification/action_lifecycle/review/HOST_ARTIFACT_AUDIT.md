# Saved work and host evidence

The final candidate is 3dce94985b28ebdae35c0bbf6be4d7db639503dc8319a32ffbe8727431e602b1.
Only src/dispatchledger/reporting/totals.py changes. The saved unified diff is
saved-contribution.patch. Root reviewed the complete thirteen-file starting
candidate, task, exact changed file, actual check output and final bindings.

The reporting invariant is that each group contains the sum of the latest active
receipt for every ticket assigned to that group. Registry.accept supplies before
and after receipts; entries.contributions removes the active predecessor and adds
the active successor. Selecting bucket(receipt) separately for those contributions
preserves the invariant when labels, units or status change. A duplicate/older
receipt produces no change. Zero groups are still omitted and rows remain sorted.
The repair does not change validation, revision selection, duplicate semantics,
public signatures or the helpers' interfaces. All twelve other files are exact.

CHK-0014 is an actual completed execution, return code zero, against that successor
and checker 46841e0e6328588ca1cab0b87ccf35cc651ddfc9c9b13ce17b9dc2d9736d4854.
Its 6,255-byte stdout is fully preserved, with empty stderr. It reports all 38
cases passing: decoded/selected values, 22 report cases and fourteen rejection
cases. The independent-ticket/moved-group example gives four ALPHA cables and six
BETA sensors, as required. The raw stream is JSON lines, not one JSON document;
an initial reviewer parsing assumption was corrected without changing any evidence.

C11 receives the full 522-byte applied diff and exact successor binding. C12
receives the actual observation and current candidate/checker applicability. The
archived model account does not authorize either the edit or submission. Three
source reads deliver current exact bytes; thirteen source extents across the seven
inputs are verified. All nine nonterminal operation receipts are represented in
the subsequent input. No capacity fallback or rejected operation occurs.

The replay retains the five inherited operations and five consumed requests and
begins at C06. It reproduces every intermediate/final snapshot, seven decoded
replies and eleven new operations using the saved observation, without executing
another checker. The closure reconciles seven new dispatches with twelve cumulative
requests and eleven new operations with sixteen cumulative operations. Runtime
shutdown and port release are recorded. Full verification details are in
VERIFICATION.json and ASSESSMENT.json.

This is a source-reviewed correct bounded contribution. It does not establish
arbitrary untested behavior, pressure continuity, failed-check recovery, large
archive navigation or general autonomous reliability. No fresh repair of the host
or further receipt retry is justified merely to obtain another pass.
