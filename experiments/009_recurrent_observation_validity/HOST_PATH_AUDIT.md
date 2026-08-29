# Experiment 009 host-path audit

## Scope

This is the condition-aware post-seal audit of every non-success path in the
sealed Experiment 009 run. It distinguishes actions Qwen actually emitted from
requests the host denied before HTTP and work the actor never had an
opportunity to attempt.

The run contains 117 prepared invocations and 112 HTTP completions. The five
invocations without completions were prospective capacity denials. There were
no endpoint, parser, protocol, checker, candidate-binding, or tool-execution
failures. Every one of the 112 completed actions was accepted.

## Exact stop paths

| path | last completed actor work | next host decision | classification |
|---|---|---|---|
| cell 01 Alpha / C50 | reopened `C3%%`, made the correct Phase-B patch, passed `public`, probed current `N9%%`, read both bridge files | denied prospective B07 at 47,713 offline prompt tokens because prompt + 512 reasoning + 2,500 output exceeded 50,176 | mechanical physical-capacity stop; Qwen was never offered `fork_ready` |
| cell 01 Alpha / T25 | reopened `C3%%`, read `beacon/label.py` twice, patched correctly, passed, probed `N9%%`, read both bridge files | denied prospective B09 at 22,042 offline prompt tokens because prompt + 512 reasoning + 2,500 output exceeded 25,000 | mechanically capacity-denied after one redundant actor read |
| cell 02 Beta / C50 | reopened `L6!!`, read and patched `pulse/label.py`, passed, probed `P4!!`, read both bridge files | denied prospective B08 at 47,782 offline prompt tokens | mechanical physical-capacity stop; Qwen was never offered `fork_ready` |
| cell 03 Alpha / C50 | reopened `C3%%`, read and patched the label, passed, probed `N9%%`, read both bridge files | denied prospective B08 at 47,689 offline prompt tokens | mechanical physical-capacity stop |
| cell 03 Alpha / T25 | produced the correct Phase-B candidate and current `N9%%` observation, then read amber in four 50-line pages and brass in three 50-line pages | frozen twelve-action Phase-B budget ended with brass incomplete; no thirteenth actor call was permitted | model-budget exhaustion caused by conservative actor-selected paging, not capacity or host failure |
| cell 04 Beta / C50 | reopened `L6!!`, read and patched the label, passed, probed `P4!!`, read both bridge files | denied prospective B08 at 47,774 offline prompt tokens | mechanical physical-capacity stop |

Cell 01 T25 and cell 03 T25 are behavioral noncompletions, but for different
reasons. Cell 01's ninth request was mechanically inadmissible at 25k. Cell 03
never prepared a thirteenth request because Qwen had consumed the frozen action
budget with small pages. Neither path may be described as Qwen choosing to
stop, failing a check, or choosing a stale observation.

## Successful recurrent host paths

Both Beta T25 paths completed the exact required host sequence:

```text
fresh Phase-B reconstruction
  -> current Phase-A observation reopened
  -> exact target source read
  -> correct candidate-bound patch
  -> public check passed
  -> new candidate-bound probe captured
  -> both bridge files read
  -> fork_ready accepted
  -> prospective Phase-C request denied at 25k
  -> fresh Phase-C reconstruction
  -> current Phase-B observation reopened
  -> exact source read
  -> correct candidate-bound patch
  -> public check passed
  -> submit accepted
```

The second transition was not scripted or host-forced. It followed the actual
actor-created Phase-B history and an exact prospective capacity denial.

## Checker and binding audit

- All four prefix `prefork` checks passed.
- All eight Phase-B `public` checks passed on the exact patched candidates.
- Both Phase-C `public` checks passed on the exact final candidates.
- No check result was reused after candidate mutation.
- Every patch supplied the exact current candidate ID and exact current file
  hash.
- Both submissions named the exact checked final candidate.
- Post-seal hidden grading passed both submitted candidates.
- No completed action was rejected, repaired, retried, or rescued.

The model-facing checks were therefore valid. There is no analogue of the
earlier Experiment 001 checker contamination.

## Capacity and runtime accounting

All 112 completed calls reported an accounting delta of exactly zero between
the frozen offline tokenizer count and llama.cpp's server prompt count. Every
T25 call remained within its 25,000-token total envelope. Every C50 denial was
issued before HTTP under the frozen 50,176-token physical envelope.

The owned server was PID 8928. Shutdown evidence records that the exact child
exited, port 18092 was released, and no `llama-server.exe` process remained.
An independent post-run check confirmed the same state. Shutdown is not
inferred from port release alone.

## Non-outcome host metadata inconsistency

The Phase-C observation directory correctly exposed candidate IDs and exact
handles, but its legacy v1 descriptive fields are imprecise:

- `ordering` says `sequence_ascending`, while reconstructed directories append
  Phase-B records after prefix records even though their stage-local sequence
  values restart at lower numbers;
- `complete_for_reopenable_dynamic_prefix_results` remains named for prefix
  results even when the directory also contains Phase-B results.

This did not affect the run. Both Phase-C actors ignored the misleading
stage-local sequence values, compared candidate bindings, selected `OBS-0005`,
and reopened the current observation. The exact bodies and hashes were correct.

The inconsistency must be removed through a prospectively versioned directory
schema before this directory format is reused in another measured study. The
sealed v1 evidence must not be rewritten, and changing the v1 renderer in
place would break historical replay.

## Disposition

No host defect affected a measured outcome. The two completed recurrent paths
are valid positive behavioral evidence. The two Alpha T25 noncompletions are
valid evidence about Qwen's local read and budget policy. C50 provides a valid
mechanical capacity reference but no completed Phase-C behavioral control.

