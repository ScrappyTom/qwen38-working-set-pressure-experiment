# Direct transcript audit — sixteen matched actions

The reviewer directly read all sixteen complete separate thinking fields, all
sixteen final JSON actions, their actual tool results and subsequent host
decisions after the terminal response seal existed. Long responses, including
C15's entire 48,334-character thinking field, were read continuously, not
diagnosed from excerpts or counters. No comparison output was inspected before
sealing. Earlier live monitoring used only progress, usage and runtime telemetry.

The four complete distinct input states, common native system instruction and
complete added reference were directly inspected. The preparation review records
the original native placement inspection; independent execution verification
matches all sixteen actual requests and native prompts to those frozen inputs.
Seeds do not change message text. Every paired user state is identical, with
the same neutral I1–I4 identifiers. This uses exact identity for duplicate inputs,
not a claim to sixteen different state readings. The current review also read
all before/after session snapshots, the complete changed C11 candidate, and the
source returned by each access; unchanged candidate bytes were replay-verified.

For each call below, the exact artifacts are in
[run-001/calls](../run-001/calls): Cnn-rendered-prompt.txt,
Cnn-assistant-reasoning.txt, Cnn-assistant-content.txt, Cnn-host-result.json,
and the before/after candidate and session JSON files. The endpoint response
preserves the original envelope and both output channels. Line references below
refer to the unchanged separate thinking files. The verifier is custody/replay
evidence; this document records the separate direct behavioral review.

No response was offered a continuation. Each normal action was executed once,
recorded, and then the next scheduled conversation began on its own fresh state.
No submission occurred. A failed baseline check is an executed checker failure,
not a failed attempt to answer an unoffered repair turn.

## What was actually available

I1 contains eleven complete, current-version source-read events, with four
content-field objects external and seven resident. The action payloads of those
reads are absent; their saved result bodies exist. The task explicitly specifies
all eleven reads and the four boundary requirements. The source of saved_runs.py
and importers.py is absent from the prompt; the resident modules and task do not
repeat their exact faulty comparisons. Recovery of either is useful, without
implying all four external bodies must be recovered. Eleven read-action examples
are visible; no executed check, patch or reopen example is present.

I2 contains read A, passing check A, then accepted patch A→B. The check has not
validated B. The resident diff contains the complete two-line successor source,
with current size 26 and the current file fingerprint. The old read body and
check streams are external. A read, complete check-action example and patch
argument values are present, but the old guard values must not be reused on B.
Reading B again is confirmation after mutation, not necessary recovery of
absent current source. The instruction to read current source leaves room for
that conservative choice; it does not establish that a further read is required
after every patch.

I3 has one complete resident read of the current two-line file returning 1; the
goal is return 2. There is no prior patch/check example. The file and candidate
fingerprints needed to edit are supplied. Both an exact edit and a legitimate
baseline check can advance the task. The resource illustration is not an
instruction to choose one of them.

I4 has a saved patch with external old/new fields (EVT-0001), an external saved
diff (RES-0001), and a current read of lines 7–8 only. The resident ready() source
does not contain the earlier marker. Its complete=true means the read reached
EOF, not that lines 1–6 were read. Both saved patch and saved diff can recover
the old marker; neither body is currently visible. A read-action example is
visible. The patch signal supplies predecessor guards and payload field names,
but not the external old/new values. No prior reopen or p0_page action example
exists. [Input examples](INPUT_OPERATION_EXAMPLES.json) preserve this distinction
between examples of values and complete instruction about requirements.

All inputs retain the same root-incomplete instruction and resource illustration.
Only the reference condition receives complete forms, limits, current-guard
meanings, return contents and effects in the added system block. The output
grammar is supplied to the server in both conditions.

## I1, seed 42 — C01 legacy / C02 reference

C01 correctly identifies all eleven completed reads and the four external
result bodies. It repeatedly debates which absent module to recover and which
argument names a reopen requires. Lines 70–74 explicitly express uncertainty
about handle versus event_handle. It finally chooses RES-0002 using handle.
Its closing plan mentions batching, although the actual final obeys one action;
no batch was executed. C02 also recognizes completed reading versus residence,
uses the stated reopen_result form, and correctly predicts a full saved result
including source and original bindings (line 5). It selects RES-0001 instead.

