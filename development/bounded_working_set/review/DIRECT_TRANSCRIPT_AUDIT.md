# Direct transcript audit

All eight complete thinking responses (254,300 characters), their final actions
(579 characters), actual results, relevant exact inputs and saved candidate were
directly reviewed. The complete library and delivered test lines 1-605 were read.
[Contemporaneous per-call notes](DIRECT_REVIEW_NOTES.md) retain the detailed
observations and a corrected progress-message mistake. C09 has an input but no
returned output; no claim of direct response review is made for it.

| Call | Direct observation | Consequence |
| --- | --- | --- |
| C01 | Correct remaining-work plan, then repeats the root tree already shown | No new source |
| C02 | Considers grouping/recovery, selects full current library | Acquires all 1,347 lines |
| C03 | Connects exception and parser logic, derives useful regression cases | Acquires test lines 1-605 |
| C04 | Correct historical-check meaning; oscillates about future conversation visibility | Useful check retrieval rejected by reserve policy |
| C05 | Correct search-before-document-read plan amid speculative draft text | Search hit stored, withheld from next input |
| C06 | Correctly recognizes status-only feedback and asks for missing result | Exact 53-byte header arrives; match still absent |
| C07 | Wants unseen test remainder; previous check error body no longer visible | Ordinary paged read rejected |
| C08 | Plans a useful group, but repeats the old check retrieval; mistakes partial bytes for display-only shortening | Retrieval rejected; no contribution saved |

Useful reasoning is present. Qwen derives one-based line/source/raw-line checks,
copy/pickle arguments, both parser variants and indentation/comment behavior from
actual source. It recognizes that unseen test structure and documentation should
be inspected. It correctly treats retrieval as reading historical evidence rather
than rerunning a check. It does not apply an old passing check to a new version,
invent and execute a marker edit, or silently overwrite saved work.

The same responses repeatedly draft guessed upstream class layouts and release
histories, revisit already articulated contract facts, and rehearse actions. The
task does not supply the historical CPython release, and no versionadded claim is
saved. Some uncertainty concerns real unread source; some speculation is not
needed to fulfill the task. The total response cost is measured, but no causal
fraction is assigned to interface ambiguity, xhigh instructions or model indecision.

Two mistaken visibility beliefs recur. C04/C05 sometimes suppose that earlier
conversation will retain source after work_on releases it. Actual requests contain
only the system message and current state. Near C08's end, Qwen says all 335 saved
bytes are present despite the visible 53-byte prefix and next_offset=53. This is
a misinterpretation of available boundary information. It has not yet produced
an incorrect artifact, and the selected retrieval seeks a different result;
the statement is not proof of why that action was chosen.

C08's query confusion has a different input basis. It associates RES-0037 with
MultilineContinuationError and speculates about zero matches. The actual query
was MissingSectionHeaderError with one hit, but neither query nor hit appears in
C08's recent summary/prefix. This is an unsupported reconstruction of absent
information. The host still has the full action/result, which the model could
retrieve. That does not make the displayed recent row semantically sufficient.

The strong host failure must be repaired without asking Qwen to count, split or
work around it. The interpretation findings warrant a small separate, neutral
consultation before settling another presentation change. Ask what is actually
visible, which earlier operation can be identified, and what a selected group
would retain. Preserve the first answer; source-check it; allow retention of the
interface. Do not convert this into another broad vocabulary study or an automatic
reasoning-policy change merely because the responses are long.
