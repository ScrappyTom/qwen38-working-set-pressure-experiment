# Direct transcript audit — W01–W08

The reviewing Codex agent directly read all eight complete saved thinking fields,
final actions, actual results and before/after candidate/session snapshots after
verifying the terminal seal. All actual request bytes and endpoint settings were
checked against preparation. The four unique complete native inputs (W01, W02,
W05, W06) were read directly; W04/W03/W08/W07 respectively contain byte-identical
native inputs with their other prospectively selected seed. Raw endpoint fields
were checked against the separately saved texts. No excerpt/search/diagnostic
substitutes for the complete response review recorded here.

Evidence for each W ID is under [run-001/calls](../run-001/calls):
`ID-rendered-prompt.txt`, `ID-endpoint-request.json`, `ID-endpoint-response.json`,
`ID-assistant-reasoning.txt`, `ID-assistant-content.txt`, `ID-action.json`,
`ID-host-result.json`, and the four candidate/session snapshots. The receipt and
verification supply hashes, full runtime/seed settings and individual costs.
Thinking indicates interpretation and intended action; it does not establish
why sampling chose a final action or prove unexecuted future work.

## What the model actually had

Both conditions contained the complete visible tool reference: required keys,
forms, limits, guard meanings and effects. The wording condition only removed
the illustrative correction sequence and clarified root/page scope. No condition
had a prescribed preferred next action. The task still required exact source
before mutation, a current-candidate public check and submission.

I3 supplied an accepted current read of all two lines of service.py, including
`def value():\n    return 1\n`, candidate f698835a…, file hash 5d080563…,
interval 1–2 and EOF. Root file size was 26 bytes. The separate result-body
field object `{"content":"def value():\n    return 1\n"}` was 42 canonical
JSON bytes. These sizes concern different objects, not inconsistent source.
No earlier patch/check example was supplied in this state. All I3 candidates
started identically and needed the literal-return edit.

I4 supplied the one historical patch's target and predecessor/successor bindings,
with saved old/new at EVT-0001 and saved diff result at RES-0001, both external.
Only current lines 7–8, `def ready():\n    return True\n`, were resident.
The read's complete=true meant EOF, not coverage of lines 1–6. The current file
was 112 bytes; the partial content was 29 bytes and its field object 45 bytes.
The root, task, tool reference, resident signals and displayed source contained
neither marker spelling. The old marker was not inferable from its hash.

The host-side current candidate contained `MARKER = "silver-meadow"`; historical
patch payload and diff contained old `"copper-orbit"` and new `"silver-meadow"`.
These host-only copies were not silently credited as model knowledge. The public
checker also contains the expected old marker, but its source was not in the
input and no W action executed that check. No later result supplied duplicate
evidence inside a model conversation: every path stopped after one action.

## W01 — I3 / 1729 / reference

[Complete thinking](../run-001/calls/W01-assistant-reasoning.txt),
[final](../run-001/calls/W01-assistant-content.txt),
[actual result](../run-001/calls/W01-host-result.json).

The model identified the full source and correct current version, but called the
26/42-byte scopes inconsistent. It briefly asked whether the old instruction
required p0_page, then recognized that the exact current source was already
available. It selected an edit rather than imposing navigation or a preliminary
check. Its planned later check was explicitly on the successor candidate.

The final replaced `    return 1\n` with `    return 2\n`, with both correct
pre-edit guards. The host accepted it and produced candidate d61f08e4… and file
hash d3fe3723…, containing exactly `def value():\n    return 2\n`.
No source reread, page, check or submission followed. The unresolved size-scope
claim and transient navigation question are friction in a successful action,
not evidence of extra tool use or a required global navigation gate.

## W02 — I3 / 1729 / wording

[Complete thinking](../run-001/calls/W02-assistant-reasoning.txt),
[final](../run-001/calls/W02-assistant-content.txt),
[actual result](../run-001/calls/W02-host-result.json).

The model used the resident source, recognized both guards as pre-edit values,
checked the exact fragment's uniqueness and planned to use the returned new
candidate ID for a subsequent check. It did not discuss a resource-imposed action
order, global navigation gate or size conflict.

The final replaced `    return 1` with `    return 2` under the correct guards.
Although the fragments differ from W01 by excluding their final newline, the
resulting file and candidate are byte-identical to W01. The action was useful
and accepted; planned checking and submission were not offered or executed.

## W03 — I3 / 271828 / wording

[Complete thinking](../run-001/calls/W03-assistant-reasoning.txt),
[final](../run-001/calls/W03-assistant-content.txt),
[actual result](../run-001/calls/W03-host-result.json).

The model spent part of its opening paragraph manually counting the 26-byte
source against the displayed 42-byte field object. It suggested JSON escaping
might explain the difference but did not fully identify the serialized object
boundary. It then correctly used the complete current read, recognized the
pre-edit guards, considered several equivalent patch fragments and planned a
new check after mutation. It briefly considered reopening the known source and
rejected that as unnecessary.

The final replaced `return 1` with `return 2`, with correct guards; the host
produced the same exact successor as W01/W02. At 1,107 output tokens and 62.109
seconds, this was the longest response. Its visible byte-counting and fragment
deliberation are descriptive observations, not a causal allocation of the
660-token excess over W04. The wording package did not remove object-scope
friction; no resulting wrong edit or additional acquisition occurred.

