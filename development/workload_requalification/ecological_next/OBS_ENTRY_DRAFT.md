# Next distinct entry: original E20 verifier observation

Read-only prospective fact review, 2026-10-02. **The current E20 source-import
run outcome is pending.** This note neither evaluates its unfinished artifact nor
authorizes implementation or model exposure. Root will publish a final next plan
after that run's closure, replay, accounting and artifact review.

**E20-OBS-VERIFIER-SAFETY** is the next distinct original entry candidate. Its
place in the execution sequence remains open: the source run's zero-count
contract and any earned prior-dispatch decision-view issue may take priority
after closure. This separate task/world combines observation selection with the
complete source-inspection obligation. No new store, semantic summary, planner,
reasoning setting or generic host feature is selected by this review.

## Exact entry and information boundary

Authority is the original
`experiments/020_owner_controlled_ecological_pilot_v2/fresh_bank/` case, with
`model_visible`, `execution_only` and `evaluator_only` material kept separate.

| Material | Bytes | SHA256 / identity |
|---|---:|---|
| Initial candidate | 128,545, 25 files | `a8ccf6bcf04177b0199148e6a91dad4ac9f1818c0898403b0fc91cceb43dcadd` |
| FIXTURE.json | 5,512 | `f0b17ae01e7c58f763161e2b2b0b045de0f5fbd2529079c5879911fb02631343` |
| TASK.txt | 1,268 | `618cfe2169ed68b1ca6aebc53dd880b98c2822bb215ff12ce412d53636544fa9` |
| public.py | 868 | `e484244a0eb144c0fbb1673e429dc8882a1976807374c0922785fee03eeb1951` |
| hidden.py | 1,070 | `6b17208c9beddc918b2ac39af8e4d6764b63c473bbd8db20fbee702dbb95434f` |

All 25 candidate file hashes and lengths match the fixture. The neutral initializer
is the exact 69-byte file; the historical admission limit is 24,000 bytes per file.
The candidate identity above is the original fixture identity, not a newly executed
repair or reconstructed runtime result. Compared with the original source-import
world, `importers.py`, `saved_runs.py` and `verifiers.py` have different fingerprints.
Load all 25 files from this fixture; copying the current source-import candidate
would import a different starting world and potentially its repair.

Fresh entry has no actor operation history, selected sources, acquired captures,
account, executed checks or submitted work. Present the exact task, current
candidate, ordinary reference and both observation inventory rows. Do not preload
either body, copy a previous model's source group/account/repair, include hidden
bytes, or reinterpret a fixture record as a check run by the new host.

## Original observations and transport

The fixture rows are original **verifier** records:

| Handle | Recorded candidate | Target | Body bytes / SHA256 |
|---|---|---|---|
| OBS-0001 | `23b5c17999963faf7453c68a6b537ae6c447555f77eb0a835bfa659ad47e89aa` | legacy verifier smoke | 147 / `090d40ebf5ea27ea375ec8fa38d155c889c59c9186ccf685903270d319d34240` |
| OBS-0002 | `a8ccf6bcf04177b0199148e6a91dad4ac9f1818c0898403b0fc91cceb43dcadd` | offline verifier safety | 322 / `c2657481323ab4a24caf3daeb3187d0cd64be152cb148d79632a961d5c5f1134` |

Both exact bodies are canonical JSON and independently match their row's
fingerprint, size and candidate binding. OBS-0001 says `status: passed`,
`failures: []`, and `suite: legacy verifier smoke`. It is the differently bound
distractor, not assurance on the starting candidate. OBS-0002 says `status: failed`
and records two findings: unsafe absolute/parent paths were accepted, and the
timeout behaved as a minimum of 60 instead of an inclusive 1..60 clamp.

The actor's task explicitly says to choose the current candidate binding and
reopen that body. Preserve that choice. Existing `reopen_observation(handle)` can
deliver a full immutable body, create an ordinary acquired RES receipt and retain
it through ordinary source operations, with identity deduplication and explicit
release by working-set replacement. No new OBS semantics are needed.

The shared bridge admits `action: capture` transport manifests; the originals say
`action: verifier`. Reuse the already declared E19 normalization: preserve the
original rows byte-exact, make a separately labeled transport copy changing only
`action`, and bind both original and transport state in snapshots/restore/custody.
Keep handle, sequence, candidate, target, size, hash and body unchanged. Neither
classification is a new execution. The bridge's transport snapshot alone does not
preserve original verifier classification; the task adapter must preserve it too.

Imported bodies provide no exact current-source editing authority and no applicable
public pass. Acquisition and actual body presentation remain separate. Audit the
model's selected handle, exact returned bytes and next delivered input. The required
observation selection/reopening should remain a separately reported task obligation;
do not silently add an observation gate merely by borrowing the source barrier.
If root chooses additional temporal enforcement, it needs an explicit prospective
policy and qualification.

## Complete source obligation

