# Queue after interpolation and the three small repairs

Read-only contract review, 22 September 2026. This supplements PLAN.md, STATUS.md,
CORPUS_RECONCILIATION.md and INVENTORY.json. No model, checker, runtime preparation
or test was executed for this review. Candidate IDs and the explicitly listed
checker hashes were read or computed from preserved files; this is not a complete
seal verification. No frozen source or evidence was changed.

The next useful unit is a task plus its entry and transition contract. Identical
task wording, a related library, or a historical passing artifact is insufficient
to merge entries. Conversely, presentation variants, seeds and copied preparation
files do not automatically require separate substantive tasks. All-corpus success
remains open, including legacy rows not resolved by these five queued families.

## 1. Configparser maintenance: three distinct entries

### Original backport

- Exact entry: `development/configparser_backport/input-qualification-003/candidate.json`,
  ten files from CPython v3.12.10, candidate
  `f32256765ff11d4a353900e33ec9b503255cd4718ea344f77e17311a84391170`.
- Assignment: `development/configparser_backport/TASK.txt` (inventory task hash
  `9ead28afffaad5cd04527d9fdd0f3ae86974e219e9b6a48a6dc4b01098af3717`).
  Implement MultilineContinuationError, add meaningful regressions and accurate
  reference documentation, preserve existing behavior, check and submit.
- Exact historical checker: `input-qualification-003/PUBLIC_CHECK.py`, SHA256
  `20906e55f2d2ac0646bc46ec81f42af6b033b1a871d1bb1bbc9dce43f0f1fb19`.
  It checks the frozen upstream suite, eight independent contract methods, edited
  tests, detection of the original by added tests, and a documentation declaration.
  Accurate prose remains an independent review obligation.
- Historical exposure: run-001 saved a correct library change; after 32 actions,
  the next read could not be delivered. No tests/docs contribution or submission
  completed. See `development/configparser_backport/review/RESULTS.md`.

### Tests and documentation from the saved library

- Entry loader: `scripts/bounded_parser.py:starting_evidence`; exact source is
  `development/configparser_backport/run-001/after/C32-candidate.json`, candidate
  `8ac73858f45e89ecb2df138e2accfdb105d0325ffc056e0bad7e9bf7e7c89a2d`,
  with the 32 genuine preceding action/result pairs. Earlier thought is not input.
- Assignment: `development/bounded_working_set/TASK.txt`, inventory task hash
  `9d0d23e959b111960eb97ca519388f2edbbe0387b63d6b7b5eed791ea1936df1`.
  The loader uses `scripts/configparser_backport.py:checker()` for the same
  backport acceptance contract. Pin its complete generated checker bytes rather
  than the tail template alone.
- Historical autonomous attempts did not finish. Assisted regression and
  documentation sessions subsequently completed the work. Those successes do not
  close this uncoached saved-library entry.

### Parser-raised exception transport extension

- Entry loader: `scripts/parser_roundtrip.py:starting_work/initial_session`;
  `development/bounded_working_set/parser-documentation/turn-04/final-candidate.json`,
  candidate `fbfc4f7a4edf09b8670fb8b0e8700258f59c22114ab6bdc6915beab9b9b89e75`.
  Retain its 39 prior actions as ancestry, but begin with an empty selected group.
- Assignment: `development/uncoached_contribution/TASK.txt`, inventory task hash
  `00b8d4e25a21157107461e140553b6195566c1c604912a438f975004bc113224`.
  Only the test file changes. A real parser exception with and without a final
  newline must survive copy, deepcopy and every available pickle protocol, with
  exact class, arguments and diagnostic state asserted.
- Checker factory: `scripts/parser_roundtrip.py:checker`, combining the exact
  saved baseline, legacy harness and `development/uncoached_contribution/PUBLIC_CHECK.py`.
  Preserve saved/edited suites, contract tests, old-work preservation, observed
  transports and four faulty-restoration checks. Historical run-001 completed in
  four model requests, but later reasoning variants are exposures of this same
  entry, not new maintenance tasks.

Preparation for this family: adapt the old report boundary before inference.
`configparser_backport/PUBLIC_CHECK.py:169-188` drops diagnostics at 4,096 bytes;
`uncoached_contribution/PUBLIC_CHECK.py:134-147` truncates details then may drop
all of them at 6,500. The repaired outer capture cannot recover those discarded
details. Preserve the report before reduction, retain the original verdict
computation, distinguish expected mutant failures from real candidate failures,
and qualify the complete failed-check projection. Do not silently replace the
old acceptance with interpolation's checker. Added executable-doc feedback is a
prospective task-policy choice; it does not eliminate prose review. Qualify
preservation from each entry separately, including its inherited checks and
episode labels. An original backport success will not by itself test continuation
from C32 or coverage extension from the assisted final candidate.

## 2. Compiler incident and saved-report restart

