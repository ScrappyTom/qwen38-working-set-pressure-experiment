# Experiment 020 Host-Path Audit

## Scope

This audit traces what the host prepared, what Qwen actually received and
emitted, what the host executed, and what was withheld until sealing. It is
paired with `TRANSCRIPT_INDEX.json`, which binds every saved request,
rendered prompt, endpoint response, private reasoning output, action, and
result by SHA-256.

## Authority and launch

The live entrypoint required exact structural equality with the owner
authorization. Before launch it verified:

1. the eight-branch schedule and one-attempt rule;
2. bank, package, runtime, actor, and closure hashes;
3. output-root absence;
4. dedicated port 18122 availability;
5. absence of a competing project server;
6. the complete project-code closure a second time adjacent to launch.

The owned llama.cpp process used the frozen AD-IQ2_S actor. The process exited
after the response seal and grading lifecycle; shutdown custody confirms the
PID ended and port 18122 was released.

## Call accounting

The actual live execution made 106 completions:

| Segment | Calls |
|---|---:|
| four shared pre-pressure prefixes | 40 |
| four R50 continuations | 27 |
| four X25 continuations | 39 |
| total | 106 |

Prepared invocations equal HTTP completions. There was no request denied by a
capacity guard, no HTTP failure, and no missing terminal response. The
conceptual paired totals in `MECHANICAL_RESULTS.json` count each shared prefix
once with R50 and once with X25; those conceptual totals are 67 and 79 and
must not be mistaken for 146 physical calls.

## Per-cell host path

### Cells 01–02: import boundaries

The shared actor read nine of eleven required source files and stopped at the
first authentic 25k boundary before mutation. Each branch then received the
same exact task, current candidate, event prefix binding, remaining two audit
obligations, P0 root, tools, and budgets.

R50 retained all event payload bodies. X25 externalized only oldest bodies and
retained action type, readable target, completion status, candidate/file
binding, ranges, and canonical reopen address. Both conditions completed all
eleven reads before the first accepted mutation.

Cell 02 R50's no-op patch was rejected as `tool_rejected`; the invocation and
rejection remained in the ordered event frame and consumed the ordinary action
budget. No host retry occurred.

### Cells 03–04: verifier observation

The shared actor selected `OBS-0002` by exact current-candidate binding,
reopened its 322-byte exact body, and read every required source file before
the authentic fork. The body identified the two actual failure classes but
did not disclose evaluator code or the desired patch.

R50 retained that exact body. X25 retained the readable observation identity,
target, candidate binding, size/hash, and canonical handle while moving the
old body to exact external custody. Qwen explicitly requested the body again
where needed. The host returned exact bytes without summary, ranking, or
relevance judgment.

## Parsing and execution

Every endpoint response contained one strict JSON action. The semantic-strict
transport accepted JSON whitespace/key-order freedom but performed no repair.
Every action then passed through the frozen action interpreter and exact
candidate/file/check admission path.

Observed host outcomes:

- 105 accepted actions;
- one bounded no-op patch rejection;
- eight passing public checks bound to the exact current candidates;
- eight accepted submissions bound to those checked candidates.

No stale candidate action, invalid handle, missing path, malformed response,
checker isolation failure, response-size breach, or token-accounting breach
occurred.

## Sealing and evaluator boundary

The host sealed 1,625 response-side files before opening evaluator truth. The
seal aggregate is
`5c9f3f3d59ff9adea3e13b0dffc9c68ae45dcb18b0788594495db597764e29e95`.

Only after that seal did the host load hidden grading material. All eight
terminal snapshots passed. The direct analysis reran hidden grading from exact
candidate custody and obtained the same pass status.

## Direct-review coverage

The primary agent read all 106 saved coding requests, private reasoning
outputs, final action objects, and exact results. Repeated shared source bodies
were checked for exact byte identity across seeds; condition-specific dynamic
requests were read individually. Diagnosis in `DIRECT_TRANSCRIPT_AUDIT.md`
therefore distinguishes:

- signal actually visible to Qwen;
- exact body resident versus external;
- Qwen's stated interpretation;
- Qwen's chosen action;
- the exact host observation that followed.

The host path supports the behavioral conclusions. No outcome needs to be
discarded or reclassified due to apparatus behavior.

