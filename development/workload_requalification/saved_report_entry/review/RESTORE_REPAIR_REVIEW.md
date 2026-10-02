# Qualified checkpoint reconstruction repair

The result and prospective plan were published at **5948a929** before this
implementation. The original live run, preparation, checker, wire inputs and
snapshot bytes remain unchanged. The repaired apparatus is qualified separately;
the original restorer's failed final roundtrip remains a recorded failure.

## Change and reason

`saved_report_task.restore` now interprets its diff-map addresses as canonical
positive integers. It accepts canonical JSON decimal strings or direct integer
keys, rejects aliases, collisions, invalid addresses and nontext values, and
requires the entire map to match accepted archived patch receipts. Inherited
patch receipts supply `diff`; new receipts supply `applied_diff`.

The exact reconstruction assertion compares the restored snapshot against a
typed copy of the incoming state. Neither the caller's state nor the historical
snapshot serializer changes. This fixes lexical-versus-numeric ordering at
addresses 2/8/16 without changing general JSON serialization, custody hashes,
requests, action semantics, budgets or the current model-facing interface.
Receipt consistency is distinct from authenticating the receipt: the external
seal and custody checks remain required.

The exact original Task and test bytes are separately preserved under
`restore-qualification-001/frozen-sources/`, with an index linked to the original
429-file execution source map. A first copy attempt encountered Windows path
length limits before writing a file; shorter provider names were then used.
The original files were not altered by that failed copy attempt.

## Verification

All **nine focused CPU tests pass** in 2.506 seconds. The two added decoder-only
tests exercise four actual-checkpoint restorations (after C04 and final, using
JSON and direct integer keys), compare original raw snapshot bytes and the actual
C05 input, preserve candidate/account/counters, and reject eleven tamper cases.
The seven existing phase/custody tests also pass; those include synthetic checker
executions and are separate from the zero-execution replay qualifier.

An initial targeted test attempt failed before exercising the decoder because a
test fixture named `run` shadowed `unittest.TestCase.run`. It was renamed, and
the original failed log is retained alongside the successful targeted and full
test logs. No production behavior was changed to accommodate that test mistake.

The separately reviewed `qualify_restore.py` loads authenticated archived original
Task code for operation replay, while current code supplies only prospective
reconstruction. Explicit provider records distinguish the two source sets; it
does not pretend repaired source still has its old fingerprint. It uses the
original unchanged verifier, saved native measurements and saved observations,
with subprocess and network access prohibited during evaluation.

The single qualifier attempt passes all **23 actual checkpoints**: exact old
snapshot bytes, model views, candidates, accounts, phase counters, integer diff
lookups and every archived EVT/RES payload agree. It replays six public replies,
sixteen new backend operations, nineteen archive operations, sixteen saved native
inputs and 223 custody records. Both actual check observations are replayed
without execution. The original final restorer reproduces its exact ValueError
before the prospective restorer satisfies the remaining observation/runtime
assertions. There are **no new model, checker, native or subprocess calls** in
this qualifier.

The qualification report SHA-256 is
`336b8df345851c8915358c6393d3e740738353699bc356b40dbd984066a2440d`.
Its helper SHA-256 is
`7f228051822c28fc11ab544239f1af8c4608af8e1d8642f1c2471b3f57854b5b`.
Only the Task and tests differ between its 429-file original/prospective source
maps; the other 427 providers remain byte-equal. Root read the full helper and
independently rechecked its result flags and all prospective source bindings.
Peer review corrected two reporting fields before execution: actual account
handle, and raw checkpoint hash distinct from parsed-map canonical hash.

## Scope and next work

This closes the observed saved-report restoration defect. It is not another model
outcome, a speed improvement, or retroactive success of the original apparatus.
Historical raw evidence and failed verification remain intact. Other adapters
with the same integer/string comparison pattern have a latent crossover risk;
the inspected uniformly two-digit checkpoints do not establish another failure.
Future adapters must qualify mixed-digit addresses rather than inherit an
unverified generic roundtrip claim.

The saved-report contribution remains a correct assisted continuation with
uncoached actions inside its phases. It establishes saved-work extension and
real verification; account continuity and natural pressure remain untested.
Proceed next to the distinct original URL-port entry under its prospective plan,
keeping its empty entry separate from the already completed saved correction.
The ecological, early continuity and discovery/selection obligations remain open.