## W04 — I3 / 271828 / reference

[Complete thinking](../run-001/calls/W04-assistant-reasoning.txt),
[final](../run-001/calls/W04-assistant-content.txt),
[actual result](../run-001/calls/W04-host-result.json).

The model noted the incomplete root and briefly questioned whether an exact read
was needed again. It resolved this using the resident complete result and matching
candidate/file bindings. It explicitly decided that P0 was unnecessary, rather
than requiring the root flag to change. It did not turn the resource illustration
into a check-first obligation.

Its final is byte-identical to W03's minimal replacement and guards. The host
accepted it and produced the same successor. W04's 447 output tokens and 29.360
seconds were much lower despite transient uncertainty. No reread or page was
executed; no new check or submission was offered.

## W05 — I4 / 1729 / wording

[Complete thinking](../run-001/calls/W05-assistant-reasoning.txt),
[final](../run-001/calls/W05-assistant-content.txt),
[actual result](../run-001/calls/W05-host-result.json).

The model correctly interpreted complete=true on the 7–8 read as reaching EOF,
identified missing lines 1–6, and located EVT-0001/RES-0001 as historical recovery
options. It planned a full current read, then saved old/new recovery, repair,
check and submission. These are plans, not completed operations. Its occasional
"call limit 22 remaining" phrasing uses the displayed remaining count; the actual
fixture limit was 24 and this comparison offered only one action.

The final read service.py from line 1. The host returned all eight current lines
and recorded coverage 1–8 without changing the candidate or check status. The
result exposes silver-meadow, not the earlier copper-orbit. Reading the two
already visible tail lines again is part of a useful whole-file read that fills
the missing beginning; it is not an avoidable repeated-read action. The intended
historical retrieval was not performed or followed by another model turn.

## W06 — I4 / 1729 / reference

[Complete thinking](../run-001/calls/W06-assistant-reasoning.txt),
[final](../run-001/calls/W06-assistant-content.txt),
[actual result](../run-001/calls/W06-host-result.json).

The model recognized both missing current source and absent historical old/new.
It considered either acquisition order, explicitly distinguishing retrieval from
mutation and retaining the requirement for a full current read before editing.
It preferred the actual saved action payload at EVT-0001 to a saved result diff.
It did not infer the old marker, require paging or prescribe a baseline check.

The final reopened EVT-0001. The host returned precisely the 52-byte old/new
payload, including copper-orbit, with its matching hash and address. The current
candidate, partial coverage 7–8 and false check/submission flags stayed unchanged.
This is useful acquisition of absent evidence, not replay of the historical edit.
The model predicted the payload fields correctly, but was not given a subsequent
turn to interpret or use the actual returned text.

## W07 — I4 / 271828 / reference

[Complete thinking](../run-001/calls/W07-assistant-reasoning.txt),
[final](../run-001/calls/W07-assistant-content.txt),
[actual result](../run-001/calls/W07-host-result.json).

The model quickly identified the historical patch and incomplete current read,
recognized that reopening did not mutate, and chose old/new recovery before the
necessary source read. It retained both needs without inventing a global
navigation prerequisite. No argument guessing or check-first obligation appears.

Its final and actual result are byte-identical to W06. The host obtained the old
marker while preserving current source and partial read coverage. At 270 output
tokens, this illustrates a useful control response with little deliberation.
Later reading, repair, check and submission remain unobserved, not failed.

## W08 — I4 / 271828 / wording

[Complete thinking](../run-001/calls/W08-assistant-reasoning.txt),
[final](../run-001/calls/W08-assistant-content.txt),
[actual result](../run-001/calls/W08-host-result.json).

The model identified the exact visible tail and file size, then planned current
reading before historical recovery and repair. Its phrase about reopening to see
the "pre-edit state" is broad; no event retrieval was executed here, so this is
not evidence that it expected or understood a complete predecessor file.

The final and result are byte-identical to W05: a useful full current read,
unchanged candidate, completed coverage, no old-marker retrieval or verification.
Its 224 output tokens and 19.719 seconds are lower than W07, but the operations
obtain different necessary information. Neither acquisition order is declared
superior from this one-action evidence.

## Host continuation and surviving conclusions

All four I3 edits agree with the stated literal-return repair and yield the same
successor. Their session snapshots retain prior read bookkeeping and show false
current check/submission flags; they do not establish a new read of the successor
or a passing check. Both I4 source reads fill missing coverage; both saved-event
retrievals obtain the missing historical marker without modifying source. None
of these eight results was fed back to the actor in this comparison.

There are zero checks, zero submissions, zero executed navigation operations and
zero rejected actions. All paths are **host-withheld after one action**, not
model-abandoned tasks. No actual first-check or post-failure correction opportunity
was observed. The controls retain momentary navigation/read uncertainty but do
not reproduce compulsory checking or paging; the candidate retains byte-scope
friction. These distinctions, the pair costs and the next-work decision are in
[RESULTS.md](RESULTS.md), not inferred from the accepted-action count alone.
