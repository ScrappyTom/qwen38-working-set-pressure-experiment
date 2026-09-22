# Ecological workload entry map

This is a read-only reconciliation for the current workload programme, dated
September 22, 2026. No checker, tokenizer, runtime, preparation path, or model was
executed. No historical source or result was changed. The next port should preserve
the task contracts below, rather than treating the eight Experiment 020 outcomes
as eight different repair tasks or reducing them to a candidate-only check.

There are **four task contracts**, with different starting defects. Three have
actual historical model exposure. E19-OBS-SUMMARY-GRAPH was prepared and checked
offline but never reached by the interrupted model schedule. Its absence of a model
result is an entry distinction, not an unsuccessful model attempt.

[ENTRY_INVENTORY.json](ENTRY_INVENTORY.json) records exact task, candidate-file,
checker, observation, schedule, and terminal snapshot identities. The small
[inventory script](build_inventory.py) reads and hashes files only. It verified all
170 files in the two bank manifests, all four initial candidate identities, and all
13 available summary-bound snapshots (including unchanged shared prefixes).
This is not a new full response-seal verification or grading run.

## Distinct entries

All four initial candidates contain 25 Python modules from the same owner-controlled
Addressable Information Layer donor. The experiment-specific neutral `__init__.py`
replaces the production initializer because its runner dependency exceeded the old
24,000-byte file bound. Keep those exact admitted candidate bytes; substituting the
current donor checkout or the artifact-map task's repaired candidate changes entry.
No editable tests are present in these candidates; checkers live outside them.

| Entry | Initial candidate | Candidate bytes | Explicit inspection |
|---|---|---:|---|
| E19-SOURCE-REOPEN | `d2a57a0044458310fbe0b915eb88447b6f76b87dd511d68a0e31c29416342116` | 128,575 | Four named files, exact current source before mutation |
| E19-OBS-SUMMARY-GRAPH | `476f83a90c40b0897e1ab5d6bc00bbb52cf3a4fe60cc11c1dd47ab3da85d0172` | 128,545 | Four named files, exact current source before mutation; current observation must be selected and reopened |
| E20-SOURCE-IMPORT-BOUNDARIES | `2355c3eaa32dcf8db2659a75feb3a93309255fbff60e14b7f154dc34c47675c0` | 128,546 | Eleven named files, exact complete reads before first mutation |
| E20-OBS-VERIFIER-SAFETY | `a8ccf6bcf04177b0199148e6a91dad4ac9f1818c0898403b0fc91cceb43dcadd` | 128,545 | Ten named files, exact complete reads before first mutation; current observation must be selected and reopened |

The task files and complete file manifests are under each original
`experiments/019_owner_controlled_ecological_pilot/fresh_bank` or
`experiments/020_owner_controlled_ecological_pilot_v2/fresh_bank` directory.
The JSON inventory supplies repo-relative paths and full hashes to avoid copying
candidate material into another bank during this review.

### E19-SOURCE-REOPEN

The task requires inclusive `ArtifactUnit.start_line`/`end_line` materialization and
strict `len(exact_text) > max_chars` truncation: equality is complete. It also requires
preserving inline text, hash-mismatch blocking, exact identifiers, and public APIs;
no changed tests or new dependencies; a current public check and submission.

The inspected faulty source has an end-exclusive slice ending at `end_line - 1`
in `artifact_units.exact_text_for_unit`, and `>= max_chars` in
`reopen.materialize_reopen`. The inline-text early return and observed-hash check
are separate behavior to retain.

Mandatory paths, all under `src/addressable_information_layer/`:
`artifact_units.py`, `reopen.py`, `records.py`, `hashing.py` (33,990 bytes).
The E19 wording says inspect exact source; it does **not** use E20's strengthened
"exact complete read of every path" wording. The completed historical path did read
all four in full. Preserve this distinction rather than silently upgrading E19.

The public checker tests a three-line function at the exact character limit and
one below it. The hidden checker repeats those assertions and adds a one-line
function addressed by unit ID. The checkers do not exhaustively establish the
preservation clauses; direct artifact review remains required.

