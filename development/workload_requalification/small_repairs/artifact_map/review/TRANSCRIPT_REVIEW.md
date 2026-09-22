# Artifact-map regression: direct transcript review

Development run `run-001`, frozen source `3107f3cf`. Review is read-only with respect
to the run. Complete saved reasoning, final replies, actual input fields and tool
results were inspected through C20, including the complete closing response.
The run closed normally with checked submission.
No evaluator feedback was sent to the actor. Findings below do not constitute an
instruction to the live run.

## Actual input and interpretation

The task requires repair of an edit-followed-by-reopen failure while preserving
unrelated source, unchanged-content behavior, later updates and genuinely stale
reference rejection. The episode annotation distinguishes this original incident
from the current repair session. The initial candidate contains 25 source files;
the selected sources and saved results are empty, as is operation history. The
system offers explicit public checking after edits, without automatic checking.
Private reasoning and discussion do not persist to the next request. The current
account does persist, attributed to the model and not certified as true.

| Call | Complete response and actual consequence |
| --- | --- |
| C01 | Explores `src`; receives the child directory `src/addressable_information_layer`. |
| C02 | Separates the task's library from the operating host, records an exploratory account, and lists directory entries 0–15. Its possible interpretations of reopening are hypotheses, not acquired source knowledge. |
| C03 | Names patching, records and availability as plausible files, records that account and requests entries 16 onward. Receives nine entries, including `reopen.py`, with no next offset. |
| C04 | Says it will start exploring and requests the root. The input already contains the full second directory page, the previous page's action row, and an account naming three files. Root listing adds no new path beyond `src`. |
| C05 | Repeats the first 16-entry directory page and records the same exploratory account. Its input contains only the root as latest feedback; earlier directory bodies have left the prompt. Known directory path and three plausible basenames remain in the account. |
| C06 | Correctly recognizes that the first page is visible, then requests the second page again. The previous second-page body is absent, while a recent row records its prior request at offset 16. |
| C07 | Names the three account files but chooses the first directory page again. The second page is complete in its input; the first page's paths are absent apart from account references. |
| C08 | Moves to the known `patching.py` path using `p0_page`. Receives four function outlines and reusable exact region references, including `apply_patch_preview` at lines 80–145. This acquires navigation, not source-edit authority. |
| C09 | The complete actionable outline is in the input. Qwen nevertheless returns to the first directory page and replaces the account with a generic statement that it is starting exploration, dropping the three named files. This call cannot be explained solely by unavailable source coordinates. |
| C10 | Sees the first directory page and a recent row recording the prior outline request, but not the outline's function names, ranges or references. It recognizes `patching.py` was paged, records that fact, then requests the second directory page again. |
| C11 | Uses the delivered second page to identify `reopen.py`, records a more specific account and requests its outline. Receives `materialize_reopen`, lines 10–82. No exact source was supplied by this outline. |
| C12 | Explicitly acknowledges that outline and requests source lines 1–100. The host returns all 83 actual lines, including the exact stale-map content-hash check. This is the first source acquisition, and demonstrates use of a newly delivered location. |
| C13 | Receives full `reopen.py`, accurately describes the hash guard and hypothesizes a stale stored hash after editing. Names `artifact_units.py` and the two imported helpers, but requests the directory's first page again. The acquired source remains fully visible; this repetition is not source loss. |
| C14 | Again traces the resident reopen code and obtains `artifact_units.py` lines 1–200. This includes import, map construction, address resolution and exact text extraction, plus the Python unitizer. The page explicitly continues at 201 and is not the entire 459-line file. |
| C15 | Identifies three plausible causes: faulty hash construction, inconsistent extraction, or failure to rebuild the map. Considers newline handling, then records the unresolved extraction/hash question and requests the rest of `artifact_units.py` (200–459). `_make_unit` arrives with the same line-joining rule. This is meaningful new acquisition; one overlapping line does not make the whole request redundant. The account precedes that evidence and does not yet claim to have resolved it. |
| C16 | Has the complete merged 459-line unit module and complete reopen module. Correctly finds their normal extraction/hash rules consistent, repeatedly considers whether the edit handler rebuilds the map, and explicitly notices the earlier tree result is absent. Requests the first directory page again. The account still asks the pre-acquisition `_make_unit` question; no account update carries the newly established consistency. The actual input contains no `patching.py` path or old outline. This call costs 3,359 generated tokens and does not save a repair. |
| C17 | Receives the directory page, keeps both source files and updates the account to their consistent hash rules plus the unresolved edit/map question. After substantial repeated reasoning, reads all 158 lines of `patching.py`. The new source contains `new_map = address_map` immediately after creation of the new artifact. The account correctly precedes this decisive observation and does not claim it already established the defect. |
| C18 | Identifies the stale `new_map = address_map` assignment and changes it to `build_address_map(new_artifact)`, which is already imported and has been inspected. The exact three-line old fragment is resident; candidate and file guards match. The host saves successor `23b5c17999963faf7453c68a6b537ae6c447555f77eb0a835bfa659ad47e89aa`. Qwen plans a public check and submission; no check is automatically executed. |
| C19 | Receives the actual successful patch receipt and refreshed source. Repeatedly asks what the previous patch changed, attempts manual line counting, hypothesizes other caller defects and rederives hash consistency. It explicitly notes the incident predates this repair session. Eventually updates its account to the saved patch/current candidate and requests the public check. The actual check executes and passes on that successor; no additional edit is made. |
| C20 | Reads the current public pass and submission eligibility, then submits the same candidate without another acquisition, edit or check. The account still says the check is needed; Qwen correctly uses the later actual observation instead. No new observation follows the terminal submission. |

