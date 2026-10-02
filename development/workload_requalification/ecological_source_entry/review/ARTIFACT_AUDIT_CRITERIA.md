# E19 source-entry artifact audit criteria

Prepared while run002 is active, from the unchanged task, original public and
hidden scripts, and named original source. No running response or private draft
was inspected. No checker, hidden evaluation, model or native operation ran.

The audit will compare the sealed current artifact with the exact 25-file
entry, rather than treating an accepted edit or passing public observation as
the complete contract.

* Inclusive extraction: a unit with inclusive start/end must materialize every
  declared source line, including a one-line unit. The original `_make_unit`
  hashes `lines[start_line - 1:end_line]`; exact extraction must agree with that
  producer rather than changing its hash or identifier to accommodate missing
  text. Preserve the existing line-normalization convention.
* Strict truncation: `truncated` is true precisely when `len(exact_text)` exceeds
  `max_chars`. Equality returns the whole exact text with false; a smaller limit
  returns the corresponding prefix with true. Hash validation precedes clipping.
* Preservation: the inline-text branch returns the same inline bytes; stale-map
  hash mismatches remain blocked; unresolved handles and missing artifacts retain
  their existing blocked behavior. Public call signatures, records and exact
  identifiers stay unchanged. All 23 non-target file bodies must remain exact;
  tests and dependencies may not be changed.
* Actual work and evidence: inspect every final saved diff and actual check
  observation. A current public pass must bind the actual submitted successor
  and unchanged checker definition. Reopening a result is retrieval, not another
  execution. No private draft is counted as work.
* Named source obligation: inspect actual sent current-source bodies and their
  candidate/version/range before the first accepted mutation for the four named
  files. Report the extents and substantive evidence, not just accepted reads or
  inventory labels. E19's wording does not impose E20's every-line inspection
  rule, and the host has no extra four-file edit-eligibility gate.

The original public script exercises a three-line Python function, exact-limit
completion and a shorter prefix. The unchanged hidden script adds a one-line
function reopened by unit ID. Neither script by itself establishes inline-text
preservation, all blocked paths, identifier preservation or unchanged unrelated
files. Those require direct artifact comparison and any separately authorized,
clearly labeled post-seal reviewer evidence. Hidden outcomes will not be returned
to the live actor.

Saved-data replay and accounting will run only after the response seal is present,
using the bound helpers. The first verifier attempt and any failure will remain
preserved before a prospective helper repair.