### E19-OBS-SUMMARY-GRAPH

The task requires `collection_stale` when any summary is stale, current summary IDs
differ from graph IDs, or the collection's input IDs differ. It requires sorted
`missing_artifact_ids` to identify summary artifacts without a map, preserves public
APIs, forbids changing tests, and requires a current public check and submission.

The faulty source combines the first two stale conditions with `and`, and iterates
map IDs absent from summaries when computing missing IDs. The collection-input
comparison is already separately present. Mandatory inspection paths are
`summary_graph.py`, `summaries.py`, `records.py`, `policy.py` (27,301 bytes).

The initial directory offers two observation identities. `OBS-0001` is a passing
legacy serializer record for candidate `5c7eba4f...`, not the initial candidate.
`OBS-0002` is a 336-byte failed summary-graph record bound to `476f83a9...`, containing
the stale-ID and missing-ID-direction failures. The task explicitly asks the actor
to select the current binding and reopen the body. Do not preload that body, remove
the distractor, reinterpret retrieval as a new check, or replace the selection
obligation with a host-chosen failure summary.

The public checker builds two artifact summaries and removes one address map,
checking stale status and the missing artifact ID. The hidden checker additionally
checks a complete map set is fresh and that removing a summary makes the collection
stale. No live transcript exists for this entry: cell 3 was never dispatched.
The prepared initial input, stored observation bodies, exact source and both
checkers were inspected here; the old offline qualification receipt records
initial public/hidden failure and known-good public/hidden success.

### E20-SOURCE-IMPORT-BOUNDARIES

The four declared corrections concern equality at `max_file_bytes`, the first
`max_files=N` eligible files, JSONL event record 1000, and an embedded artifact on
record 1000. Later eligible files/records remain excluded. Preserve deterministic
ordering, exclusions, schemas, identities, materialization, and APIs. No modified
tests or new dependencies; current public check and submission required.

The faulty `importers.fixture_from_directory` skips equality with `>=` and only
stops after `len(artifacts) > max_files`. `saved_runs` uses `>= MAX_JSONL_LINES` in
both event and embedded-artifact loops. Its record parsing, filename selection,
size caps, ordering, and embedded artifact construction are not replacement targets.

The mandatory complete audit is 72,238 bytes across these eleven paths:
`saved_runs.py`, `importers.py`, `fixture_packs.py`, `records.py`, `content_log.py`,
`artifact_units.py`, `hashing.py`, `storage.py`, `renderer.py`, `policy.py`,
`readiness.py`. The whole inspection must precede the **first accepted mutation**,
including an otherwise harmless formatting edit. Required reading is stated in
the actor's task, not a hidden criterion or an evaluator-supplied ideal path.

The public checker creates two five-byte text files and a 1000-record JSONL file;
it expects exactly the first text file at `max_files=1, max_file_bytes=5`, all 1000
events, and the final embedded artifact. The hidden checker also tests an empty
file at byte limit zero and 1001 JSONL records yielding 1000 events.

There is a known acceptance gap, already recorded in
`maintenance/resume_after_020/FINDING.md`: the frozen graders do not test a zero
**file count**. The donor and both R50 repairs append one file before checking this
limit and passed 9/12 supplemental cases; the X25 repairs check the count first and
passed 12/12. Those were separate later measurements, not changed original scores.
The future port must preserve the original grades and carry this declared `N`
boundary into artifact assessment or a separately qualified supplemental check.
An original-grader pass must not be presented as proof that the entire stated
boundary contract is satisfied. No supplemental check was run in this review.

### E20-OBS-VERIFIER-SAFETY

The task requires rejection of absolute, parent-traversing and empty paths while
accepting canonical relative paths. Timeouts clamp to inclusive `1..60` with invalid
values defaulting to 20. Preserve command-prefix enforcement, workspace containment,
deterministic receipts, and APIs; no test changes or new dependencies; current
public check and submission required.

The faulty `_safe_relative_path` joins absolute/parent conditions with `and`.
`_bounded_timeout` uses an inner `max` where an upper clamp is required. The inspected
code also normalizes backslashes, resolves working directories, and enforces
containment independently; keep those operations and their actual contracts.