- Original entry: `development/compiler_incident/preparation-001/candidate.json`,
  six files, candidate
  `28441db41e7ca5385feb03c96574fed32acfc4d67e7e608c93572fe06ed8033d`.
  Load from the sealed package via `scripts/run_compiler_incident.py:load_fixture`,
  not the oracle/capture builder.
- Task: preparation `TASK.txt`, inventory hash
  `469cf1b592326122c0e46bafd3e4143b288a308688615a6f4b54503839be4090`.
  Repair the optimizer and write both historical build comparisons to
  `reports/incident.json`. Preserve original/captured behavior versus current
  repair verification.
- Checker: preparation `PUBLIC_CHECK.py`, SHA256
  `23d69d6a42e0f8bfd34ac0ea83c14e533ab549cae67d9755b3f0126f2e39446a`;
  26 contract/report cases. `observations.json` and `captures.json` define three
  exact historical observations and their original candidate bindings. They are
  essential task inputs, not optional checker diagnostics.
- Historical exposure: two shared-prefix cells led to one checked repair/report,
  two smaller-input capacity stops and one resident empty final. This was not
  four independent tasks. A new repaired-host completion is development
  requalification, not a replay of that R23808/X16000 comparison.
- Distinct saved-report entry: `scripts/saved_work_continuation.py:starting_state`
  replays three separately recorded proposal-check operations from
  `development/delivery_dialogue/proposal-check-001/`; candidate
  `f7939c49b60d57f19b88dde8d31c6deb0ea036b6a3746c5d27b61d5ce0b99fd6`,
  with a correct optimizer and empty report. `PHASE_1.txt` asks for OBS-0002;
  `PHASE_2.txt` extends/corrects the actual saved report for both builds.
  The first accepted check after a report edit triggers the recorded phase
  transition irrespective of pass. The historical protocol supplies four initial
  acquisitions and five restart acquisitions, explicitly researcher-selected.
  Its nine-action checked completion remains assisted evidence.

Preparation: import historical capture bodies into reachable exact observation
access, preserving their old bindings and scope. The ordinary WorkingSession
delegation (`working_session.py:466`) constructs a new SessionState without the
fixture's incident-observation collection; copying candidate files and checker
alone would lose essential inputs. Qualify the actual model-visible route to all
three observations before native exposure. Keep an uncoached original entry and
an assisted-restart regression separately labeled. If a new autonomous restart
variant is selected, it is an additional declared condition, not retroactive
replacement of the assisted contract. Test actual saved incomplete/incorrect
report feedback and the transition from first entry to second; a final report
pass alone does not establish continuity across that restart.

## 3. URL-port original entry

- Loader: `development/working_account/task.py:starting_candidate` checks the six
  task file hashes in `development/working_account/url_ports/SOURCE.json`.
  Its donor is CPython v3.12.0 commit
  `0fb18b02c8ad56299d6a2910be0bab8ad601ef24`. The four additionally downloaded
  support files are acquisition evidence, not candidate padding.
- Entry and task: `development/working_account/url_ports/TASK.txt`; empty selected
  source group and account, no completed port additions. Obtain the exact initial
  candidate ID and three fully generated checker hashes from this loader's
  preserved preparation before freezing a new package; this review did not invoke
  the loader or assert those identities.
- Check factory: that task module combines baseline files, scope and
  `development/working_account/examples.py` with `url_ports/CHECK.py`. The policy
  triggers tests after test edits and public after documentation edits; only
  current public pass permits submission. The original contract includes both
  urlsplit/urlparse, str/ASCII-bytes cases, exact error/timing/boundary behavior,
  seven deliberate faults, executable examples and preservation/prose review.
- Historical fresh run stopped after four replies/three acquisitions because
  rejection feedback did not fit. Numerous later recovery and correction states
  descend from it. The coherent-diagnostics checked correction closes its saved
  work entry only; it does not close autonomous selection and contribution from
  the original empty entry.

Preparation: use the already repaired common host/report semantics with the
original candidate and task, not the later saved tests/docs. Compare original
acceptance against the revised checker definition, preserving any prospectively
declared strengthened checks already earned. Qualify broad acquisition, control
rejection and replacement plus complete test/docs feedback. Do not require Qwen
to repeat the historical bad selection or wrong expectation to count as success.

## 4. Ecological source and observation cases, E018-E020

Each bank keeps the task at `fresh_bank/model_visible/<case>/TASK.txt`, source
under its `candidate/`, the entry manifest/checker under
`fresh_bank/execution_only/<case>/FIXTURE.json` and `public.py`, and hidden
acceptance under `fresh_bank/evaluator_only/<case>/hidden.py`. Preserve those
separations. Bank manifests enumerate file hashes; do not infer identity from a
similar task name.