The host returns the actual importers.py saved result to C01 and saved_runs.py
to C02. Both include the exact faulty boundary code and unchanged current-version
bindings. Neither changes source, check flags or read coverage. These are useful
recoveries of absent source, not redundant reading caused solely by metadata
confusion. The different target choice is legitimate; no later repair was
offered to measure which ordering is better. Generation is 2,022→901 tokens.

## I1, seed 314159 — C04 legacy / C03 reference

C04 initially oscillates over whether externalization undoes inspection, then
recognizes that the read events count and missing source can be recovered before
mutation. It also debates arguments for operations it has not seen executed.
At line 94 it asserts that check needs no candidate field; line 112 repeats
that conclusion. The final nevertheless contains the required current guard.
C03 uses the complete check and retrieval contracts, including the distinction
between saved access and new coverage. It still spends extensive thinking on
check versus reacquisition and alternative future action sequences.

Both promote the resource illustration into an expected procedure. C03 line 82
calls it a hint for the ideal next sequence; C04 repeatedly appeals to a scripted
expected action. Both finish with exactly the same correctly bound public check.
The host executes it and returns the same 406-byte AssertionError stream about
the imported artifact list. This is a useful baseline failure on the unrepaired
candidate; it is not evidence of failed repair capability. No follow-up is offered.

The reference does not eliminate this deliberation: generation is 6,205→6,125,
while elapsed request time is 402.500→405.687 seconds. C03 also describes the
10,164-byte content-field object as source size in its early planning. Actual
saved_runs.py source is 9,505 bytes, its field object 10,164, and its full saved
result 10,549. The reference accurately describes retrieval but does not redesign
the displayed size grouping. No outcome is attributed to this size misstatement.

## I2, seed 42 — C06 legacy / C05 reference

C06 sees the old check on A and the accepted edit to B. It repeatedly debates
whether the user requires a post-edit read, occasionally confuses payload size
with file size, then selects a new check on B. The earlier complete check example
provides the form, and the final updates its guard to the actual current B.
The host runs the new check successfully and sets B's public-check flag true.
It does not reuse or reopen the old passing result.

C05 recognizes the same transition and chooses to read B to confirm source
(line 12), followed in its plan by checking and submitting. The host returns
the full two-line current source, already reconstructible from the resident
diff. Coverage and check state remain unchanged. That confirmation is a
conservative reading of the task; it produces less immediate validation progress
than C06. Generation falls 3,379→646, but these are different useful actions and
the shorter first response does not establish faster completion of the task.
This pair already had argument examples, so its difference cannot be attributed
solely to resolving missing argument names.

## I2, seed 314159 — C07 legacy / C08 reference

Both identify the unvalidated successor and select the same complete current
read. C07 spends substantial effort comparing the old content-field object's
46 bytes with current file size 26, compounded by miscounting the literal source
and patch fragments. At line 7 it partly recovers the distinction by suspecting
canonical payload sizes. Those sizes describe different objects, not corrupt
source evidence. The original source is 30 bytes; the old/new replacement has
lengths 12/8 and produces 26 bytes. C08 briefly says the patch result is not exact
current source, then expressly recognizes that the diff reconstructs it; it
still chooses reading under the user's wording (line 1).

Both actual reads return the same current file and leave the check flag false.
They are confirmation after mutation, not proof that current source was absent.
Generation is 1,814→485. The reference adds more input than this pair saves in
output, although the response is quicker. The chosen read has an existing
argument example in both conditions.

## I3, seed 42 — C09 legacy / C10 reference

C09 knows the exact required change, but guesses old_string/old_text/old/new,
candidate fields and check forms. It speculates whether candidate identity
changes on mutation and repeatedly reads the budget illustration as procedural
authority. Line 68 says the ideal-path note overrides ambiguity; line 82 favors
omitting a candidate argument. Its final check includes the actual required guard.

C10 knows the exact forms and the actual invalidation of check flags after a
patch. It initially plans a repeat read despite resident complete source, then
recovers the fact that the read is already recorded (line 56). It continues to
treat the illustration as a next-step instruction (line 74), and chooses the
same baseline check as C09. Both actual checks fail on value()==2, as the
unchanged source returns 1. A baseline check is legitimate; treating resource
description as a mandate is the demonstrated friction. Generation is
7,058→4,889. No repeated read or repair turn actually occurs.