The mandatory complete audit is 68,898 bytes across ten paths:
`verifiers.py`, `records.py`, `hashing.py`, `readiness.py`, `policy.py`, `routing.py`,
`reducers.py`, `verifier_logs.py`, `storage.py`, `artifact_units.py`.

The two observation identities are a 147-byte passing legacy verifier smoke result
for `23b5c179...` and a 322-byte failed safety result for the initial `a8ccf6bc...`
candidate. `OBS-0002` contains the observed unsafe path acceptance and minimum-60
timeout behavior. Keep the directory, exact body, original candidate binding, and
explicit model-selected historical access together as an entry obligation.

The public checker tests canonical/absolute/parent/empty paths, timeout values
0/20/above maximum/invalid, a contained subdirectory and rejected escape. The hidden
checker adds backslash normalization, a negative timeout and a very large timeout.
These are fixed assertion scripts, not a general verifier safety certification.

## Historical exposure, artifacts and pressure

Both experiments declared seeds 173205 and 223607, 24 total action opportunities
per trajectory, and counterbalanced R50/X25 branches. The earlier actor was
Qwen3.8-27B AD-IQ2_S with low, server-capped 512-token thinking, a 50,176-token physical
context and q4 KV. The current IQ3_XXS medium-uncapped 56,576 configuration is a
different development configuration; its result must not be called an unchanged
replication or a controlled model/interface speed comparison.

The initial event histories and selected sources were empty. Observation entries
contain pre-existing fixture observations, not model-acquired source or a new pass.
The shared prefix within each seed was actual Qwen work, then cloned once into both
branches. No cross-cell model conversation was carried. A future original-entry run
must not inherit a successful historical patch, chosen reading group, analysis,
hidden checker, supplemental probe, or a different seed's history.

E19 saved thirteen model responses, twelve complete action/result pairs, and no
treatment branch. Seed 173205 made nine calls and submitted candidate
`5c7eba4fbad9c51325a9abc4f4b27c5b8d9eedb5b344558b5921915ed854a49f`, changing only
`artifact_units.py` and `reopen.py`. Its actual check and submission replies establish
the pass despite the historical summary incorrectly saying
`shared_call_budget_exhausted`. Seed 223607 saved four responses, but the fourth
no-op proposal encountered non-idempotent snapshot custody before a result was saved.
The old top-level receipt counts only nine; the raw response files and subsequent
mechanical addendum establish thirteen. Neither observation seed ran. Preserve these
apparatus discrepancies instead of taking one summary field as authority.

E20 made 106 physical calls: 40 shared-prefix calls, 27 R50 continuation calls and
39 X25 continuation calls. The conceptual paired totals are 67 and 79 because each
prefix is counted with each condition. All eight terminal candidates passed their
frozen public and post-seal hidden scripts and submitted. This review verified their
snapshot bytes/identities, not their checks through new execution.

| E20 task / seed | Shared calls | R50 continuation / total | X25 continuation / total | Changed source |
|---|---:|---:|---:|---|
| Import / 173205 | 9 | 10 / 19 | 10 / 19 | importers.py, saved_runs.py |
| Import / 223607 | 9 | 9 / 18 | 14 / 23 | importers.py, saved_runs.py |
| Verifier / 173205 | 11 | 4 / 15 | 7 / 18 | verifiers.py |
| Verifier / 223607 | 11 | 4 / 15 | 8 / 19 | verifiers.py |

All four E20 forks occurred before any accepted edit. The import forks followed nine
of eleven reads; the verifier forks followed observation recovery and all ten reads.
The identical pre-fork requests were denied by the old total 25k envelope but admitted
under R50. X25 retained a further 1000-token operating margin by removing oldest exact
bodies while keeping the full event signal. R50 kept bodies resident. These are
experimental transition obligations, not additional repair tasks or independently
sampled prefixes.

The September maintenance reanalysis corrected continuous exact-source coverage
measurement and rechecked all eight pre-edit audits against actual source versions
and bytes. Its findings preserve the original eight grades. A page's EOF flag,
path-only read history, outline, account, or stored-but-undelivered result must not
be substituted for continuous delivered source coverage in a new audit.

