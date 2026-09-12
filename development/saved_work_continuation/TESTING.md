# Verification record

All work in this preparation is offline. No completion endpoint was called.

The first test command incorrectly assumed pytest was installed. Python reported
`No module named pytest`; no tests ran. Converted the new tests to this project's
existing standard-library unittest setup without adding a dependency.

The first unittest pass had five passing cases, one failure and two errors:

- The two mock full-report replacements used pretty JSON of 531 characters,
  exceeding the existing 512-character patch-fragment grammar. Kept the grammar
  and host unchanged; used valid compact JSON in the scripted fixture. An actor
  can instead use smaller replacements. No live model chose the rejected format.
- The rejection-delivery test treated an externally stored patch's old/new text
  as if it were part of the error feedback. The actual rejection error remains in
  resident result fields. Added a result-specific delivery predicate for the new
  runner's feedback gate and preserved the separate full-pair residency check.
  This corrects the proposed gate, not the historical host or sealed measurements.

Eight focused tests subsequently passed. After the completed qualification,
ran them again alongside the six existing delivery-boundary tests: **14 selected
tests passed**, not the full repository suite. Exact console bytes are saved in
the two adjacent `.console.txt` files.

The eight new cases cover saved candidate/capture bindings and uncapped settings;
monotonic prefix admission without a hidden protection policy; rejected edits and
resident error feedback; actual two-phase runner closure with both correct and
incorrect first entries; phase allowance exhaustion without automatic restart;
incomplete response preservation without action execution/retry; and separation
of evaluator imports from the live entry point. Test mocks are not Qwen evidence.

`prepare_saved_work_continuation.py` completed its first offline package attempt.
It reproduces the original native-token baseline, checks four old-state
reacquisitions and three full saved-work routes, and saves 27 distinct tokenizer
counts. The final route deliberately reacquires the first build before correcting
its initially wrong entry. All actual source/report operations, check results,
requests and native inputs remain in preparation-001, sealed without overwriting.

`verify_saved_work_preparation.py` independently replays 53 stored operations and
verifies all 17 selected input/event reconstructions. It then runs the real new
runner with five scripted mock answers against the direct route's exact prepared
native inputs and counts. The checked submission, raw mocks, source identities
and custody chain are saved separately in rehearsal-001. There are **zero real
completion requests** in that rehearsal; its synthetic output token counts are
test values and must never enter actor-performance totals.

The new execution manifest was frozen only after this qualification and rehearsal.
No historical source, score, runtime file, transcript or seal was rewritten.