## I3, seed 314159 — C12 legacy / C11 reference

C12 recognizes completed source reading and the needed repair, but guesses
the check signature, worries that an extra guard could invalidate the object,
and invokes the resource illustration as evidence to check first (lines 9–11).
Its final supplies the correct guard and the host returns the same legitimate
baseline failure as in C09/C10.

C11 explicitly lists every patch requirement (line 8), verifies the exact
single occurrence of return 1, and plans a new check on the successor after
the patch clears current check flags (line 6). Its final applies precisely that
edit with current pre-edit candidate/file guards. The host returns the correct
two-line successor returning 2, preserving other code. The successor is not
checked or submitted in this call; those planned steps were never offered.
Generation is 1,198→637. The edit realizes the requested source change, but the
baseline check remains a legitimate alternative rather than a scored wrong action.

## I4, seed 42 — C14 legacy / C13 reference

Both recognize that the tail read is partial and that the earlier marker must
be recovered from historical patch/diff evidence. C14 uses the existing read
example, briefly wonders about an additional limit argument, and debates a
future reopen's handle form (lines 7–11). C13 uses the documented operations
but repeatedly switches its planned order between reading and historical
recovery. It says a new read is needed for a valid file fingerprint (line 48),
although the current tail read already supplies that fingerprint; acquiring
the missing source remains a sound reason to read.

Both final actions read service.py from line 1. Both results supply the complete
eight-line source, extend coverage from 7–8 to 1–8 and set complete_reads. This
is necessary acquisition under the complete-reading task, not a redundant reread.
Neither retrieves the old marker in this single action. Generation rises
854→926, and elapsed time rises 47.297→55.125 seconds. This pair shows no effort
benefit from the added reference for an operation already exemplified in history.

## I4, seed 314159 — C15 legacy / C16 reference

C15 correctly recognizes the partial read and the missing old marker before
its extended deliberation. It considers both valid historical recovery routes,
but repeatedly guesses the p0_page interface: parameterless or path-based,
stateful advancement or explicit scope. It treats the unchanged root's
incomplete flag and system imperative as an obligation to expand. Lines 127–179
repeatedly favor a parameterless action. The complete thinking never discusses
an offset value. Its final instead supplies path service.py and offset 1.

The host accepts that valid form and returns only the second of two function
outline rows: ready(), lines 7–8. The same function's exact source was already
resident in the original tail read. The response also supplies outline count
and paging metadata, but no new source needed for the repair or earlier marker.
Offset 1 skips the first outline row; the host implements the requested offset
correctly. This is limited task progress and unnecessary confirmation of the
known tail, despite formal acceptance. It is not a failure to understand that
the complete flag refers only to the requested tail. The unsupported parameterless
plan and accepted final differ; the transcript does not explain selection of
offset 1, and grammar constraints do not establish a causal explanation for it.

C16 explicitly distinguishes EOF from full coverage (line 10), rejects an
outline as insufficient for exact source acquisition (line 12), identifies the
saved action/diff routes, and reads the complete current file. Coverage becomes
1–8; the old marker remains to be retrieved. Generation is 10,648→925 and elapsed
time 556.157→55.281 seconds. This is the largest observed benefit, with better
immediate acquisition under the reference. It does not establish that a specific
reference sentence caused the difference or that navigation wording is fixed.

## Scope of the conclusion

All sixteen final actions were accepted and replayed, with no stale binding or
malformed action. This conceals substantial legacy argument uncertainty and
one low-value outline access. The reference supplies usable operational
information and is supported as a bounded presentation choice. It does not
remove resource-wording deliberation, all confirmation, or displayed-object
scope confusion. Complete requirements also coexist with long thinking.

None of the four I4 responses actually retrieves or uses the old marker; those
plans are not credited as completed historical recovery. C02's explicit full-result
prediction is locally correct, but most calls do not predict full envelopes.
This ordinary-action comparison cannot establish a general retrieved-object
interpretation repair. Task outcome, first-action utility, token cost and latency
remain separate in [RESULTS.md](RESULTS.md).