There is no user Phase A/Phase B task handoff, `fork_ready` task action, or fresh
instruction after the boundary here. The historical host calls the entire task
`continuation` even at entry and performs the pressure fork itself. Do not invent a
phase gate by borrowing the earlier synthetic phase tasks. Conversely, neither the
old submit handler nor the Python graders enforced every inspection/observation
obligation. Those are separately audited task behaviors; current guard enforcement
would be a declared host change, not evidence of independent model judgment.

## Concrete next-port boundary

1. Port the four exact original entries and fixed public graders independently.
   E19 summary-graph remains a prepared-only engineering entry unless the programme
   explicitly adds its first model exposure; it is not counted as a historic failure.
   Keep two real task families per experiment; seeds/conditions remain exposure rows.
2. Qualify capture and reporting for these assertion-script checks. A nonzero exit
   with an assertion traceback is a failed executed check, even if an earlier
   `public passed` line appears. Preserve raw stdout/stderr before reduction. Do not
   invent test counts or use the parser-specific coverage/fault schema.
3. Preserve current-observation selection for both observation entries. The ordinary
   recent-history/check view is not a substitute for an initial directory containing
   differently bound observations and exact user-requested access. Qualify this path
   using actual first inputs and returned bodies before model exposure.
4. Add an independent temporal audit for the named pre-edit inspections and actual
   body delivery. In E20 it must cover every line before the first accepted edit.
   Preserve exact source/version and distinguish acquisition from continuing visibility.
   Also inspect preservation clauses the small graders do not test.
5. Declare whether a new run is a functional task regression or a pressure-continuity
   evaluation. A checked repair under today's bounded view can close its functional
   entry while leaving the historical pressure transition unqualified. It must not
   silently close the R50/X25 obligations. If a pressure comparison is later chosen,
   qualify its achievable input/output definitions and authentic boundary prospectively;
   do not import the old total-25k meaning into the new 23,808 input-only policy, add
   filler, or manufacture an observed fork after seeing the run.
6. Native qualification and a separately frozen finite exposure are still required.
   Do not choose a new allowance solely because the old actor finished within 24
   calls. Current grouping, optional accounts, explicit check policy and generation
   behavior change the opportunity/cost model. Preserve original task/acceptance and
   classify every such configuration change in the preparation.

This boundary needs task/observation/temporal-audit adapters, not a new store or
metadata taxonomy. Hidden evaluators and reference repairs stay outside actor inputs;
current task contracts, named audit obligations and available public checking remain
visible. Correct work and verified temporal compliance must be reported separately.

## Direct evidence reviewed

Besides all four task texts, eight checker scripts and four observation bodies, this
review read the faulty source routines discussed above, current historical request/
execution/inspection code, original specs/schedules/runtime profiles, and these
specific actual records:

- E19 cell-01/shared `001-rendered-prompt.txt`, separate thinking/final action and
  actual source-result metadata plus governing function; `008` public check and
  `009` checked submission thinking/actions/results. The response/result inventory
  also independently confirms cell-02's four/three saved response/result counts.
- E19 observation entry `execution_package/cell-03/initial-coding-request.json` and
  its exact stored bodies. There is **no live result to inspect**; the offline receipt
  is identified as offline rather than passed off as a transcript.
- E20 import cell-01/shared `001-coding-request.json`, thinking/action/full source
  result; cell-01/R50 `009-result.json`; all branch patch/check/submit actions and
  terminal snapshot file identities.
- E20 verifier cell-03/shared `001-rendered-prompt.txt`, thinking/action/exact
  observation result; cell-03/R50 `003-result.json`; all branch terminal actions and
  snapshot identities. The first response explicitly selects the matching candidate.
- All twelve E20 shared/branch summaries, four actual boundary records, terminal
  post-seal grading records, and the later measurement finding. These supplement
  direct records; they do not replace them or constitute a new exhaustive transcript
  audit. Historical detailed audits remain in their original experiment directories.
