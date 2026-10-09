# CPU qualification before model exposure

The scoped code change is earned by ordinary behavior. The saved library writes
an option `first=second` with value `third` as `first=second = third`; reading it
back yields option `first`, value `second = third`. Both the pinned CPython 3.14.0
reference and the minimal backport reject this through InvalidWriteError. No
claim of universal round-trip safety is made.

`cpu-qualification-002/RESULTS.json` preserves nine independent execution routes:
12-method contract on the saved baseline, minimal backport and pinned upstream;
the actual checker on correct work, unsafe writing, vacuous tests and missing
documentation; ordinary unittest execution on correct and unsafe work. These
are engineering cases, not model trials. Correct work passes the preserved
362-method suite (five skips), 14 independent contract/preservation/sensitivity
methods and two evaluator regression methods. The unsafe API-compatible baseline
produces seven assertion failures across those two regressions. Full outputs remain
preserved. This protects against crediting an AttributeError as behavior coverage.

`cpu-route-002` executes 17 researcher-selected decisions through the actual host:
failed check, discovery, exact source delivery, guarded implementation edits,
new tests, documentation, passing check, and submission. Every scripted decision
states its supporting input. Admission uses an explicit constant stub; this does
not qualify native token fit, decoder forms, or Qwen's choices. Those remain next.

Four integration tests pass in TESTS-002.log. They verify the empty new-job entry,
actual failure diagnostics plus complete streams beyond 8,192 bytes, exact state
restoration, present-source edit authority and preserved existing test bytes.

Preserved preparation mistakes:

- The first upstream fetch used the annotated tag object and returned HTTP 404
  before any file was saved. The acquisition now pins its peeled commit.
- CPU-001's ordinary test discovery imported `support` outside its `test` package.
  Correct explicit package-qualified `python -m unittest` invocation passes;
  production parser code was not changed to accommodate this harness mistake.
- TESTS-001 assumed the first contract diagnostic concerned the missing exception.
  The first was the equally real missing-regression assertion. The test now checks
  actual diagnostic delivery and the preserved complete traces without imposing
  that unsupported ordering. The production report was not changed for that test.

CPU route 001 checked for an exception name anywhere in the view, which could
be satisfied by the task text. Route 002 checks the actual delivered assessment
for its real missing-regression diagnostic. Export insertion is justified by
the task plus the inspected export tuple, not falsely credited to that diagnostic.
The original route remains preserved; the corrected route also completes.

The current interpreter is Python 3.11.4; the draft specification's guessed patch
version was corrected from the actual execution output before qualification.
No model completion or new GPU runtime has been invoked for this package.