| Exact case | Initial candidate | Distinct obligation |
|---|---|---|
| E18-SOURCE-LANTERN | `3dfa888955adab1021a75c47f1e1400887a8a16b4fb920c190f60fdbae9fe882` | Four required source reads in a 130-file world |
| E18-OBS-HARBOR | `e331513f6ce44015a22f975c289b0594c11e6a685299c3e4aeabcb331a399a49` | Four required reads plus two historical/current observation records |
| E19-SOURCE-REOPEN | `d2a57a0044458310fbe0b915eb88447b6f76b87dd511d68a0e31c29416342116` | Artifact unit/reopen boundary repairs; task text names exact pre-edit source |
| E19-OBS-SUMMARY-GRAPH | `476f83a90c40b0897e1ab5d6bc00bbb52cf3a4fe60cc11c1dd47ab3da85d0172` | Candidate-bound observation selection and summary-graph repair |
| E20-SOURCE-IMPORT-BOUNDARIES | `2355c3eaa32dcf8db2659a75feb3a93309255fbff60e14b7f154dc34c47675c0` | Exact complete inspection of eleven specified files before first mutation; four boundary repairs |
| E20-OBS-VERIFIER-SAFETY | `a8ccf6bcf04177b0199148e6a91dad4ac9f1818c0898403b0fc91cceb43dcadd` | Select/reopen current observation; exact complete inspection of ten files before mutation; verifier safety repair |

Historical E018 includes genuine completed observation branches and failed
resident paths. E019 stopped after a source-path candidate/custody defect before
any observation-case exposure: its observation fixture is prepared-only until an
actual exposure is found, not a failed Qwen task. E020 completed all eight
historical trajectories. Those outcomes do not make the six listed fixtures
duplicates, nor do seeds and residency conditions make each fixture a different
repair. The E19 task-level reading requirement still matters even though the
inspected fixture JSON's required-inspection list is empty.

Preparation: retain public AND hidden checks and independently evaluate temporal
requirements. Current visible-source eligibility only proves the exact old edit
text was delivered; it does not establish completion of an entire acceptance
reading list before the first edit. Reuse the repaired
`ecological_pilot_v2.py:inspection_status` with actual delivered source and identity
rather than path-only completed-read flags. Incident observations must be made
reachable as in the compiler family. Running these cases on the new selection
policy can close task regressions but cannot claim replication of historical
pressure/residency effects. Do not add forced paging or reading beyond original
task requirements merely to recreate a pressure boundary.

## 5. Phase, exact recovery and predecessor reconciliation

Do not flatten E002-E017 to one ordinary repair. The frozen phase manifests and
phase texts identify acquisition obligations, workflow progress changes,
prefork/public checks, probes, fork readiness and the next task. E013/E014's
`src/working_set_exp/phase_receipts.py` explicitly requires Phase A progress=1,
prefork validation (and an integrity probe for the observation case), then a
different Phase B repair. E015 uses E014 at a completed Phase B closure checkpoint;
that is a distinct exposed entry, not fresh acquisition work.

E017 adds an embedded recovery task absent from the task-file inventory:
`src/working_set_exp/event_frame_v2_qualification.py:_signal_fixture` (lines149-210).
Its actual historical edit replaces the exact marker in `archive/source.dat`;
Phase B must locate/reopen the prior action's old/new payload, read current
`report.py`, restore the removed marker, check and submit. Its tiny public checker
alone would accept an evaluator-leaked marker, so final candidate correctness is
insufficient. Preserve the actual historical pair and assess its reacquisition.
Do not insert the marker, reference solution or old private thought in the new
normal input. The related closure fixtures also test stale/current check binding.

Preparation: first map each exact bank/candidate/checker/phase checkpoint to its
actual exposure and acceptance. Use existing phase machinery or a task-specific
adapter that preserves these transitions; leave any unimplemented transition
explicitly open. A monolithic rewrite or new general planner is unnecessary.
E016 capacity stress and the unexposed INC-042 worlds are engineering regressions,
not actor tasks that require an invented artifact.

The predecessor inventory remains a separate reconciliation queue. The 27 task
texts cover live task families and duplicated banks/trajectory inputs; three
currently appear only in fixtures_dev. Candidate and checker identity must be
compared before deduplication. Its original Experiment001 checker reportedly
failed even known-good work, so qualify the apparatus against preserved original
and reference candidates before assigning its outcome to a model. This bounded
review does not supply missing predecessor exposure mappings or close that queue.

## Preparation order and stop conditions

After the active interpolation continuation and the three already prepared small
repairs, prepare the configparser original/saved-library/transport entries first:
they reuse the same real-source/checker lineage while exposing the known upstream
diagnostic-loss boundary. Then compiler original and saved-report transition;
original URL-port entry; ecological and legacy phase/recovery entries. Exact
legacy mapping can proceed read-only in parallel with the earlier live runs.

The highest-priority portability checks are (1) preserve complete observations
before old checker formatting, (2) import genuinely available historical evidence
without fabricating current checks, and (3) retain acceptance conditions about
when reading, phase transitions and recovery happened. Reuse current guards,
capture, grouping and replay. Do not add an abstraction until one of these exact
contracts requires it. Passing all future public checkers would still leave
direct artifact/prose quality and temporal obligations to audit.