## Navigation information path

The actual C04–C07 inputs were inspected field by field. `current_p0` remains the
original root description (`src`, 25 files, 128,524 bytes). It does not incorporate
the browsed directory. `recent_activity` retains accepted tree path, offset,
candidate, sequence and recovery handles, but not the request limit, entry paths,
total count or continuation offset. All selected source/result lists are empty;
there is no capacity fallback or source eviction.

Those four actual inputs contain 5,243, 5,103, 5,457 and 5,252 native tokens,
respectively, against the 23,808 ceiling. This establishes that the observed
disappearance was not caused by reaching that ceiling; it does not substitute
for native measurement of a proposed replacement view. Exact input digests and
extracted fields are in `NAVIGATION_INFORMATION_PATH.json`, generated by the
review-only `../../review/navigation_path.py` helper.

The most recent directory page is fully delivered. Requesting another operation
removes its body from the normal input unless explicitly selected. Thus the two
pages never form a combined resident directory listing. C05, after the root
request, contains neither page body. The model retains a mechanically recorded
fact that it listed these paths, but not the resulting full map. C10 similarly
retains the fact of outlining a file while losing its supplied function locations.
This is an observed host presentation omission, not a failed store or incomplete
immediate result delivery.

The limit of 16 tree entries forces at least two operations for this 25-entry
directory. That is an operation contract, not an observed physical-capacity need.
Native counterfactual sizing has not been run by this reviewer. A prospective
bounded navigation view would need its own capacity and stale-version tests.

The omission does not explain every repeated action. Exact usable file paths
remain in accounts through C08, and C09 receives the complete patching outline.
No evidence establishes that missing navigation detail is the sole cause, or
that retaining the entire directory would cause successful repair. Conversely,
it would be inaccurate to describe every repeated listing as rereading a fully
visible answer. Directly shown information, archived information and inferred
information remain separate.

C16 supplies a stronger consequence-level observation than the earliest repeats:
Qwen itself says the earlier tree's body is not visible while it seeks the edit
handler. Direct input inspection confirms this. The six-row history still names
EVT-0020's tree path and offset, but neither its entries nor the earlier patching
outline. Its current account names only the two inspected source modules. The
input is 11,774 tokens and contains both whole files, so this is navigation-detail
loss under the default policy, not displacement of source under capacity pressure.
Qwen also entertains unsupported assumptions about caller behavior while the
caller is uninspected; the record does not show that a retained map alone would
prevent that deliberation.

## Edit-to-check information path

The complete C19 input contains the accepted patch's actual predecessor/successor
bindings, pre/post line intervals, current file fingerprint and recoverable EVT
handle. Its action summary names the operation and path but omits `old` and `new`.
All selected sources have refreshed to the successor, including the now-correct
`build_address_map(new_artifact)` line. No old fragment or diff is resident. The
account still asks to see the edit handler, because it was authored before that
acquisition and was not updated in C18. This is truthful provenance, but it does
not carry the repair's explanation into C19.

Qwen repeatedly tries to reconstruct the actual change and says it could inspect
the event, but ultimately runs the current check instead. It is inaccurate to say
the old and new code were both shown and the actor ignored the difference. It is
also inaccurate to say no useful next operation was possible: the current binding
and untested status were clear, and the actor requested the appropriate check.
The cost attributable to absent change detail is not isolated. A bounded exact
change report would be an earned candidate for prospective information-path
qualification, without treating account prose as host-certified explanation.

`CHANGE_INFORMATION_PATH.json` inventories every C19 JSON string field and both
messages, identifies the archived exact patch and diff, and confirms absence of
the changed old line, old fragment and diff from the input. The replacement
fragment is present in refreshed source. Native C19 input is 13,878 tokens; its
4,998 generated tokens take 309.468 seconds. That cost contains both legitimate
verification reasoning and repeated reconstruction; it is not all assigned to the
missing delta. C20 takes 202 generated tokens and closes correctly from real
passing feedback.

## Review boundaries

All twenty complete reasoning fields and final replies, all actual operations and
receipts, actual current-source bodies and pertinent state fields were reviewed.
Exact replay separately checks every complete input, source identity, operation,
intermediate state and final state. A represented receipt sequence alone is not
used as proof that useful fields remained visible. The two concrete omissions
above remain findings within a successful trajectory.

No account is treated as verified reasoning, and this run does not prove account
benefit. It does show use of provisional accounts and correct preference for a
later check over an outdated account. No failed check, rejected action, group
replacement, historical retrieval or capacity transition occurs. It is a source-led
repair with successful check consumption, not pressure-continuity evidence.