The exact task requires an exact **complete** read of every following path before
the first mutation. All are under `src/addressable_information_layer/`:

| Path | Lines | Bytes |
|---|---:|---:|
| verifiers.py | 319 | 14,787 |
| records.py | 460 | 12,218 |
| hashing.py | 39 | 1,172 |
| readiness.py | 141 | 5,925 |
| policy.py | 140 | 5,742 |
| routing.py | 55 | 1,979 |
| reducers.py | 134 | 5,106 |
| verifier_logs.py | 49 | 1,841 |
| storage.py | 58 | 2,688 |
| artifact_units.py | 459 | 17,440 |
| Total | 1,854 | 68,898 |

This is the same kind of complete-coverage obligation as E20 source-import, with
ten different designated paths. E19's four-path nonempty-exposure policy is
insufficient. Reuse the delivered-coverage semantics, not its hardcoded eleven-path
task identity: exact current-file ranges must continuously cover [1,true EOF],
with adjacent/overlap merging and separate custody carriers for merged displays.
Stored/acquired/rendered/measured but undelivered source, outlines, accounts,
addresses and partial serialized history do not count. Complete historical source
qualifies only through the existing exact current-source validator.

The prospective task-local declaration can guard both first mutation forms while
preserving the ordinary source/version/check guards. Credit is cumulative through
release of unchanged source; changed identity invalidates pre-boundary coverage;
current target text remains independently necessary for editing. Exact delivered
coverage establishes exposure, not comprehension or a semantic audit. A first
mutation accepted under that barrier partly measures host enforcement.

All ten files need not remain resident together. Their natural volume is a task
fact, not a native token count or a promise of one whole group fitting the current
23,808-token input ceiling. Keep bounded proof, compact missing extents, actual
dispatch authentication and the predecessor-bound first accepted mutation receipt.
Do not mutate the frozen source-import policy or instantiate its Task world to
obtain these generic semantics.

## Source defects and preservation boundary

Direct inspection of the original 319-line `verifiers.py` establishes the two
injected defects without executing a checker:

- `_safe_relative_path` normalizes backslashes, constructs `PurePosixPath`, then
  uses `path.is_absolute() and ".." in path.parts or not path.parts`. That rejects
  the conjunction but permits an absolute path without traversal and a traversal
  path without an absolute root. The empty-parts condition is independently present.
- `_bounded_timeout` converts with `int`, defaults to 20 on `TypeError` or
  `ValueError`, then returns `max(1, max(timeout, MAX_COMMAND_TIMEOUT_SECONDS))`.
  The inner maximum enforces a minimum of 60 and fails the upper bound.

The function interfaces, command-prefix enforcement, `shell=False`, temporary
workspace use, source materialization, cwd resolution and containment check,
output truncation, and deterministic receipt construction are separate existing
behaviors. Preserve them and the other 24 file bodies; no changed tests or added
dependencies. The full required companion sources describe record types,
deterministic hashing, readiness/policy classifications, routing/reducer behavior,
log-derived events, result storage and unit materialization. They are the required
audit world, not a license to revise unrelated policies.

No reference successor or literal fix is proposed as actor input. A later
engineering script may derive edits from exact actually displayed source and task,
consume real current public feedback and preserve a failed partial repair if useful.
The private/reference contribution stays outside the untouched actor entry. A
correct direct solution also counts; the model need not make a wrong repair first.

## Fixed grade and broader contract

Public checks canonical `pkg/module.py`, leading parent traversal, a POSIX absolute
path and empty path; timeouts 0,20,above maximum and an invalid string; a contained
subdirectory and a rejected cwd escape. Hidden repeats public and adds backslash
normalization, timeout -100 and a very large integer. Hidden can print the earlier
`public passed` line before a later assertion fails: actual process completion and
exit status govern the overall observation. Existing raw-observation preservation
and the generic assertion-script `case_reports` projection already handle that
boundary; do not add parser fault schemas or invented test counts.

Keep both graders byte-exact, public actor-requested and hidden post-seal. Neither
checks command-prefix enforcement, deterministic receipts or the complete source
inspection/observation obligations. Those require exact artifact/provenance/temporal
review separately. No automatic edit checks are justified merely by this entry.

Two narrow scope questions deserve explicit post-seal review, without silently
strengthening the graders or declaring new failure results:

- The invalid-timeout script uses a string; the implementation catches only
  `TypeError`/`ValueError`, not `OverflowError`. Whether the broad task wording
  includes all numeric conversion failures is not established by that script.
- The path helper uses POSIX path semantics after separator normalization. Fixed
  cases do not establish treatment of drive-qualified spellings or native path
  containment across platforms. Any additional executable examples need a
  declared, separately qualified evaluator scope; do not call a small function
  repair a general verifier safety certification.

No supplemental probe is selected here, and no such cases were executed. The
existing source-import twelve-case probe is a different task's assessment and
must not be copied into this verifier entry.

### Direct source references for these conclusions

