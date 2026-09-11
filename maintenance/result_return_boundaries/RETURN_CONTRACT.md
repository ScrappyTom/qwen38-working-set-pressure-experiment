# Prospective return contract for subsequent preparation

This supplements the retained complete tool reference. It is not a new live
prompt or an edit to the consumed comparison's reference. Future preparation
must incorporate these facts, verify them against the selected host source,
and inspect the exact native input before exposure.

- `read` returns exact whole lines. Its page fits 18,000 source UTF-8 bytes,
  22,000 bytes for the complete serialized result, and 22,000 bytes for that
  result's exact historical-access wrapper. JSON escaping can shorten a page.
  Follow `next_start_line` for the remaining source. `complete` describes reaching
  EOF on this read; a tail-only page does not prove whole-file coverage.
- Candidate and file fingerprints bind the acquired source. Historical reads
  remain historical after edits; they do not establish inspection of changed
  successor content. Unchanged-file evidence can still apply across a candidate
  change. These acquisition records do not prove later model delivery or use.
- `reopen_result` / `reopen_observation` return the complete original serialized
  result in `exact_result_utf8`, with its hash and byte count. They do not rerun
  checks, mutate source, or create new reading coverage. Retrieval preserves the
  original candidate/check binding and canonical address, even when accessed
  repeatedly. It does not return only selected output fields.
- `reopen_event` returns exact saved action-content fields, with the payload's
  hash and byte count. It does not replay an edit. All advertised imported
  historical bodies must fit their actual retrieval wrappers.
- A complete result must pass admission before acquisition, mutation or terminal
  state is committed. A read or edit rejected by this boundary is not credited
  as successful. A check can have executed before its return is rejected; that
  rejection is not a newly accepted passing observation.
- Directory `p0_page` counts do not depend on signature presentation limits.
  File outlines still reject a signature above 240 bytes or unparseable Python;
  such errors are returned normally. Exact source remains accessible with `read`.
  Paging does not change the root's repository-scope flags.

No action names, required arguments, version guards, stored originals or canonical
recovery identities change. Larger pages and oversized mutation/check results
can behave differently under the new bounds; qualify that cost in task work.