Paths below are relative to the original case, not to a changed donor or a
successful historical candidate. The exact file hashes are recorded above and
in FIXTURE.json. The target file is
`model_visible/E20-OBS-VERIFIER-SAFETY/candidate/src/addressable_information_layer/verifiers.py`,
SHA256 `7fce50addb0186306b21d29d28d7b89efe3409419f8f2944c059364cdb5dcf22`.

- Exact task line1 states current-observation selection, ten complete path reads
  before mutation, inclusive timeout bounds, rejection/preservation obligations,
  public checking and submission. FIXTURE.json line1 binds those same ten paths,
  all 25 original files and both `action: verifier` observation rows.
- `verifiers.py:25` defines maximum60; `:251` begins timeout conversion, `:254`
  identifies the two caught exception classes, and `:256` has the inner maximum.
  These are source facts, not a new observation that every invalid input fails.
- `verifiers.py:269` begins separator normalization and PurePosixPath handling;
  `:272` contains the conjunction. The separate command allowlist begins at
  `:233`, command execution at `:195` uses `shell=False` at `:217`, materialization
  begins at `:259`, cwd containment at `:277` checks `relative_to` at `:286`, and
  deterministic receipt construction begins at `:300`.
- `execution_only/E20-OBS-VERIFIER-SAFETY/public.py:7` begins exact path assertions;
  `:11` begins timeout assertions; `:17` tests contained cwd and `:18` escape.
  `evaluator_only/E20-OBS-VERIFIER-SAFETY/hidden.py:21` adds backslash normalization,
  `:22` negative timeout and `:23` a large integer. Its earlier line19 pass text
  does not establish completion of those later assertions.
- Each exact observation is one JSON line under
  `execution_only/E20-OBS-VERIFIER-SAFETY/observations/`. OBS-0002's two recorded
  expectations are rejected unsafe paths and an inclusive1..60 timeout clamp;
  neither record contains an actor check definition, new execution time or
  current repaired-candidate pass.

This follow-up review reread those exact task/fixture/OBS/checker files and the
complete governing verifier routines directly. It did not treat the earlier
draft or old diagnostic summary as their substitute, and did not execute a
function probe, checker, import adapter, model or native request.

## Smallest prospective port

After current source-run closure and review, publish one new bounded task-local
entry combining existing imported-capture custody/retention with complete delivered
coverage for the ten original paths. Keep the original task and 25-file world,
two observation records, ordinary operations, optional account, public-only/no-auto
check policy and immutable archive. The adapter must validate its own candidate
and original rows rather than inherit the hardcoded E19 or source-import fixture.

Bind original fixture/task/checkers/all candidate files/both observation bodies,
the bridge, actual coverage implementation, schema/reference/decoder and runner/
replay/qualification dependencies. First input must have two inventory rows, no
OBS body or prior acquired source, no account/check/history, and no evaluator
findings. Validate actual extended constrained forms, including historical access,
unknown/corrupt rejection and candidate-bound source/check authority separation.

CPU transition tests should include complete ten-path coverage through replacement,
merged ranges, both first-mutation rejections and accepted boundaries, retained
OBS2 surviving ordinary acquisitions and OBS reread deduplication, explicit release,
typed restore/tamper of coverage plus original/transport provenance, and unchanged
historical source bindings. Native engineering qualification should show that
model-selected observation access and bounded source groups can be delivered,
an incomplete inspection is rejected truthfully, useful source-derived work reaches
real public feedback, a correction reaches current pass, and submission closes.
Every scripted next choice needs support in its actual preceding input; supplied
script decisions remain evaluator assistance, not model performance.

Root must declare the live budget/settings prospectively after qualification.
Reusing 24 requests/72 operations, seed173205 and the current actor is a possible
functional configuration, not a promise of adequate opportunity or an unchanged
replication. Do not add allowance after exposure, coach inside the run, execute
private drafts, preload a reference group or change effort/format silently.

## Remaining pressure and evidence limits

The original E20 schedule had two seeds, shared prefixes and paired R50/X25
branches. Its eight fixed public/hidden passes remain historical grades. This
review did not rerun or comprehensively reread those trajectories. The entry map
records that the verifier prefix included observation recovery and all ten reads
before its pressure fork; that is historical context, not fresh delivery evidence.

The old 25,000-token total envelope and current input-only ceiling differ in actor,
template, response reserve, history and selection policy. A current functional
repair or selection turnover cannot close that matched pressure obligation.
Neither artificial filler nor an inherited repaired prefix belongs in this fresh
entry. Keep wider corpus and pressure work open under separately qualified plans.

This note directly reviewed exact TASK/FIXTURE/both OBS bodies/public/hidden, all
ten mandatory source files, the current observation/coverage adapters and the
ecological entry map. Inert standard-library file hashing verified all 25 source
rows, source totals, exact observation canonical bytes and listed material hashes.
It made no task import, checker, native, model or GPU call and changed only this
unbound prospective note.
